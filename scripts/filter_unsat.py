"""
Filter out UNSAT instances by running CP-SAT on every generated
instance, and delete any that come back UNSATISFIABLE.

Regex and Nonograms are SAT by construction (or by checking when constructing
the automata), so they should all pass. This check is primarily for polyominoes.

CLI:
  python scripts/filter_unsat.py                  # default 60s/instance timeout
  python scripts/filter_unsat.py --timeout 120    # raise per-instance limit
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


# ---------------------------------------------------------------------------
# MiniZinc Status Parsing
# ---------------------------------------------------------------------------
_SOLVER_STATUS_MAP = {
    "SATISFIED":          "SATISFIED",
    "ALL_SOLUTIONS":      "SATISFIED",
    "OPTIMAL_SOLUTION":   "SATISFIED",
    "UNSATISFIABLE":      "UNSATISFIABLE",
    "UNSAT_OR_UNBOUNDED": "UNSATISFIABLE",
    "UNKNOWN":            "UNKNOWN",
    "ERROR":              "ERROR",
}


def _parse_status(stdout, exit_code):
    if exit_code != 0:
        return "ERROR"
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
        if msg.get("type") == "status":
            reported = msg.get("status")
            if reported:
                last_status = reported
        elif msg.get("type") == "error":
            saw_error = True
    if saw_error:
        return "ERROR"
    if last_status is not None:
        return _SOLVER_STATUS_MAP.get(last_status, "UNKNOWN")
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
    parser = argparse.ArgumentParser(description="Filter out provably-UNSAT instances via CP-SAT.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help=f"CP-SAT time limit per instance, seconds (default: {DEFAULT_TIMEOUT}).")
    args = parser.parse_args()

    json_paths = sorted(JSON_ROOT.glob("*/*.json"))
    if not json_paths:
        sys.exit(f"No instances found under {JSON_ROOT}")

    print(f"=== Filter UNSAT ===")
    print(f"CP-SAT solver: {CPSAT_SOLVER_ID}, timeout {args.timeout}s per instance")
    print(f"Found {len(json_paths)} instances across all problem types")
    print()

    counts   = {"SATISFIED": 0, "UNSATISFIABLE": 0, "UNKNOWN": 0, "ERROR": 0}
    deleted  = []
    skipped  = []

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
    for status in ("SATISFIED", "UNSATISFIABLE", "UNKNOWN", "ERROR"):
        if counts.get(status, 0):
            print(f"  {status:<14} {counts[status]}")
    if skipped:
        print(f"  Skipped:       {len(skipped)} ({', '.join(skipped[:10])}{'...' if len(skipped) > 10 else ''})")
    if deleted:
        print(f"  Deleted:       {len(deleted)} ({', '.join(deleted[:10])}{'...' if len(deleted) > 10 else ''})")


if __name__ == "__main__":
    main()
