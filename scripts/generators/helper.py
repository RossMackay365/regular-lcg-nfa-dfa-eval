import json
from pathlib import Path


# ---------------------------------------------------------------------------
# Output Location
# ---------------------------------------------------------------------------
OUTPUT_ROOT = Path(__file__).resolve().parent.parent.parent / "candidate_instances"


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
# Feasibility
# ---------------------------------------------------------------------------

# Takes Transition Step in DFA if Possible
def _dfa_step(d, state, symbol):
    inner = d.get(state) if isinstance(d, dict) else None
    if inner is None:
        return None
    dst = inner.get(symbol) if isinstance(inner, dict) else None
    if dst in (None, 0):
        return None
    return dst

# BFS over DFA - Checks for Reachable Accepting State (and thus feasible solution)
def is_feasible(dfa_tuple, var_count):
    Q, S_size, d, q0, F = dfa_tuple
    accepting = set(F)
    frontier = {q0}
    for _ in range(var_count):
        next_frontier = set()
        for state in frontier:
            for sym in range(1, S_size + 1):
                dst = _dfa_step(d, state, sym)
                if dst is not None:
                    next_frontier.add(dst)
        frontier = next_frontier
        if not frontier:
            return False
    return bool(frontier & accepting)


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
    problem_dir = OUTPUT_ROOT / candidate["problem_type"]
    problem_dir.mkdir(parents=True, exist_ok=True)
    path = problem_dir / f"{candidate['name']}.json"
    if path.exists():
        return False
    with path.open("w") as f:
        f.write(_dump_candidate(candidate))
    return True