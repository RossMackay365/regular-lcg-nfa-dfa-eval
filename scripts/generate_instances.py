import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from generators import regex, nonogram, polyominoes


MASTER_SEED = 71
MAX_TARGET_PER_PROBLEM = 100

GENERATORS = [
    regex,
    nonogram,
    polyominoes,
]


def main(seed=MASTER_SEED, target_count=MAX_TARGET_PER_PROBLEM):
    for gen in GENERATORS:
        print(f"Generating {gen.PROBLEM_TYPE}...")
        gen.generate_instances(seed=seed, target_count=target_count)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate instances across all problem types.")
    parser.add_argument("--seed", type=int, default=MASTER_SEED, help=f"Master RNG seed (default: {MASTER_SEED})")
    parser.add_argument("--target-count", type=int, default=MAX_TARGET_PER_PROBLEM, help=f"Target instances per problem type (default: {MAX_TARGET_PER_PROBLEM})")
    args = parser.parse_args()
    main(seed=args.seed, target_count=args.target_count)