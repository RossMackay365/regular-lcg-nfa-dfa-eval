"""
Nonogram Instance Generator

Generates candidate instances for the nonogram regular constraint benchmark.
Each candidate is a (width x height) grid puzzle whose row and column hints
each become a regular constraint over the alphabet {1=empty, 2=filled}.

CLI: python nonogram.py [--seed 71] [--target-count 100]

Written by Ross Mackay, with reference to a generator by Julius Gvozdiovas (2025): 
  https://github.com/JulGvoz/nfa-propagator-explanations/blob/227196987c770e9fe682fd581ceed04f93b80b64/experiments/problem_generators/nonogram.py
"""

import argparse
import random
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.automata_construction import (
    regex_to_nfa, nfa_to_min_dfa, encode_nfa, encode_dfa,
)
from scripts.generators.helper import serialize_automaton, write_candidate

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PROBLEM_TYPE = "nonogram"
S = 2
SIZE_VALUES = [
    (5, 5),
    (10, 5), (10, 10),
    (15, 10), (15, 15),
    (20, 15), (20, 20),
    (25, 20), (25, 25),
    (30, 25), (30, 30),
    (35, 30), (35, 35),
]
DENSITY = 0.5


# ---------------------------------------------------------------------------
# Grid + Hint Helpers
# ---------------------------------------------------------------------------
def _generate_grid(width, height, density, rng):
    return [[1 if rng.random() < density else 0 for _ in range(width)] for _ in range(height)]


def _line_hint(line):
    hint = []
    current = 0
    for cell in line:
        if cell:
            current += 1
        elif current != 0:
            hint.append(current)
            current = 0
    if current != 0 or not hint:
        hint.append(current)
    return hint


# ---------------------------------------------------------------------------
# Regex Builder
# ---------------------------------------------------------------------------
# Encode generated hint as a FAdo-compatible regex over {1=empty, 2=filled}.
def _hint_to_regex(hint):
    if hint == [0]:
        return "1*"
    runs = [" ".join(["2"] * n) for n in hint]
    return "1* " + " 1 1* ".join(runs) + " 1*"


# ---------------------------------------------------------------------------
# Automata Construction
# ---------------------------------------------------------------------------
def _build_line_automata(regex_str):
    nfa = regex_to_nfa(regex_str)
    nfa.Sigma.add("2")
    dfa = nfa_to_min_dfa(nfa)
    return encode_nfa(nfa), encode_dfa(dfa)


# ---------------------------------------------------------------------------
# Main Generator
# ---------------------------------------------------------------------------
def generate_candidates(seed, target_count=100):
    rng = random.Random(seed)
    seen = set()
    counter = 0
    skip_counter = 0

    # Repeats Up to 30x Target Count to Ensure Sufficient Valid Candidates
    for _ in range(target_count * 30):
        if counter >= target_count:
            break

        width, height = rng.choice(SIZE_VALUES)
        density = DENSITY

        grid = _generate_grid(width, height, density, rng)
        row_hints = [_line_hint(grid[y]) for y in range(height)]
        col_hints = [_line_hint([grid[y][x] for y in range(height)]) for x in range(width)]

        # Dedup on (width, height, row hints, colum hints)
        key = (
            width, height,
            tuple(tuple(h) for h in row_hints),
            tuple(tuple(h) for h in col_hints),
        )
        if key in seen:
            skip_counter += 1
            continue

        # Build Automata
        nfa_tuples = []
        dfa_tuples = []
        for hint in row_hints + col_hints:
            nfa_tuple, dfa_tuple = _build_line_automata(_hint_to_regex(hint))
            nfa_tuples.append(nfa_tuple)
            dfa_tuples.append(dfa_tuple)

        # Determine Blowup (Summed Across All Row + Column Constraints)
        total_nfa = sum(t[0] for t in nfa_tuples)
        total_dfa = sum(t[0] for t in dfa_tuples)
        blowup = total_dfa / total_nfa

        seen.add(key)
        write_candidate({
            "problem_type": PROBLEM_TYPE,
            "name":         f"nonogram_{counter}",
            "seed":         seed,
            "params": {
                "width":         width,
                "height":        height,
                "density":       density,
                "row_hints":     row_hints,
                "col_hints":     col_hints,
                "alphabet_size": S,
            },
            "alphabet_size": S,
            "nfas":   [serialize_automaton(t) for t in nfa_tuples],
            "dfas":   [serialize_automaton(t) for t in dfa_tuples],
            "blowup": blowup,
        })
        counter += 1
        print(f"Generated nonogram_{counter - 1} ({width}x{height}, d={density}) blowup={round(blowup, 2)}")

    print(f"Done. {counter} candidates, {skip_counter} skipped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate nonogram candidate instances.")
    parser.add_argument("--seed", type=int, default=71, help="Master RNG seed (default: 71)")
    parser.add_argument("--target-count", type=int, default=100, help="Target number of candidates to generate (default: 100)")
    args = parser.parse_args()
    generate_candidates(seed=args.seed, target_count=args.target_count)
