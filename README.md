## NFA vs DFA Representations for the Regular Constraint in Lazy Clause Generation

This repository is the reproducibility package for Ross Mackay's thesis "NFA vs DFA Representations for the Regular Constraint in Lazy Clause Generation: A Comparative Evaluation".

---

### Pipeline

There are four stages used to produce and test problem instances against NFA, DFA and decomposition-based propagators. The stages are outlined below, and any stage can be rerun in isolation to ensure reproducibility.

* **Stage 1 — `generate_candidates.py`**. Calls the respective generators for each problem type from `scripts/generators/{problem_type}.py`, which generate the instances, building the per-instance NFA(s) and minimal DFA(s) via `scripts/automata_construction.py`, records the blowup ratio, and writes one JSON per candidate to `candidate_instances/{problem_type}/`.
* **Stage 2 — `select_instances.py`**. Reads `candidate_instances/`, bins each candidate by its blowup ratio, and randomly samples 20 candidates per blowup bin under the master seed, writing the chosen instances to `instances_json/{blowup}/`.
* **Stage 3 — `generate_dzn.py`**. Reads each selected `instances_json/{blowup}/{name}.json` and emits two `.dzn` files: `instances_dzn/nfa/{blowup}/{name}.dzn` (NFA transition tables) and `instances_dzn/dfa/{blowup}/{name}.dzn` (minimal DFA transition tables). Both share the same problem parameters, only the automata representation differs.
* **Stage 4 — `run_experiments.py`**. For each selected instance, runs three configurations against `models/{problem_type}.mzn`: NFA propagator (NFA `.dzn`, `mode=1`), DFA propagator (DFA `.dzn`, `mode=0`), and solver decomposition (DFA `.dzn`, `mode=0`, with solver configured for decomposition). 60 instances × 3 configs = 180 runs.

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

For **multi-constraint** problem types (`nonograms`, `pentominoes`, `shift_scheduling`) the K independent automata are packed in 3D arrays:

```minizinc
array[1..K] of int: q0;
array[1..K] of set of int: F;
array[1..K, 1..Q, 1..S] of int: d_dfa;
array[1..K, 1..Q, 1..S] of set of int: d_nfa;
```

Each `regular(...)` call uses the K-th automaton by slicing its 2D transition table. Q is the maximum number of states across all automata in the instance and smaller automata are padded with 0 for DFA dead states or {} for NFA empty transitions. S is the shared alphabet for the entire instance so every automaton uses the same set of symbols.

---

### Problem Types

Four problem types, all selected or restricted to be regular-dominated:

* shift scheduling (k-step rest day constraints)
* nonograms
* pentominoes
* regex

---

### Experimental Matrix

Instances are binned along a single axis: **blowup ratio**, measured as minimal DFA states divided by NFA states (Glushkov Construction).

| Bin    | Range      |
|--------|------------|
| Low    | < 2x       |
| Medium | 2x to 10x  |
| High   | > 10x      |

20 instances per bin, randomly sampled under the master seed, for 60 instances total. Bin assignment is empirical: every candidate is binned based on its measured blowup, regardless of the problem type it was generated from.

For problem types with multiple regular constraints per instance (shift_scheduling, nonograms, pentominoes), the per-instance blowup used for binning is `max_k(|DFA_k| / |NFA_k|)`. Per-constraint detail is preserved in the candidate `.json`.

---

### Directory Layout

**`models/{problem_type}.mzn`**
One model per problem type. Same model file is used for NFA, DFA, and decomposition runs. Only the data file and the `mode` parameter differ.

**`candidate_instances/{problem_type}/{name}.json`**
Stage 1 output. Full candidate pool. Contains problem type parameters, NFA(s), minimal DFA(s), per-constraint and per-instance blowup ratios, and generator seed.

**`instances_json/{blowup}/{name}.json`**
Stage 2 output. The 60 selected instances, named `{blowup}_{index}`. Candidate contents plus the assigned blowup bin and master-seed sample index. This file is the source of truth for the problem, with both dzn files generated from it.

**`instances_dzn/nfa/{blowup}/{name}.dzn`**
Stage 3 output. Data file for the NFA-propagator run. Contains the NFA transition tables plus problem parameters and per-constraint `q0` / `F` arrays.

**`instances_dzn/dfa/{blowup}/{name}.dzn`**
Stage 3 output. Data file for the DFA-propagator run and the decomposition run. Contains the minimal DFA transition tables, with the same shape as the NFA `.dzn`.

Blowup directories are numbered for sort order: `0_low_blowup`, `1_medium_blowup`, `2_high_blowup`.

---

### Reproducibility

A single master seed drives all randomised generation and sampling, and is recorded in every instance `.json`. Rerunning the pipeline from that seed reproduces the candidate pool, the selected 60, and the `.dzn` files exactly. This ensures full reproducibility of the entire experimental data set, and experimental results.
