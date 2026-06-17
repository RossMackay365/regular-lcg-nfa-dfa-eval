"""
Run the three solver configurations on every selected instance.

For each `instances_json/{bin}/{name}.json`, runs three configurations against
`models/{problem_type}.mzn`:

  1) NFA propagator:    instances_dzn/nfa/{bin}/{name}.dzn,  solver pumpkin-regular
  2) DFA propagator:    instances_dzn/dfa/{bin}/{name}.dzn,  solver pumpkin-regular
  3) Decomposition:     instances_dzn/dfa/{bin}/{name}.dzn,  solver pumpkin-decomposition

Results are written to:
  results/{YYYY-MM-DD_HH-MM-SS}/{bin}/{name}.json
  results/{YYYY-MM-DD_HH-MM-SS}/summary.csv
"""

import argparse
import csv
import json
import random
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

_SCRIPTS_ROOT = Path(__file__).resolve().parent
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

from generators.helper import BIN_DIRS, CONSTRUCTION_STEPS


# ---------------------------------------------------------------------------
# Paths & Constants
# ---------------------------------------------------------------------------
_ROOT        = Path(__file__).resolve().parent.parent
MODELS_ROOT  = _ROOT / "models"
DZN_ROOT     = _ROOT / "instances_dzn"
JSON_ROOT    = _ROOT / "instances_json"
RESULTS_ROOT = _ROOT / "results"

TIMEOUT_SEC = 1200
TIMEOUT_GRACE_SEC = 10
MASTER_SEED = 71

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
CSV_DERIVED_COLUMNS = [
    "layered_multigraph_sync_ms",
]
CSV_CONSTRUCTION_COLUMNS = []
for _step in CONSTRUCTION_STEPS:
    CSV_CONSTRUCTION_COLUMNS.append(f"{_step}_ms")
    CSV_CONSTRUCTION_COLUMNS.append(f"{_step}_states")

SUMMARY_COLUMNS = (
    CSV_FIXED_COLUMNS + CSV_STAT_COLUMNS + CSV_DERIVED_COLUMNS + CSV_CONSTRUCTION_COLUMNS
)


# ---------------------------------------------------------------------------
# Instance Loading
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
        "construction": instance.get("construction", {}),
    }


def dzn_path(info, dzn_kind):
    return DZN_ROOT / dzn_kind / info["blowup_bin"] / f"{info['name']}.dzn"


# ---------------------------------------------------------------------------
# Running MiniZinc
# ---------------------------------------------------------------------------
_SOLVER_CREATIONFLAGS = (
    getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    | getattr(subprocess, "CREATE_NO_WINDOW", 0)
)


def _kill_tree(proc):
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            for image in ("pumpkin-solver.exe", "minizinc.exe"):
                subprocess.run(["taskkill", "/F", "/IM", image], capture_output=True)
            proc.wait(timeout=5)
    else:
        proc.kill()
        proc.wait(timeout=15)


def _read_capture(f):
    f.seek(0)
    return f.read().decode("utf-8", errors="replace")


def run_minizinc(model, dzn, solver_id):
    argv = [
        "minizinc",
        "--solver", solver_id,
        "--statistics",
        "-v",
        "--time-limit", str(TIMEOUT_SEC * 1000),
        str(model),
        str(dzn),
    ]
    with tempfile.TemporaryFile() as out_f, tempfile.TemporaryFile() as err_f:
        proc = subprocess.Popen(
            argv, stdout=out_f, stderr=err_f, creationflags=_SOLVER_CREATIONFLAGS,
        )
        timed_out = False
        try:
            proc.wait(timeout=TIMEOUT_SEC + TIMEOUT_GRACE_SEC)
        except subprocess.TimeoutExpired:
            _kill_tree(proc)
            timed_out = True
        return {
            "stdout":    _read_capture(out_f),
            "stderr":    _read_capture(err_f),
            "exit_code": None if timed_out else proc.returncode,
            "timed_out": timed_out,
        }


# ---------------------------------------------------------------------------
# Statistics Parsing
# ---------------------------------------------------------------------------
_SYNC_KEY_RE = re.compile(r"LayeredMultigraphSyncTimeNs$")


def _parse_stat_value(raw):
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == '"' and raw[-1] == '"':
        return raw[1:-1]
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        return raw


def parse_text_output(stdout):
    stats = {}
    solution_seen = unsat = unknown = False

    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("%%%mzn-stat:"):
            body = line[len("%%%mzn-stat:"):].strip()
            if "=" in body:
                key, _, val = body.partition("=")
                stats[key.strip()] = _parse_stat_value(val)
        elif line == "----------":
            solution_seen = True
        elif line.startswith("====") and "UNSATISFIABLE" in line:
            unsat = True
        elif line.startswith("====") and "UNKNOWN" in line:
            unknown = True

    return {"stats": stats, "solution_seen": solution_seen, "unsat": unsat, "unknown": unknown}


def collect_errors(stdout, stderr):
    errors = []
    for blob in (stdout, stderr):
        for line in blob.splitlines():
            s = line.strip()
            if s.startswith("Error:") or s.startswith("MiniZinc: error"):
                errors.append(s)
    return errors


def filter_stderr(stderr):
    kept = [
        line for line in stderr.splitlines()
        if line.strip().startswith(("Error:", "Warning:", "MiniZinc: error"))
    ]
    return "\n".join(kept)


def layered_multigraph_sync_ms(stats):
    total_ns = 0
    found = False
    for key, val in stats.items():
        if _SYNC_KEY_RE.search(key) and isinstance(val, (int, float)):
            total_ns += val
            found = True
    return total_ns / 1_000_000 if found else None


# ---------------------------------------------------------------------------
# Individual Runs
# ---------------------------------------------------------------------------
def run_config(info, cfg):
    dzn = dzn_path(info, cfg["dzn_kind"])
    print(f"  [{cfg['name']:<13}] solver={cfg['solver_id']}  dzn={dzn.relative_to(_ROOT).as_posix()}")

    try:
        run = run_minizinc(info["model"], dzn, cfg["solver_id"])
    except Exception as exc:  # noqa: BLE001 - deliberately broad; resilience over precision
        print(f"  [{cfg['name']:<13}]   -> EXCEPTION {type(exc).__name__}: {exc}")
        return {
            "solver_id": cfg["solver_id"],
            "dzn": dzn.relative_to(_ROOT).as_posix(),
            "status": "ERROR",
            "exit_code": None,
            "stats": {},
            "layered_multigraph_sync_ms": None,
            "errors": [f"{type(exc).__name__}: {exc}"],
            "stdout": "",
            "stderr": "",
        }

    parsed = parse_text_output(run["stdout"])
    errors = collect_errors(run["stdout"], run["stderr"])

    if run["timed_out"]:
        status = "TIMEOUT"            
    elif errors or run["exit_code"] != 0:
        status = "ERROR"
    elif parsed["unsat"]:
        status = "UNSAT"
    elif parsed["unknown"]:
        status = "TIMEOUT"           
    elif parsed["solution_seen"]:
        status = "SATISFIED"
    else:
        status = "UNKNOWN"

    sync_ms = layered_multigraph_sync_ms(parsed["stats"])
    print(
        f"  [{cfg['name']:<13}]   -> status={status}  "
        f"solveTime={parsed['stats'].get('solveTime', 'n/a')}  "
        f"sync_ms={'n/a' if sync_ms is None else f'{sync_ms:.1f}'}"
    )

    return {
        "solver_id": cfg["solver_id"],
        "dzn": dzn.relative_to(_ROOT).as_posix(),
        "status": status,
        "exit_code": run["exit_code"],
        "stats": parsed["stats"],
        "layered_multigraph_sync_ms": sync_ms,
        "errors": errors,
        "stdout": run["stdout"],
        "stderr": filter_stderr(run["stderr"]),
    }


# ---------------------------------------------------------------------------
# Output Writers
# ---------------------------------------------------------------------------
def write_instance_json(run_dir, info, per_config_results):
    out_path = run_dir / info["blowup_bin"] / f"{info['name']}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "instance":        info["name"],
        "problem_type":    info["problem_type"],
        "blowup_bin":      info["blowup_bin"],
        "blowup":          info["blowup"],
        "timeout_seconds": TIMEOUT_SEC,
        "model":           info["model"].relative_to(_ROOT).as_posix(),
        "construction":    info["construction"],
        "configs":         per_config_results,
    }
    out_path.write_text(json.dumps(payload, indent=2))
    return out_path


def flatten_for_csv(info, per_config_results, configs):
    construction = info.get("construction", {})
    construction_cells = {}
    for step in CONSTRUCTION_STEPS:
        block = construction.get(step, {})
        construction_cells[f"{step}_ms"]     = block.get("ms_total", "")
        construction_cells[f"{step}_states"] = block.get("states_total", "")

    rows = []
    for cfg in configs:
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
        sync_ms = result["layered_multigraph_sync_ms"]
        row["layered_multigraph_sync_ms"] = "" if sync_ms is None else sync_ms
        row.update(construction_cells)
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Select Instances
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
# Resume Logic
# ---------------------------------------------------------------------------
_RUN_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$")
_LATEST = object()


def _resolve_run_dir(resume_arg):
    """Return (run_dir, resume). resume_arg is None (fresh run), the _LATEST sentinel
    (resume the newest run), or a path string (resume that directory)."""
    if resume_arg is None:
        run_dir = RESULTS_ROOT / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir, False

    if resume_arg is _LATEST:
        candidates = [d for d in RESULTS_ROOT.glob("*") if d.is_dir() and _RUN_DIR_RE.match(d.name)]
        run_dir = max(candidates, default=None)
        if run_dir is None:
            sys.exit(f"--resume: no run directories found under {RESULTS_ROOT.relative_to(_ROOT).as_posix()}")
    else:
        run_dir = Path(resume_arg)
        if not run_dir.is_absolute():
            run_dir = (_ROOT / run_dir).resolve()
        if not run_dir.is_dir():
            sys.exit(f"--resume: not a directory: {run_dir}")

    summary_path = run_dir / "summary.csv"
    if not summary_path.exists():
        sys.exit(f"--resume: {summary_path.relative_to(_ROOT).as_posix()} does not exist; nothing to resume")

    with summary_path.open("r", newline="", encoding="utf-8") as f:
        header = next(csv.reader(f), [])
    if header != SUMMARY_COLUMNS:
        sys.exit(
            "--resume: existing summary.csv header does not match the current schema; "
            "refusing to append misaligned rows.\n"
            f"  existing: {header}\n"
            f"  current:  {SUMMARY_COLUMNS}"
        )
    return run_dir, True


def _completed_instances(run_dir):
    return {(p.parent.name, p.stem) for p in run_dir.glob("*_blowup/*.json")}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--resume",
        nargs="?",
        const=_LATEST,
        default=None,
    )
    parser.add_argument(
        "--skip-decomposition",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    run_dir, resume = _resolve_run_dir(args.resume)
    configs = [c for c in CONFIGS if not (args.skip_decomposition and c["name"] == "decomposition")]
    json_paths = select_balanced_instances()

    done = _completed_instances(run_dir) if resume else set()
    pending = [p for p in json_paths if (p.parent.name, p.stem) not in done]

    if resume:
        print(f"Resuming {run_dir.relative_to(_ROOT).as_posix()} "
              f"({len(done)} instances already complete, {len(pending)} remaining)")
    if args.skip_decomposition:
        print("Skipping decomposition runs (--skip-decomposition)")
    print(f"Running {len(pending)} instances x {len(configs)} configs = {len(pending) * len(configs)} runs")
    print(f"Per-run time limit: {TIMEOUT_SEC} s")
    print(f"Writing results to {run_dir.relative_to(_ROOT).as_posix()}\n")

    if not pending:
        print("Nothing to do: every selected instance is already recorded.")
        return

    summary_path = run_dir / "summary.csv"
    with summary_path.open("a" if resume else "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=SUMMARY_COLUMNS, extrasaction="ignore")
        if not resume:
            writer.writeheader()
            csv_file.flush()

        for i, json_path in enumerate(pending, start=1):
            info = discover_instance(json_path)
            print(f"[{i}/{len(pending)}] {info['blowup_bin']}/{info['name']}  (blowup={info['blowup']:.2f})")

            try:
                per_config_results = {cfg["name"]: run_config(info, cfg) for cfg in configs}
                out_path = write_instance_json(run_dir, info, per_config_results)
                for row in flatten_for_csv(info, per_config_results, configs):
                    writer.writerow(row)
                csv_file.flush()
                print(f"  wrote {out_path.relative_to(_ROOT).as_posix()}\n")
            except Exception as exc:  # noqa: BLE001 - one bad instance must not abort the sweep
                print(f"  !! skipping {info['name']} after error: {type(exc).__name__}: {exc}\n")
                continue

    print(f"Done. Summary: {summary_path.relative_to(_ROOT).as_posix()}")


if __name__ == "__main__":
    main()
