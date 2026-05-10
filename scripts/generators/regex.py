"""
Regex Instance Generator

Generates candidates regexes, using a classical blowup 
construction characterised by two parameters, n and k.

Cyclic regex of the form (1|...|k)* anchor (1|...|k)^n,
consisting of a repeated alternation prefix, a fixed anchor
substring, and a length-n suffix over the same alphabet.
"""

import random
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.automata_construction import construct_automata
from scripts.generators.helper import serialize_automaton, write_candidate

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PROBLEM_TYPE = "regex"

# Restrict Weights of N = 11 for Runtime Efficiency (Causes Blowup > 150x, 5min runtime)
N_VALUES  = [5, 6, 7, 8, 9, 10]
K_VALUES = [2, 3, 4, 5, 6, 7, 8]


# ---------------------------------------------------------------------------
# Regex Builder
# ---------------------------------------------------------------------------
# Build Wildcard (1 | 2 | ... | k)
def _build_wildcard(k):
    return "(" + "|".join(str(i) for i in range(1, k + 1)) + ")"

# Build Cyclic Regex
def _build_cyclic(n, k, anchor):
    wild   = _build_wildcard(k)
    suffix = " ".join([wild] * n)
    return f"{wild}* {anchor} {suffix}"


# ---------------------------------------------------------------------------
# Sampling Helpers
# ---------------------------------------------------------------------------
# Return Regex Length, Enforced > Min_Regex_Length
def _var_count(rng, min_length):
    return rng.randint(min_length, min_length * 3)

# Sample Instance - Returns Regex, Variable Count, and Params Info
def _sample_instance(rng):
    n      = rng.choice(N_VALUES)
    k      = rng.choice(K_VALUES)
    anchor = rng.randint(1, k)
    regex  = _build_cyclic(n, k, anchor)
    param  = {"n": n, "k": k, "anchor": anchor}
    return regex, _var_count(rng, n + 1), param


# ---------------------------------------------------------------------------
# Main Generator
# ---------------------------------------------------------------------------
def generate_candidates(seed, target_count=100):
    rng = random.Random(seed)
    seen = set()
    counter = 0

    # Repeats Up to 30x Target Count to Ensure Sufficient Valid Candidates
    for i in range(target_count * 30):
        if counter >= target_count:
            break

        regex, var_count, param = _sample_instance(rng)

        # Remove Duplicate Regexes
        if regex in seen:
            continue

        # Build NFA/DFA
        nfa, dfa = construct_automata(regex)

        # Determine Blowup
        blowup = dfa[0] / nfa[0]

        seen.add(regex)
        write_candidate({
            "problem_type":  PROBLEM_TYPE,
            "name":          f"regex_{counter}",
            "seed":          seed,
            "params": {
                "n":             param["n"],
                "k":             param["k"],
                "anchor":        param["anchor"],
                "var_count":     var_count,
                "alphabet_size": param["k"],
            },
            "alphabet_size": param["k"],
            "nfas":          [serialize_automaton(nfa)],
            "dfas":          [serialize_automaton(dfa)],
            "blowup":        blowup,
        })
        counter += 1
        print("Generated instance: " + str(counter) + " with blowup: " + str(blowup))