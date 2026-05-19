"""
Shift Scheduling Regex Generator

Generates candidate instances for the shift-scheduling regular constraint
benchmark. Each candidate contains one or more k-step shift recovery regexes over the
alphabet {1=Day, 2=Night, 3=Evening, 4=Rest}.

Problem Statement: somewhere in the schedule, a trigger shift T occurs, and exactly
k days later there is a rest day (4). Generated instances always have k >= 4 to ensure blowup >= 1.

Each instance contains 2-3 constraints with distinct (T, k) pairs,
and blowup is summed across constraints.

CLI: python shift_scheduling.py [--seed 42] [--target-count 100]
"""

import argparse
import random
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.automata_construction import construct_automata
from scripts.generators.helper import (serialize_automaton, write_candidate)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PROBLEM_TYPE = "shift_scheduling"
S = 4                       # 1=Day  2=Night  3=Evening  4=Rest
ANY_CLASS = "(1|2|3|4)"     # Wildcard for Any Shift (FAdo doesn't accept [1-4])
TRIGGER_SHIFTS = [2, 3]     # Night and Evening - Recovery Triggers
K_VALUES = [4, 5, 6]


# ---------------------------------------------------------------------------
# Regex Builder
# ---------------------------------------------------------------------------
def _build_constraint(trigger, k):
    """
    Pattern: (1|2|3|4)* T (1|2|3|4)^k 4 (1|2|3|4)*
    where T is the trigger shift and k is the recovery gap.
    """
    middle = " ".join([ANY_CLASS] * k)
    return f"{ANY_CLASS}* {trigger} {middle} 4 {ANY_CLASS}*"

# ---------------------------------------------------------------------------
# Sampling Helper
# ---------------------------------------------------------------------------
# Relative probabilities for the number of constraints per instance.
N_CONSTRAINTS_CHOICES = [2, 3]
N_CONSTRAINTS_WEIGHTS = [2.0, 1.0]

# Randomly Choose Sequence Length from 1 - 5 Weeks
def _var_count(rng):
    return rng.choice([7, 14, 21, 28, 35])


# Sample Pair of Trigger and K, Excluding Already-Used Pairs
def _sample_tk_pair(rng, exclude):
    exclude = exclude or set()
    available = [(t, k) for t in TRIGGER_SHIFTS for k in K_VALUES if (t, k) not in exclude]
    return rng.choice(available)

# Sample Problem Instance: Set of Regexes, Variable Count, and Params Info
def _sample_instance(rng):
    n = rng.choices(N_CONSTRAINTS_CHOICES, weights=N_CONSTRAINTS_WEIGHTS, k=1)[0]
    used = set()
    regexes = []
    params = []

    for _ in range(n):
        t, k = _sample_tk_pair(rng, exclude=used)
        used.add((t, k))
        regexes.append(_build_constraint(t, k))
        params.append({"trigger": t, "k": k})
    return regexes, _var_count(rng), params


# ---------------------------------------------------------------------------
# Main Generator - Returns Dictionary with Candidate Info and Automata
# ---------------------------------------------------------------------------
def generate_candidates(seed, target_count=100):
    rng = random.Random(seed)
    seen = set()
    counter = 0

    # Repeats Up to 30x Target Count to Ensure Sufficient Valid Candidates
    for _ in range(target_count * 30):
        if counter >= target_count:
            break

        regexes, var_count, constraint_params = _sample_instance(rng)

        # Handle Duplicate Problems
        key = frozenset(regexes)
        if key in seen:
            continue

        # Construct Automata (Automata Construction Skips UNSAT Instances)
        result = construct_automata(regexes, var_count)
        if result is None:
            continue
        nfa_tuples, dfa_tuples = result

        # Determine Blowup (Blowup Summed Across Constraints)
        total_nfa = sum(nfa[0] for nfa in nfa_tuples)
        total_dfa = sum(dfa[0] for dfa in dfa_tuples)
        blowup = total_dfa / total_nfa

        seen.add(key)
        write_candidate({
            "problem_type": PROBLEM_TYPE,
            "name":         f"shift_scheduling_{counter}",
            "seed":         seed,
            "params": {
                "constraints":   constraint_params,
                "var_count":     var_count,
                "alphabet_size": S,
            },
            "alphabet_size": S,
            "nfas":   [serialize_automaton(t) for t in nfa_tuples],
            "dfas":   [serialize_automaton(t) for t in dfa_tuples],
            "blowup": blowup,
        })
        counter += 1
        print("Generated instance: " + str(counter) + " with blowup: " + str(blowup))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate shift-scheduling candidate instances.")
    parser.add_argument("--seed", type=int, default=42, help="Master RNG seed (default: 42)")
    parser.add_argument("--target-count", type=int, default=100, help="Target number of candidates to generate (default: 100)")
    args = parser.parse_args()
    generate_candidates(seed=args.seed, target_count=args.target_count)