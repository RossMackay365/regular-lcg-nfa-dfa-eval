"""
Filter out instances that are infeasible for the experimental matrix. Two checks:

  1) Decomposition Complexity Ceiling - Decomposition Cannot Feasibly Flatten.
  2) UNSAT Check (CP-SAT) - Drop UNSAT Instances.

CLI:
  python scripts/filter_infeasible.py                # default 120s/instance CP-SAT timeout
  python scripts/filter_infeasible.py --timeout 300  # raise per-instance CP-SAT limit
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

_SCRIPTS_ROOT = Path(__file__).resolve().parent
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))


# ---------------------------------------------------------------------------
# Paths & Constants
# ---------------------------------------------------------------------------
_ROOT       = Path(__file__).resolve().parent.parent
MODELS_ROOT = _ROOT / "models"
JSON_ROOT   = _ROOT / "instances_json"
DZN_ROOT    = _ROOT / "instances_dzn"

CPSAT_SOLVER_ID = "cp-sat"
DEFAULT_TIMEOUT = 120
MAX_DECOMP_COST = 1_000_000


# ---------------------------------------------------------------------------
# Decomposition Complexity
# Proxy for Flatten Time: |seq| * Q * S (Transition Table Cells)
# ---------------------------------------------------------------------------
def decomposition_cost(instance):
    pt = instance["problem_type"]
    p  = instance["params"]
    S  = int(instance["alphabet_size"])
    Q  = max(int(a["Q"]) for a in instance["dfas"])

    if pt == "regex":
        n_constraints  = 1
        seq_length     = int(p["var_count"])
    elif pt == "nonogram":
        h = int(p["height"])
        w = int(p["width"])
        n_constraints  = h + w
        seq_length     = max(h, w)
    elif pt == "polyominoes":
        size           = int(p["size"])
        n_constraints  = int(p["tiles"])
        seq_length     = size * size + size
    else:
        return None

    return n_constraints * Q * S * seq_length


# ---------------------------------------------------------------------------
# MiniZinc Status Parsing
# ---------------------------------------------------------------------------
_UNSAT_STATUSES = {"UNSATISFIABLE", "UNSAT_OR_UNBOUNDED"}


def _parse_status(stdout, exit_code):
    if exit_code != 0:
        return "ERROR"
    solution_seen = False
    last_status = None
    saw_error = False
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg_type = msg.get("type")
        if msg_type == "solution":
            solution_seen = True
        elif msg_type == "status":
            reported = msg.get("status")
            if reported:
                last_status = reported
        elif msg_type == "error":
            saw_error = True
    if saw_error:
        return "ERROR"
    if solution_seen:
        return "SATISFIED"
    if last_status in _UNSAT_STATUSES:
        return "UNSATISFIABLE"
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# CP-SAT Invocation
# ---------------------------------------------------------------------------
def run_cpsat(model_path, dzn_path, timeout_s):
    argv = [
        "minizinc",
        "--solver", CPSAT_SOLVER_ID,
        "--statistics",
        "--json-stream",
        "--time-limit", str(timeout_s * 1000),
        str(model_path),
        str(dzn_path),
    ]
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout_s + 30)
    except subprocess.TimeoutExpired:
        return {"status": "UNKNOWN", "exit_code": -1, "stdout": "", "stderr": "process timeout"}
    status = _parse_status(proc.stdout, proc.returncode)
    return {"status": status, "exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}


# ---------------------------------------------------------------------------
# File Deletion
# ---------------------------------------------------------------------------
def _artefact_paths(json_path):
    bin_name = json_path.parent.name
    name     = json_path.stem
    return [
        json_path,
        DZN_ROOT / "nfa" / bin_name / f"{name}.dzn",
        DZN_ROOT / "dfa" / bin_name / f"{name}.dzn",
    ]


def _delete_instance(json_path):
    actions = []
    for p in _artefact_paths(json_path):
        if not p.exists():
            actions.append((p, "missing"))
            continue
        p.unlink()
        actions.append((p, "deleted"))
    return actions


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Delete instances that are infeasible for the experimental matrix.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help=f"CP-SAT time limit per instance, seconds (default: {DEFAULT_TIMEOUT}).")
    args = parser.parse_args()

    json_paths = sorted(JSON_ROOT.glob("*/*.json"))
    if not json_paths:
        sys.exit(f"No instances found under {JSON_ROOT}")

    print(f"=== Filter Infeasible ===")
    print(f"Decomposition cost ceiling: {MAX_DECOMP_COST:,}")
    print(f"CP-SAT solver: {CPSAT_SOLVER_ID}, timeout {args.timeout}s per instance")
    print(f"Found {len(json_paths)} instances across all problem types")
    print()

    counts = {"SATISFIED": 0, "UNSATISFIABLE": 0, "UNKNOWN": 0, "ERROR": 0, "DECOMP_TOO_LARGE": 0}
    deleted = []
    skipped = []

    for i, json_path in enumerate(json_paths, start=1):
        bin_name = json_path.parent.name
        name     = json_path.stem

        try:
            instance = json.loads(json_path.read_text())
            problem_type = instance["problem_type"]
        except (OSError, json.JSONDecodeError, KeyError) as e:
            print(f"[{i:>4}/{len(json_paths)}] {bin_name}/{name}  SKIP (cannot read problem_type: {e})")
            skipped.append(name)
            continue

        # 1) Decomposition Complexity Check
        cost = decomposition_cost(instance)
        if cost is not None and cost > MAX_DECOMP_COST:
            counts["DECOMP_TOO_LARGE"] += 1
            print(f"[{i:>4}/{len(json_paths)}] {bin_name}/{name}  DECOMP_TOO_LARGE  (cost={cost:,} > {MAX_DECOMP_COST:,})")
            for p, action in _delete_instance(json_path):
                print(f"           -> {action}: {p.relative_to(_ROOT).as_posix()}")
            deleted.append(name)
            continue

        # 2) CP-SAT Feasibility Check
        model_path = MODELS_ROOT / f"{problem_type}.mzn"
        dzn_path   = DZN_ROOT / "dfa" / bin_name / f"{name}.dzn"
        if not model_path.exists():
            print(f"[{i:>4}/{len(json_paths)}] {bin_name}/{name}  SKIP (model missing: {model_path.relative_to(_ROOT).as_posix()})")
            skipped.append(name)
            continue
        if not dzn_path.exists():
            print(f"[{i:>4}/{len(json_paths)}] {bin_name}/{name}  SKIP (dzn missing: {dzn_path.relative_to(_ROOT).as_posix()})")
            skipped.append(name)
            continue

        result = run_cpsat(model_path, dzn_path, args.timeout)
        status = result["status"]
        counts[status] = counts.get(status, 0) + 1

        line = f"[{i:>4}/{len(json_paths)}] {bin_name}/{name}  {status}"
        if status == "ERROR" and result["stderr"]:
            line += f"  (stderr: {result['stderr'].splitlines()[0][:80]})"
        print(line)

        if status == "UNSATISFIABLE":
            for p, action in _delete_instance(json_path):
                print(f"           -> {action}: {p.relative_to(_ROOT).as_posix()}")
            deleted.append(name)

    print()
    print("=== Summary ===")
    for status in ("SATISFIED", "UNSATISFIABLE", "UNKNOWN", "ERROR", "DECOMP_TOO_LARGE"):
        if counts.get(status, 0):
            print(f"  {status:<18} {counts[status]}")
    if skipped:
        print(f"  Skipped:           {len(skipped)} ({', '.join(skipped[:10])}{'...' if len(skipped) > 10 else ''})")
    if deleted:
        print(f"  Deleted:           {len(deleted)} ({', '.join(deleted[:10])}{'...' if len(deleted) > 10 else ''})")


if __name__ == "__main__":
    main()
