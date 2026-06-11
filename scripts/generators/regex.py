"""
Regex Instance Generator

Generates instances for the regex regular constraint benchmark. Each instance
is K = 2 `regular` constraints over ONE shared variable array of length
var_count, solved as `maximize sum(weights[i] * variables[i])`:

  1. Anchor regex  (1|...|k)* anchor (1|...|k)^n  over the alphabet {1..k}.

  2. Cardinality cap "exactly t occurrences of symbol c" over the same alphabet {1..k}.

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
    is_jointly_feasible,
    print_generator_footer,
    print_generator_header,
    print_generator_progress,
    serialize_automaton,
    write_instance,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PROBLEM_TYPE   = "regex"
N_CONSTRAINTS  = 2 

MAX_DFA_STATES = 150_000
N_VALUES = [4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
K_VALUES = [2, 3]
M_VALUES = [2, 3]

VAR_COUNT_MIN = 18
VAR_COUNT_MAX = 23


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

def _build_cardinality(k, c, t):
    others = [str(i) for i in range(1, k + 1) if i != c]
    rest   = "(" + "|".join(others) + ")"
    parts  = [f"{rest}*"]
    for _ in range(t):
        parts.append(str(c))
        parts.append(f"{rest}*")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Sampling Helpers
# ---------------------------------------------------------------------------
def _var_count(rng, min_length):
    return max(min_length, rng.randint(VAR_COUNT_MIN, VAR_COUNT_MAX))

# Map an anchor tuple to its canonical alphabet-relabeling form.
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


def _sample_instance(rng):
    n         = rng.choice(N_VALUES)
    k         = rng.choice(K_VALUES)
    m         = rng.choice(M_VALUES)
    anchor    = tuple(rng.randint(1, k) for _ in range(m))
    var_count = _var_count(rng, n + m)

    card_symbol = rng.randint(1, k)
    card_count  = rng.randint(max(1, var_count // 4), max(1, 3 * var_count // 4))

    regex_list = [
        _build_cyclic(n, k, anchor),
        _build_cardinality(k, card_symbol, card_count),
    ]
    param = {
        "n": n, "k": k, "m": m, "anchor": anchor,
        "card_symbol": card_symbol, "card_count": card_count,
    }
    return regex_list, var_count, param

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

        regex_list, var_count, param = _sample_instance(rng)

        # Dedup on (n, k, m, canonical anchor pattern, card symbol, card count).
        key = (
            param["n"], param["k"], param["m"], _canonical_pattern(param["anchor"]),
            param["card_symbol"], param["card_count"], var_count,
        )
        if key in seen:
            skip_counter += 1
            continue

        if _predicted_dfa_states(param["n"], param["k"], param["m"]) > MAX_DFA_STATES:
            skip_counter += 1
            continue

        instance_start = time.perf_counter()

        sigma = [str(i) for i in range(1, param["k"] + 1)]
        result = construct_automata(
            regex_list,
            sigma_extra=sigma,
            feasibility_var_counts=[var_count] * len(regex_list),
        )
        if result is None:
            skip_counter += 1
            continue
        nfa_tuples, dfa_tuples, metrics = result

        if not is_jointly_feasible(nfa_tuples, var_count):
            skip_counter += 1
            continue

        total_nfa = sum(t[0] for t in nfa_tuples)
        total_dfa = sum(t[0] for t in dfa_tuples)
        blowup = total_dfa / total_nfa

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
                "card_symbol":   param["card_symbol"],
                "card_count":    param["card_count"],
                "var_count":     var_count,
                "n_constraints": N_CONSTRAINTS,
                "alphabet_size": param["k"],
            },
            "alphabet_size": param["k"],
            "nfas":          [serialize_automaton(t) for t in nfa_tuples],
            "dfas":          [serialize_automaton(t) for t in dfa_tuples],
            "blowup":        blowup,
            "construction":  assemble_metrics(metrics),
        })
        counter += 1
        anchor_str = "(" + ",".join(str(a) for a in param["anchor"]) + ")"
        params_str = (
            f"n={param['n']} k={param['k']} m={param['m']}"
            f" anchor={anchor_str} card={param['card_symbol']}x{param['card_count']}"
            f" var_count={var_count}"
        )
        print_generator_progress(counter, target_count, f"regex_{counter - 1}", params_str, blowup, instance_elapsed)

    print_generator_footer(counter, skip_counter, time.perf_counter() - total_start)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate regex instances.")
    parser.add_argument("--seed", type=int, default=71, help="Master RNG seed (default: 71)")
    parser.add_argument("--target-count", type=int, default=100, help="Target number of instances to generate (default: 100)")
    args = parser.parse_args()
    generate_instances(seed=args.seed, target_count=args.target_count)
