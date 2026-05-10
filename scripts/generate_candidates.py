import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from generators import shift_scheduling, regex


MASTER_SEED = 42
TARGET_PER_PROBLEM = 100

GENERATORS = [
    shift_scheduling,
    regex,
]


def main():
    for gen in GENERATORS:
        print(f"Generating {gen.PROBLEM_TYPE}...")
        gen.generate_candidates(seed=MASTER_SEED, target_count=TARGET_PER_PROBLEM)


if __name__ == "__main__":
    main()