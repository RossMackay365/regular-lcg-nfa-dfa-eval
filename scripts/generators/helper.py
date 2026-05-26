import json
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
# JSON Formatting
# ---------------------------------------------------------------------------
_PRIMITIVE = (int, float, str, bool, type(None))


def _is_primitive_list(v):
    return isinstance(v, list) and all(isinstance(e, _PRIMITIVE) for e in v)


def _dump_candidate(data):
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
# File Writing
# ---------------------------------------------------------------------------
def write_candidate(candidate):
    bin_dir = OUTPUT_ROOT / bin_dir_for(candidate["blowup"])
    bin_dir.mkdir(parents=True, exist_ok=True)
    path = bin_dir / f"{candidate['name']}.json"
    if path.exists():
        return False
    with path.open("w") as f:
        f.write(_dump_candidate(candidate))
    return True