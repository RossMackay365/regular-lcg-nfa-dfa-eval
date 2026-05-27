"""
Regex Instance Generator

Generates instances for the regex regular constraint benchmark.
Each instance is a single regex of the form (1|...|k)* anchor (1|...|k)^n
over the alphabet {1..k}, based on a classic DFA blowup construction.

Problem Statement: somewhere near the end of the string, a fixed m-symbol
anchor appears, followed by exactly n wildcard symbols. The DFA must remember
which possible end positions have already matched the anchor, while also
tracking the last m-1 symbols to detect new matches. As a result, the DFA can
grow exponentially in n, while the NFA grows only linearly.

Each instance is parameterised by (n, k, m). Instances whose predicted DFA
size exceeds MAX_DFA_STATES are skipped, and anchors that are equivalent under
alphabet renaming (e.g. (2,1,2) ≡ (1,2,1)) are removed.

CLI: python regex.py [--seed 71] [--target-count 100]
"""

import argparse
import random
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.automata_construction import construct_automata
from scripts.generators.helper import (
    assemble_metrics,
    print_generator_footer,
    print_generator_header,
    print_generator_progress,
    serialize_automaton,
    write_instance,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PROBLEM_TYPE = "regex"

MAX_DFA_STATES = 150_000
N_VALUES = [4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
K_VALUES = [2, 3]
M_VALUES = [2, 3]


# ---------------------------------------------------------------------------
# Regex Builder
# ---------------------------------------------------------------------------
# Build Wildcard (1 | 2 | ... | k)
def _build_wildcard(k):
    return "(" + "|".join(str(i) for i in range(1, k + 1)) + ")"

# Build Regex with Multi-Symbol Anchor
def _build_cyclic(n, k, anchor):
    wild       = _build_wildcard(k)
    suffix     = " ".join([wild] * n)
    anchor_str = " ".join(str(a) for a in anchor)
    return f"{wild}* {anchor_str} {suffix}"


# ---------------------------------------------------------------------------
# Sampling Helpers
# ---------------------------------------------------------------------------
# Return Regex Length, Enforced > Min_Regex_Length
def _var_count(rng, min_length):
    return rng.randint(min_length, min_length * 3)

# Map an anchor tuple to its canonical alphabet-relabeling form.
# E.g. (2, 1, 2) -> (1, 2, 1) and (3, 1, 3) -> (1, 2, 1) — same class.
def _canonical_pattern(anchor):
    mapping = {}
    next_id = 1
    result  = []
    for sym in anchor:
        if sym not in mapping:
            mapping[sym] = next_id
            next_id += 1
        result.append(mapping[sym])
    return tuple(result)

# Sample Instance - Returns Regex, Variable Count, and Params Info
def _sample_instance(rng):
    n      = rng.choice(N_VALUES)
    k      = rng.choice(K_VALUES)
    m      = rng.choice(M_VALUES)
    anchor = tuple(rng.randint(1, k) for _ in range(m))
    regex  = _build_cyclic(n, k, anchor)
    param  = {"n": n, "k": k, "m": m, "anchor": anchor}
    return regex, _var_count(rng, n + m), param

# Upper bound on minimal-DFA size for (Σ)* anchor (Σ)^n with |anchor|=m:
# 2^(n+1) anchor-occurrence patterns over the n+1 end-positions, times k^(m-1)
# possible trailing partial-match states.
def _predicted_dfa_states(n, k, m):
    return (2 ** (n + 1)) * (k ** (m - 1))


# ---------------------------------------------------------------------------
# Main Generator
# ---------------------------------------------------------------------------
def generate_instances(seed, target_count=100):
    rng = random.Random(seed)
    seen = set()
    counter = 0
    skip_counter = 0

    total_start = time.perf_counter()
    print_generator_header(PROBLEM_TYPE, target_count, seed)

    # Repeats Up to 30x Target Count to Ensure Sufficient Valid Instances
    for i in range(target_count * 30):
        if counter >= target_count:
            break

        regex, var_count, param = _sample_instance(rng)

        # Dedup on (n, k, m, canonical anchor pattern) - Avoids Alphabet-Relabelling Equivalence
        key = (param["n"], param["k"], param["m"], _canonical_pattern(param["anchor"]))
        if key in seen:
            skip_counter += 1
            continue

        # Skip combos whose minimal DFA would blow up FAdo's subset construction.
        if _predicted_dfa_states(param["n"], param["k"], param["m"]) > MAX_DFA_STATES:
            skip_counter += 1
            continue

        instance_start = time.perf_counter()

        result = construct_automata([regex], feasibility_var_counts=[var_count])
        if result is None:
            skip_counter += 1
            continue
        nfa_tuples, dfa_tuples, metrics = result
        nfa, dfa = nfa_tuples[0], dfa_tuples[0]

        # Determine Blowup
        blowup = dfa[0] / nfa[0]

        instance_elapsed = time.perf_counter() - instance_start

        seen.add(key)
        write_instance({
            "problem_type":  PROBLEM_TYPE,
            "name":          f"regex_{counter}",
            "seed":          seed,
            "params": {
                "n":             param["n"],
                "k":             param["k"],
                "m":             param["m"],
                "anchor":        list(param["anchor"]),
                "var_count":     var_count,
                "alphabet_size": param["k"],
            },
            "alphabet_size": param["k"],
            "nfas":          [serialize_automaton(nfa)],
            "dfas":          [serialize_automaton(dfa)],
            "blowup":        blowup,
            "construction":  assemble_metrics(metrics),
        })
        counter += 1
        anchor_str = "(" + ",".join(str(a) for a in param["anchor"]) + ")"
        params_str = (
            f"n={param['n']} k={param['k']} m={param['m']}"
            f" anchor={anchor_str} var_count={var_count}"
        )
        print_generator_progress(counter, target_count, f"regex_{counter - 1}", params_str, blowup, instance_elapsed)

    print_generator_footer(counter, skip_counter, time.perf_counter() - total_start)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate regex instances.")
    parser.add_argument("--seed", type=int, default=71, help="Master RNG seed (default: 71)")
    parser.add_argument("--target-count", type=int, default=100, help="Target number of instances to generate (default: 100)")
    args = parser.parse_args()
    generate_instances(seed=args.seed, target_count=args.target_count)
