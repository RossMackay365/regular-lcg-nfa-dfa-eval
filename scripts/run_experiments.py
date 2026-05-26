"""
Run the three solver configurations on every selected instance, 600s time limit per run.

For each `instances_json/{bin}/{name}.json`, runs three configurations against
`models/{problem_type}.mzn`:

  1) NFA propagator:    instances_dzn/nfa/{bin}/{name}.dzn,  solver pumpkin-regular
  2) DFA propagator:    instances_dzn/dfa/{bin}/{name}.dzn,  solver pumpkin-regular
  3) Decomposition:     instances_dzn/dfa/{bin}/{name}.dzn,  solver pumpkin-decomposition

Each invocation writes into a fresh timestamped run directory so reruns never overwrite
prior results:

  results/{YYYY-MM-DD_HH-MM-SS}/{bin}/{name}.json   # per-instance, all three runs embedded
  results/{YYYY-MM-DD_HH-MM-SS}/summary.csv         # one row per (instance, config)
"""

import csv
import json
import random
import subprocess
import sys
from datetime import datetime
from pathlib import Path

_SCRIPTS_ROOT = Path(__file__).resolve().parent
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

from generators.helper import BIN_DIRS


# ---------------------------------------------------------------------------
# Paths & Constants
# ---------------------------------------------------------------------------
_ROOT        = Path(__file__).resolve().parent.parent
MODELS_ROOT  = _ROOT / "models"
DZN_ROOT     = _ROOT / "instances_dzn"
JSON_ROOT    = _ROOT / "instances_json"
RESULTS_ROOT = _ROOT / "results"

TIMEOUT_SEC = 600
MASTER_SEED = 42

CONFIGS = [
    {"name": "nfa",           "dzn_kind": "nfa", "solver_id": "nl.tudelft.algorithmics.pumpkin-regular"},
    {"name": "dfa",           "dzn_kind": "dfa", "solver_id": "nl.tudelft.algorithmics.pumpkin-regular"},
    {"name": "decomposition", "dzn_kind": "dfa", "solver_id": "nl.tudelft.algorithmics.pumpkin-decomposition"},
]

CSV_FIXED_COLUMNS = [
    "bin", "problem_type", "instance", "blowup",
    "config", "solver_id",
    "status", "exit_code",
]
CSV_STAT_COLUMNS = [
    "solveTime",
    "flatTime",
    "nodes",
    "failures",
    "restarts",
    "propagations",
    "nogoods",
    "AverageLearnedNogoodLength",
    "AverageLbd",
    "AverageBacktrackAmount",
]


# ---------------------------------------------------------------------------
# 1. Instance Loading
# ---------------------------------------------------------------------------
def discover_instance(json_path):
    instance = json.loads(json_path.read_text())
    return {
        "json_path":    json_path,
        "name":         instance["name"],
        "problem_type": instance["problem_type"],
        "blowup":       instance["blowup"],
        "blowup_bin":   json_path.parent.name,
        "model":        MODELS_ROOT / f"{instance['problem_type']}.mzn",
    }


def dzn_path(info, dzn_kind):
    return DZN_ROOT / dzn_kind / info["blowup_bin"] / f"{info['name']}.dzn"


# ---------------------------------------------------------------------------
# 2. MiniZinc Running
# ---------------------------------------------------------------------------
def run_minizinc(model, dzn, solver_id):
    argv = [
        "minizinc",
        "--solver", solver_id,
        "--statistics",
        "--json-stream",
        "--time-limit", str(TIMEOUT_SEC * 1000),
        str(model),
        str(dzn),
    ]
    proc = subprocess.run(argv, capture_output=True, text=True)
    return {
        "argv":      argv,
        "stdout":    proc.stdout,
        "stderr":    proc.stderr,
        "exit_code": proc.returncode,
    }


# ---------------------------------------------------------------------------
# 3. JSON Stream Parsing
# ---------------------------------------------------------------------------
def parse_json_stream(stdout):
    stats = {}
    errors = []
    solution_seen = False
    parse_errors = []

    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            parse_errors.append(line)
            continue

        match msg.get("type"):
            case "statistics":
                stats.update(msg.get("statistics", {}))
            case "solution":
                solution_seen = True
            case "error":
                errors.append(msg.get("message") or msg.get("what") or str(msg))

    return {
        "stats":         stats,
        "errors":        errors,
        "solution_seen": solution_seen,
        "parse_errors":  parse_errors,
    }


# ---------------------------------------------------------------------------
# 4. Individual Run Orchestration
# ---------------------------------------------------------------------------
def run_config(info, cfg):
    dzn = dzn_path(info, cfg["dzn_kind"])
    print(f"  [{cfg['name']:<13}] solver={cfg['solver_id']}  dzn={dzn.relative_to(_ROOT).as_posix()}")

    run = run_minizinc(info["model"], dzn, cfg["solver_id"])
    parsed = parse_json_stream(run["stdout"])

    if parsed["errors"] or run["exit_code"] != 0:
        status = "ERROR"
    else:
        status = "SATISFIED" if parsed["solution_seen"] else "UNKNOWN"

    print(
        f"  [{cfg['name']:<13}]   -> status={status}  "
        f"solveTime={parsed['stats'].get('solveTime', 'n/a')}"
    )

    return {
        "solver_id":    cfg["solver_id"],
        "dzn":          dzn.relative_to(_ROOT).as_posix(),
        "status":       status,
        "exit_code":    run["exit_code"],
        "stats":        parsed["stats"],
        "errors":       parsed["errors"],
        "parse_errors": parsed["parse_errors"],
        "stdout":       run["stdout"],
        "stderr":       run["stderr"],
    }


# ---------------------------------------------------------------------------
# 5. Output Writers
# ---------------------------------------------------------------------------
def write_instance_json(run_dir, info, per_config_results):
    out_path = run_dir / info["blowup_bin"] / f"{info['name']}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "instance":         info["name"],
        "problem_type":     info["problem_type"],
        "blowup_bin":       info["blowup_bin"],
        "blowup":           info["blowup"],
        "timeout_seconds":  TIMEOUT_SEC,
        "model":            info["model"].relative_to(_ROOT).as_posix(),
        "configs":          per_config_results,
    }
    out_path.write_text(json.dumps(payload, indent=2))
    return out_path


def flatten_for_csv(info, per_config_results):
    rows = []
    for cfg in CONFIGS:
        result = per_config_results[cfg["name"]]
        row = {
            "bin":          info["blowup_bin"],
            "problem_type": info["problem_type"],
            "instance":     info["name"],
            "blowup":       info["blowup"],
            "config":       cfg["name"],
            "solver_id":    result["solver_id"],
            "status":       result["status"],
            "exit_code":    result["exit_code"],
        }
        for key in CSV_STAT_COLUMNS:
            row[key] = result["stats"].get(key, "")
        rows.append(row)
    return rows


def write_summary_csv(run_dir, rows):
    out_path = run_dir / "summary.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    columns = CSV_FIXED_COLUMNS + CSV_STAT_COLUMNS
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return out_path


# ---------------------------------------------------------------------------
# 6. Select Instances (Equal Number Per Bin)
# ---------------------------------------------------------------------------
def select_balanced_instances(seed=MASTER_SEED):
    per_bin = {
        bin_name: sorted(JSON_ROOT.glob(f"{dir_name}/*.json"))
        for bin_name, dir_name in BIN_DIRS.items()
    }

    sizes = {b: len(p) for b, p in per_bin.items()}

    n = min(sizes.values())
    rng = random.Random(seed)
    chosen = []
    for bin_name in BIN_DIRS:
        chosen.extend(sorted(rng.sample(per_bin[bin_name], n)))

    print("Bin sizes on disk:  " + ", ".join(f"{b}={sizes[b]}" for b in BIN_DIRS))
    print(f"Sub-sampling each bin to min size = {n} (seed={seed})\n")
    return chosen


# ---------------------------------------------------------------------------
# 7. Main
# ---------------------------------------------------------------------------
def main():
    json_paths = select_balanced_instances()

    run_dir = RESULTS_ROOT / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"Running {len(json_paths)} instances x {len(CONFIGS)} configs = {len(json_paths) * len(CONFIGS)} runs")
    print(f"Per-run time limit: {TIMEOUT_SEC} s")
    print(f"Writing results to {run_dir.relative_to(_ROOT).as_posix()}\n")

    all_rows = []
    for i, json_path in enumerate(json_paths, start=1):
        info = discover_instance(json_path)
        print(f"[{i}/{len(json_paths)}] {info['blowup_bin']}/{info['name']}  (blowup={info['blowup']:.2f})")

        per_config_results = {}
        for cfg in CONFIGS:
            per_config_results[cfg["name"]] = run_config(info, cfg)

        out_path = write_instance_json(run_dir, info, per_config_results)
        all_rows.extend(flatten_for_csv(info, per_config_results))
        print(f"  wrote {out_path.relative_to(_ROOT).as_posix()}\n")

    write_summary_csv(run_dir, all_rows)

if __name__ == "__main__":
    main()
