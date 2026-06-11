"""
Polyominoes Instance Generator

Generates instances for the polyominoes regular constraint benchmark.
Problem generation is based on the minizinc-pentominoes-generator CLI
(Mikael Zayenz Lagerkvist, 2020), which emits random board layouts and 
per-piece regexes encoding legal placements. These regexes are then parsed,
translated into FAdo-compatible syntax, and converted into NFA and minimal
DFA representations via the shared automata construction helpers. 

CLI: python polyominoes.py [--seed 71] [--target-count 100]

Requires:
  minizinc-pentominoes-generator/ submodule, built with `cargo build --release`.

Written by Ross Mackay, with reference to:
  https://github.com/zayenz/minizinc-pentominoes-generator
"""

import argparse
import os
import random
import re
import subprocess
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
PROBLEM_TYPE = "polyominoes"
SIZE_VALUES  = [6, 8, 10, 12]
TILES_VALUES = [4, 5, 6]
STRATEGIES   = ["source", "target", "far", "close"]

_BIN_NAME = "minizinc-pentominoes-generator" + (".exe" if os.name == "nt" else "")
CLI_PATH  = _ROOT / "minizinc-pentominoes-generator" / "target" / "release" / _BIN_NAME


# ---------------------------------------------------------------------------
# CLI Invocation
# ---------------------------------------------------------------------------
def _run_cli(size, tiles, strategy, seed):
    if not CLI_PATH.exists():
        raise FileNotFoundError(
            f"Polyominoes CLI not found at {CLI_PATH}. "
            f"Run `cargo build --release` inside the minizinc-pentominoes-generator submodule."
        )
    try:
        result = subprocess.run(
            [str(CLI_PATH),
             "--size",     str(size),
             "--tiles",    str(tiles),
             "--strategy", strategy,
             "--seed",     str(seed)],
            capture_output=True, text=True, timeout=120,
        )
    except subprocess.TimeoutExpired:
        return None
    if result.returncode != 0:
        return None
    return result.stdout


# ---------------------------------------------------------------------------
# CLI Output Parser
# ---------------------------------------------------------------------------
_SIZE_RE       = re.compile(r"^\s*size\s*=\s*(\d+)\s*;",  re.MULTILINE)
_TILES_RE      = re.compile(r"^\s*tiles\s*=\s*(\d+)\s*;", re.MULTILINE)
_EXPR_BLOCK_RE = re.compile(r"expressions\s*=\s*\[(.*?)\]\s*;", re.DOTALL)
_QUOTED_RE     = re.compile(r'"([^"]+)"')


def _parse_output(text):
    size_m  = _SIZE_RE.search(text)
    tiles_m = _TILES_RE.search(text)
    block_m = _EXPR_BLOCK_RE.search(text)
    if not (size_m and tiles_m and block_m):
        return None
    size  = int(size_m.group(1))
    tiles = int(tiles_m.group(1))
    raw_exprs = _QUOTED_RE.findall(block_m.group(1))
    if len(raw_exprs) != tiles:
        return None
    return size, tiles, raw_exprs


# ---------------------------------------------------------------------------
# Regex Translation (Translating Regexes to FAdo-Compatible Syntax)
# ---------------------------------------------------------------------------
_CHAR_CLASS_RE = re.compile(r"\[([^\[\]]+)\]")
_QUANT_RE      = re.compile(r"(\d+|\([^()]+\))\{(\d+)\}")
_DIGIT_RE      = re.compile(r"\d+")


def _digit_to_letter(d):
    n = int(d)
    if not 1 <= n <= 26:
        raise ValueError(f"Symbol {n} outside supported range 1..26")
    return chr(ord("a") + n - 1)


def _translate_regex(raw):
    out = _CHAR_CLASS_RE.sub(
        lambda m: "(" + "|".join(m.group(1).split()) + ")",
        raw,
    )
    out = _QUANT_RE.sub(
        lambda m: " ".join([m.group(1)] * int(m.group(2))),
        out,
    )
    out = _DIGIT_RE.sub(lambda m: _digit_to_letter(m.group(0)), out)
    return out


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
    for _ in range(target_count * 30):
        if counter >= target_count:
            break

        size     = rng.choice(SIZE_VALUES)
        tiles    = rng.choice(TILES_VALUES)
        strategy = rng.choice(STRATEGIES)
        cli_seed = rng.randrange(2 ** 32)

        instance_start = time.perf_counter()

        text = _run_cli(size, tiles, strategy, cli_seed)
        if text is None:
            skip_counter += 1
            continue

        parsed = _parse_output(text)
        if parsed is None:
            skip_counter += 1
            continue
        out_size, out_tiles, raw_exprs = parsed

        # Dedup on (size, tiles, strategy, seed)
        key = (out_size, out_tiles, tuple(raw_exprs))
        if key in seen:
            skip_counter += 1
            continue

        S = out_tiles + 1
        sigma_extra = [_digit_to_letter(s) for s in range(1, S + 1)]
        regex_list = [_translate_regex(raw) for raw in raw_exprs]
        try:
            result = construct_automata(regex_list, sigma_extra=sigma_extra, feasibility_var_counts=None)
        except Exception as e:
            print(f"  build failed for size={out_size} tiles={out_tiles} strategy={strategy}: {e}")
            skip_counter += 1
            continue
        nfa_tuples, dfa_tuples, metrics_list = result

        # Determine Blowup (Summed Across All Per-Tile Constraints)
        total_nfa = sum(t[0] for t in nfa_tuples)
        total_dfa = sum(t[0] for t in dfa_tuples)
        blowup = total_dfa / total_nfa

        instance_elapsed = time.perf_counter() - instance_start

        seen.add(key)
        write_instance({
            "problem_type":  PROBLEM_TYPE,
            "name":          f"polyominoes_{counter}",
            "seed":          seed,
            "params": {
                "size":          out_size,
                "tiles":         out_tiles,
                "strategy":      strategy,
                "cli_seed":      cli_seed,
                "alphabet_size": S,
            },
            "alphabet_size": S,
            "nfas":          [serialize_automaton(t) for t in nfa_tuples],
            "dfas":          [serialize_automaton(t) for t in dfa_tuples],
            "blowup":        blowup,
            "construction":  assemble_metrics(metrics_list),
        })
        counter += 1
        params_str = f"size={out_size} tiles={out_tiles} strategy={strategy}"
        print_generator_progress(counter, target_count, f"polyominoes_{counter - 1}", params_str, blowup, instance_elapsed)

    print_generator_footer(counter, skip_counter, time.perf_counter() - total_start)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate polyominoes instances.")
    parser.add_argument("--seed", type=int, default=71, help="Master RNG seed (default: 71)")
    parser.add_argument("--target-count", type=int, default=100, help="Target number of instances to generate (default: 100)")
    args = parser.parse_args()
    generate_instances(seed=args.seed, target_count=args.target_count)