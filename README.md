## NFA vs DFA Representations for the Regular Constraint in Lazy Clause Generation

This repository is the reproducibility package for Ross Mackay's thesis "NFA vs DFA Representations for the Regular Constraint in Lazy Clause Generation: A Comparative Evaluation".

---

### Pipeline

There are three stages used to produce and test problem instances against NFA, DFA and decomposition-based propagators. The stages are outlined below, and any stage can be rerun in isolation to ensure reproducibility.

* **Stage 1 — `generate_candidates.py`**. Calls the respective generators for each problem type from `scripts/generators/{problem_type}.py`, which generate the instances, building the per-instance NFA(s) and minimal DFA(s) via `scripts/automata_construction.py`, records the blowup ratio, and writes one JSON per instance directly into the blowup-bin folder it belongs to: `instances_json/{blowup}/{name}.json`. Bins are assigned from the measured blowup ratio against the thresholds in `scripts/blowup_bins.py`.
* **Stage 2 — `generate_dzn.py`**. Reads each `instances_json/{blowup}/{name}.json` and emits two `.dzn` files: `instances_dzn/nfa/{blowup}/{name}.dzn` (NFA transition tables) and `instances_dzn/dfa/{blowup}/{name}.dzn` (minimal DFA transition tables). Both share the same problem parameters, only the automata representation differs.
* **Stage 3 — `run_experiments.py`**. Sub-samples each blowup bin down to `min(|bin|)` instances using a seeded random draw so every bin contributes the same number of instances. For each selected instance, runs three configurations against `models/{problem_type}.mzn`: NFA propagator (NFA `.dzn`, `mode=1`), DFA propagator (DFA `.dzn`, `mode=0`), and solver decomposition (DFA `.dzn`, `mode=0`, with solver configured for decomposition).

---

### Model Representation

Every `.mzn` in `models/` follows the same convention so a single `.dzn` schema can support the same model file under either propagator:

* **`int: mode`** — `0` selects `regular` (DFA), `1` selects `regular_nfa` (NFA). The model body branches on `mode` inside each constraint.
* **`int: Q`** — state count (per-instance maximum across the instance's automata, with padding for smaller automata).
* **`int: S`** — alphabet size. Variables in the model use domain `1..S`.
* **`d_dfa`, `d_nfa`** — transition tables matching the standard MiniZinc signatures:
  * `array[1..Q, 1..S] of int: d_dfa` (DFA — single next state)
  * `array[1..Q, 1..S] of set of int: d_nfa` (NFA — set of next states)

For **single-constraint** problem types (`regex`) these are flat: one `q0`, one `F`, one 2D `d_dfa`, one 2D `d_nfa`.

For **multi-constraint** problem types (`nonograms`, `polyominoes`) the K independent automata are packed in 3D arrays:

```minizinc
array[1..K] of int: q0;
array[1..K] of set of int: F;
array[1..K, 1..Q, 1..S] of int: d_dfa;
array[1..K, 1..Q, 1..S] of set of int: d_nfa;
```

Each `regular(...)` call uses the K-th automaton by slicing its 2D transition table. Q is the maximum number of states across all automata in the instance and smaller automata are padded with 0 for DFA dead states or {} for NFA empty transitions. S is the shared alphabet for the entire instance so every automaton uses the same set of symbols.

---

### Problem Types

Three problem types, all selected or restricted to be regular-dominated:

* nonograms
* polyominoes
* regex

---

### Experimental Matrix

Instances are binned along a single axis: **blowup ratio**, measured as minimal DFA states divided by reduced NFA states.

| Bin    | Range      |
|--------|------------|
| Low    | < 2x       |
| Medium | 2x to 10x  |
| High   | > 10x      |

Because bin sizes are typically uneven across problem types, `run_experiments.py` draws a seeded random sub-sample of size `min(|bin|)` from each bin at run time so every bin contributes the same number of instances to the experiment. Bin assignment is empirical: every instance is binned based on its measured blowup, regardless of the problem type it was generated from.

For problem types with multiple regular constraints per instance (nonograms, polyominoes), the per-instance blowup used for binning is aggregated across constraints (see each generator for its exact aggregation). Per-constraint detail is preserved in the instance `.json`.

#### NFA construction

The denominator uses a Glushkov NFA reduced with right-bisimulation reduction (rEquivNFA in FAdo). This preserves the language, runs in polynomial time, and keeps the automaton nondeterministic. Raw Glushkov NFAs contain structural redundancy that a minimal DFA removes, so comparing against them can underestimate determinisation cost. Computing the true minimum NFA is PSPACE-complete, so bisimulation reduction is a practical approximation: it compares the smallest NFA we can efficiently build with the minimal DFA.

---

### Directory Layout

**`models/{problem_type}.mzn`**
One model per problem type. Same model file is used for NFA, DFA, and decomposition runs. Only the data file and the `mode` parameter differ.

**`instances_json/{blowup}/{name}.json`**
Stage 1 output. Every generated instance, stratified by blowup bin. Each file contains the problem type parameters, NFA(s), minimal DFA(s), per-constraint and per-instance blowup ratios, and generator seed. This file is the source of truth for the problem, with both dzn files generated from it.

**`instances_dzn/nfa/{blowup}/{name}.dzn`**
Stage 2 output. Data file for the NFA-propagator run. Contains the NFA transition tables plus problem parameters and per-constraint `q0` / `F` arrays.

**`instances_dzn/dfa/{blowup}/{name}.dzn`**
Stage 2 output. Data file for the DFA-propagator run and the decomposition run. Contains the minimal DFA transition tables, with the same shape as the NFA `.dzn`.

Blowup directories are numbered for sort order: `0_low_blowup`, `1_medium_blowup`, `2_high_blowup`.

---

### Statistics

Each run records ten solver statistics emitted by Pumpkin via MiniZinc's `--json-stream` output. They group into three categories tracking different aspects of solver behaviour:

* **Overall performance.** `solveTime` (seconds inside the solver), `flatTime` (seconds spent flattening the MiniZinc model to FlatZinc), and `nodes` (search tree size).
* **Search and learning.** `propagations` (domain updates performed by constraint propagators), `failures` (conflicts encountered), `restarts` (times the solver discarded its current assignment and restarted from depth 0, keeping learned clauses), and `nogoods` (learned clauses generated from those conflicts).
* **Clause quality.** `AverageLearnedNogoodLength` (mean literal count of learned clauses), `AverageLbd` (mean Literal Block Distance — the standard CDCL clause-quality measure), and `AverageBacktrackAmount` (mean backtrack distance per failure).

Each invocation of `run_experiments.py` writes into a fresh timestamped run directory `results/{YYYY-MM-DD_HH-MM-SS}/` so reruns never overwrite prior results. The per-instance JSON at `results/{YYYY-MM-DD_HH-MM-SS}/{blowup}/{name}.json` retains the full statistics dictionary alongside raw stdout/stderr, so additional metrics can be added to `results/{YYYY-MM-DD_HH-MM-SS}/summary.csv` without rerunning the experiments.

---

### Reproducibility

A single master seed drives all randomised generation and the run-time bin sampling, and is recorded in every instance `.json`. Rerunning the pipeline from that seed reproduces the generated instances, the `.dzn` files, and the per-bin sample chosen by `run_experiments.py` exactly. This ensures full reproducibility of the entire experimental data set, and experimental results.

Stage 1 scripts (`generate_candidates.py` and each `scripts/generators/{problem_type}.py`) accept `--seed` and `--target-count` CLI flags so an alternate seed or candidate-pool size can be run without modifying the code. Defaults match the recorded master seed (71) and the standard maximum per-problem target (100).