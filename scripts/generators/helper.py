import json
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Output Location
# ---------------------------------------------------------------------------
OUTPUT_ROOT = Path(__file__).resolve().parent.parent.parent / "instances_json"


# ---------------------------------------------------------------------------
# Blowup Bin Helpers
# ---------------------------------------------------------------------------
BIN_DIRS = {
    "low":    "0_low_blowup",
    "medium": "1_medium_blowup",
    "high":   "2_high_blowup",
}


def bin_for(blowup):
    if blowup < 2:
        return "low"
    if blowup < 10:
        return "medium"
    return "high"


def bin_dir_for(blowup):
    return BIN_DIRS[bin_for(blowup)]


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------
def _make_serialisable(obj):
    # Recursively Convert Sets, Tuples, Keys into JSON-Serialisable Form
    if isinstance(obj, (set, frozenset)):
        return sorted(_make_serialisable(x) for x in obj)
    if isinstance(obj, (tuple, list)):
        return [_make_serialisable(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _make_serialisable(v) for k, v in obj.items()}
    return obj


def serialize_automaton(automaton_tuple):
    Q, S_size, d, q0, F = automaton_tuple
    return {
        "Q":  int(Q),
        "S":  int(S_size),
        "d":  _make_serialisable(d),
        "q0": int(q0),
        "F":  sorted(int(s) for s in F),
    }


# ---------------------------------------------------------------------------
# Construction Metrics
# ---------------------------------------------------------------------------
CONSTRUCTION_STEPS = ("nfa_glushkov", "nfa_rbisim", "dfa_subset", "dfa_min")


def assemble_metrics(per_constraint_metrics):
    out = {}
    for step in CONSTRUCTION_STEPS:
        ms_key     = f"{step}_ms"
        states_key = f"{step}_states"
        ms_list     = [float(m[ms_key])     for m in per_constraint_metrics]
        states_list = [int(m[states_key]) for m in per_constraint_metrics]
        out[step] = {
            "ms":           ms_list,
            "ms_total":     float(sum(ms_list)),
            "states":       states_list,
            "states_total": int(sum(states_list)),
        }
    return out


# ---------------------------------------------------------------------------
# JSON Formatting
# ---------------------------------------------------------------------------
_PRIMITIVE = (int, float, str, bool, type(None))


def _is_primitive_list(v):
    return isinstance(v, list) and all(isinstance(e, _PRIMITIVE) for e in v)


def _dump_instance(data):
    placeholders = {}

    def compact(obj):
        token = f"__COMPACT_{len(placeholders)}__"
        placeholders[token] = json.dumps(obj, separators=(",", ":"))
        return token

    def walk(obj):
        if isinstance(obj, dict):
            return {k: walk(v) for k, v in obj.items()}
        if isinstance(obj, list):
            if not obj:
                return []
            if all(isinstance(e, _PRIMITIVE) for e in obj):
                return compact(obj)
            if all(_is_primitive_list(e) for e in obj):
                return compact(obj)
            return [walk(v) for v in obj]
        return obj

    text = json.dumps(walk(data), indent=2)
    for token, c in placeholders.items():
        text = text.replace(f'"{token}"', c)
    return text


# ---------------------------------------------------------------------------
# Generator Progress Reporting
# ---------------------------------------------------------------------------
def print_generator_header(problem_type, target_count, seed):
    print(f"=== Generating {problem_type} (target={target_count}, seed={seed}) ===")
    print(f"Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()


def print_generator_progress(counter, target_count, name, params_str, blowup, elapsed_s):
    print(
        f"[{counter:>4}/{target_count}] {name}"
        f"  {params_str}"
        f"  blowup={blowup:.2f}"
        f"  ({elapsed_s:.1f}s)"
    )


def print_generator_footer(counter, skip_counter, total_elapsed_s):
    mins, secs = divmod(total_elapsed_s, 60)
    print()
    print(f"Finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total time: {int(mins)}m {secs:.1f}s")
    print(f"Done. {counter} instances generated, {skip_counter} skipped.")


# ---------------------------------------------------------------------------
# File Writing
# ---------------------------------------------------------------------------
def write_instance(instance):
    bin_dir = OUTPUT_ROOT / bin_dir_for(instance["blowup"])
    bin_dir.mkdir(parents=True, exist_ok=True)
    path = bin_dir / f"{instance['name']}.json"
    if path.exists():
        return False
    with path.open("w") as f:
        f.write(_dump_instance(instance))
    return True