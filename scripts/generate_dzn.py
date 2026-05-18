"""
Generate MiniZinc .dzn data files from selected instance JSONs.

For each problem instance, two .dzn files are generated:

  1) DFA Representation: Mode = 0, populated d_dfa, empty d_nfa.
  2) NFA Representation: Mode = 1, populated d_nfa, empty d_dfa.

These files are then written too the instances_dzn folder.
"""

import json
from pathlib import Path


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parent.parent
INSTANCES_JSON_ROOT = _ROOT / "instances_json"
INSTANCES_DZN_ROOT  = _ROOT / "instances_dzn"


# ---------------------------------------------------------------------------
# 1. MiniZinc Literal Formatters
# ---------------------------------------------------------------------------
def fmt_set(values):
    if not values:
        return "{}"
    return "{" + ", ".join(str(int(v)) for v in sorted(values)) + "}"


def _fmt_transition_cell(transition_cell, as_sets):
    return fmt_set(transition_cell) if as_sets else str(int(transition_cell))


def fmt_2d(rows, cols, transition_cells, *, as_sets):
    lines = []
    for r in range(rows):
        chunk = transition_cells[r * cols : (r + 1) * cols]
        lines.append("  " + ", ".join(_fmt_transition_cell(c, as_sets) for c in chunk))
    return f"array2d(1..{rows}, 1..{cols}, [\n" + ",\n".join(lines) + "\n])"


def fmt_3d(d1, d2, d3, transition_cells, *, as_sets):
    slices = []
    for k in range(d1):
        rows = []
        for r in range(d2):
            start = k * d2 * d3 + r * d3
            chunk = transition_cells[start : start + d3]
            rows.append("    " + ", ".join(_fmt_transition_cell(c, as_sets) for c in chunk))
        slices.append(f"  % k = {k + 1}\n" + ",\n".join(rows))
    return f"array3d(1..{d1}, 1..{d2}, 1..{d3}, [\n" + ",\n\n".join(slices) + "\n])"


# ---------------------------------------------------------------------------
# 2. Transition Table Flatteners
#
# Flattens Transition Tables from Nested JSON Structure to Flat Lists 
# of Transition Cells, to be passed to formatters.
# ---------------------------------------------------------------------------

def flatten_dfa(automaton, Q, S):
    d = automaton["d"]
    flat = []
    for q in range(1, Q + 1):
        row = d.get(str(q), {})
        for s in range(1, S + 1):
            target = row.get(str(s), 0)
            flat.append(int(target) if target is not None else 0)
    return flat


def flatten_nfa(automaton, Q, S):
    d = automaton["d"]
    flat = []
    for q in range(1, Q + 1):
        row = d.get(str(q), {})
        for s in range(1, S + 1):
            flat.append(list(row.get(str(s), [])))
    return flat


# ---------------------------------------------------------------------------
# 3. Per-Problem Body Builders
# ---------------------------------------------------------------------------

def build_regex_body(instance, is_dfa):
    automaton = instance["dfas" if is_dfa else "nfas"][0]

    Q  = int(automaton["Q"])
    S  = int(instance["alphabet_size"])
    q0 = int(automaton["q0"])
    F  = automaton["F"]

    if is_dfa:
        d_dfa = flatten_dfa(automaton, Q, S)
        d_nfa = [[] for _ in range(Q * S)]
    else:
        d_nfa = flatten_nfa(automaton, Q, S)
        d_dfa = [0] * (Q * S)

    return (
        f"var_count = {int(instance['params']['var_count'])};\n"
        f"Q = {Q};\n"
        f"S = {S};\n"
        f"q0 = {q0};\n"
        f"F = {fmt_set(F)};\n"
        f"d_dfa = {fmt_2d(Q, S, d_dfa, as_sets=False)};\n"
        f"d_nfa = {fmt_2d(Q, S, d_nfa, as_sets=True)};\n"
    )


def build_shift_scheduling_body(instance, is_dfa):
    automata = instance["dfas" if is_dfa else "nfas"]
    K = len(automata)
    S = int(instance["alphabet_size"])
    Q = max(int(a["Q"]) for a in automata)

    q0_per_k = [int(a["q0"]) for a in automata]
    F_per_k  = [a["F"] for a in automata]

    if is_dfa:
        d_dfa = []
        for a in automata:
            d_dfa.extend(flatten_dfa(a, Q, S))
        d_nfa = [[] for _ in range(K * Q * S)]
    else:
        d_nfa = []
        for a in automata:
            d_nfa.extend(flatten_nfa(a, Q, S))
        d_dfa = [0] * (K * Q * S)

    q0_array = "[" + ", ".join(str(x) for x in q0_per_k) + "]"
    F_array  = "[" + ", ".join(fmt_set(f) for f in F_per_k) + "]"

    return (
        f"sequence_length = {int(instance['params']['var_count'])};\n"
        f"n_constraints = {K};\n"
        f"Q = {Q};\n"
        f"S = {S};\n"
        f"q0 = {q0_array};\n"
        f"F = {F_array};\n"
        f"d_dfa = {fmt_3d(K, Q, S, d_dfa, as_sets=False)};\n"
        f"d_nfa = {fmt_3d(K, Q, S, d_nfa, as_sets=True)};\n"
    )


BODY_BUILDERS = {
    "regex":            build_regex_body,
    "shift_scheduling": build_shift_scheduling_body,
}


# ---------------------------------------------------------------------------
# 4. Orchestration
# ---------------------------------------------------------------------------

def write_dzn_file(path, problem_type, instance_name, blowup, source_json, is_dfa, body):
    mode = 0 if is_dfa else 1
    representation = "DFA" if is_dfa else "NFA"

    header = (
        f"% Auto-generated by scripts/generate_dzn.py\n"
        f"% problem_type   = {problem_type}\n"
        f"% instance       = {instance_name}\n"
        f"% source_json    = {source_json}\n"
        f"% blowup         = {blowup}\n"
        f"% representation = {representation}\n"
        f"\n"
        f"mode = {mode};\n"
        f"\n"
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + body)


def process_instance(json_path):
    instance = json.loads(json_path.read_text())
    problem_type = instance["problem_type"]
    name = instance["name"]
    blowup_bin = json_path.parent.name
    blowup = instance["blowup"]
    source_json = json_path.relative_to(_ROOT).as_posix()

    build_body = BODY_BUILDERS.get(problem_type)

    for kind, is_dfa in (("nfa", False), ("dfa", True)):
        body = build_body(instance, is_dfa)
        out_path = INSTANCES_DZN_ROOT / kind / blowup_bin / f"{name}.dzn"
        write_dzn_file(out_path, problem_type, name, blowup, source_json, is_dfa, body)


def main():

    json_paths = sorted(INSTANCES_JSON_ROOT.rglob("*.json"))

    for path in json_paths:
        process_instance(path)
        print(f"Generated dzn for {path.relative_to(INSTANCES_JSON_ROOT)}")

    print(f"\nWrote {2 * len(json_paths)} .dzn files under {INSTANCES_DZN_ROOT}.")


if __name__ == "__main__":
    main()
