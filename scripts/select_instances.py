import argparse
import json
import random
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CANDIDATE_ROOT = Path(__file__).resolve().parent.parent / "candidate_instances"
OUTPUT_ROOT    = Path(__file__).resolve().parent.parent / "instances_json"
SAMPLES_PER_BIN = 10
MASTER_SEED    = 42

BIN_DIRS = {
    "1-2":  "0_low_blowup",
    "2-10": "1_medium_blowup",
    ">10":  "2_high_blowup",
}


# ---------------------------------------------------------------------------
# Binning
# ---------------------------------------------------------------------------
def load_and_bin():
    candidates = []
    for path in CANDIDATE_ROOT.glob("*/*.json"):
        with path.open() as f:
            candidates.append(json.load(f))

    bins = {"1-2": [], "2-10": [], ">10": []}
    for c in candidates:
        blowup = c["blowup"]
        if blowup < 2:
            bins["1-2"].append(c)
        elif blowup < 10:
            bins["2-10"].append(c)
        else:
            bins[">10"].append(c)

    return bins


# ---------------------------------------------------------------------------
# Printing
# ---------------------------------------------------------------------------
def print_bins(bins):
    for bin_name, instances in bins.items():
        print(f"\n=== Blowup {bin_name} ({len(instances)} instances) ===")
        print(f"{'name':<30} {'problem_type':<20} {'DFA':<8} {'blowup':<10}")
        print("-" * 70)
        for c in sorted(instances, key=lambda x: x["blowup"]):
            print(
                f"{c['name']:<30} "
                f"{c['problem_type']:<20} "
                f"DFA={c['dfas'][0]['Q']:<6} "
                f"blowup={c['blowup']:.2f}x"
            )

    print(f"\nTotal: {sum(len(v) for v in bins.values())} candidates")
    for bin_name, instances in bins.items():
        print(f"  {bin_name}: {len(instances)}")


# ---------------------------------------------------------------------------
# Sampling and Writing
# ---------------------------------------------------------------------------
def sample_and_write(bins, seed, samples_per_bin):
    rng = random.Random(seed)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    for bin_name, instances in bins.items():
        out_dir = OUTPUT_ROOT / BIN_DIRS[bin_name]
        out_dir.mkdir(exist_ok=True)

        n = min(samples_per_bin, len(instances))
        if n < samples_per_bin:
            print(f"Warning: bin {bin_name} has only {n} instances, wanted {samples_per_bin}")

        sampled = rng.sample(instances, n)
        for c in sampled:
            path = out_dir / f"{c['name']}.json"
            with path.open("w") as f:
                json.dump(c, f, indent=2)

        print(f"Wrote {n} instances to {out_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Select instances from candidate pool.")
    parser.add_argument("--seed", type=int, default=MASTER_SEED,
                        help=f"Master RNG seed (default: {MASTER_SEED})")
    parser.add_argument("--samples-per-bin", type=int, default=SAMPLES_PER_BIN,
                        help=f"Number of instances to sample per blowup bin (default: {SAMPLES_PER_BIN})")
    args = parser.parse_args()

    bins = load_and_bin()
    print_bins(bins)
    sample_and_write(bins, seed=args.seed, samples_per_bin=args.samples_per_bin)