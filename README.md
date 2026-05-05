## NFA vs DFA Representations for the Regular Constraint in Lazy Clause Generation

This repository is the reproducibility package for Ross Mackay's thesis "NFA vs DFA Representations for the Regular Constraint in Lazy Clause Generation: A Comparative Evaluation".

---

### Pipeline

There are four stages used to produce and test problem instances against NFA, DFA and decomposition-based propagators. The stages are outlined below, and any stage can be rerun in isolation to ensure reproducibility.

* **Stage 1 — `generate_candidates.py`**. Reads parameter sweeps from each `scripts/generators/{problem_type}.py`, builds the per-instance NFA(s) and minimal DFA(s) via `scripts/automata_helper.py`, records blowup ratio and cyclic/acyclic flag, writes one JSON per candidate to `candidate_instances/{problem_type}/`.
* **Stage 2 — `select_instances.py`**. Reads `candidate_instances/`, runs `scripts/classify.py` to compute the difficulty axis, applies bin thresholds, samples five candidates per (blowup, structure, difficulty) cell under the master seed, writes the chosen instances to `instances_json/{blowup}/`.
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

For **single-constraint** problem types (`shift_scheduling`, `regex`) these are flat: one `q0`, one `F`, one 2D `d_dfa`, one 2D `d_nfa`.

For **multi-constraint** problem types (`nonograms`, `pentominoes`, `car_sequencing`) the K independent automata are packed in 3D arrays:

```minizinc
array[1..K] of int: q0;
array[1..K] of set of int: F;
array[1..K, 1..Q, 1..S] of int: d_dfa;
array[1..K, 1..Q, 1..S] of set of int: d_nfa;
```

Each `regular(...)` call uses the K-th automaton by slicing its 2D transition table. Q is the maximum number of states across all automata in the instance and smaller automata are padded with 0 for DFA dead states or {} for NFA empty transitions. S is the shared alphabet for the entire instance so every automaton uses the same set of symbols.

---

### Problem Types

Five problem types, all selected or restricted to be regular-dominated:

* shift scheduling (individual rules only, no demand/staffing)
* car sequencing (capacity-only)
* nonograms (pure regular composition)
* pentominoes (pure regular composition)
* regex (single regular constraint)

The regex problem type is a synthetic problem introduced to cover cells not reached by the four real-problem types.

---

### Experimental Matrix

| Axis       | Values                                                                        |
|------------|-------------------------------------------------------------------------------|
| Blowup     | low (< 2x), medium (2 to 10x), high (> 10x), measured as DFA / NFA states     |
| Structure  | cyclic or acyclic, by whether the minimal DFA has a non-self-loop cycle       |
| Difficulty | easy or hard, assigned within each (blowup, structure) group                  |

Five instances per cell, sampled under the master seed.

Importantly, the cell assignment is empirical. That means every candidate is binned based on its measured blowup, structure, and difficulty, regardless of the problem type it was generated from. That being said, the problems expected to be found in each cell can be seen below:

|         | Low blowup       | Medium blowup                      | High blowup        |
|---------|------------------|------------------------------------|--------------------|
| Cyclic  | shift scheduling | shift scheduling, car sequencing   | pentominoes, regex |
| Acyclic | nonograms, regex | regex                              | regex              |


For problem types with multiple regular constraints per instance (nonograms, pentominoes, car_sequencing), the per-instance blowup used for binning is `max_k(|DFA_k| / |NFA_k|)`. Per-constraint detail is preserved in the candidate `.json`.

---

### Directory Layout

**`models/{problem_type}.mzn`**
One model per problem type. Same model file is used for NFA, DFA, and decomposition runs. Only the data file and the `mode` parameter differ.

**`candidate_instances/{problem_type}/{name}.json`**
Stage 1 output. Full candidate pool, ~100 per problem type. Contains problem type parameters, NFA(s), minimal DFA(s), per-constraint and per-instance blowup ratios, cyclic/acyclic flag, generator seed. No bin labels and no difficulty measure (those are determined in stage 2).

**`instances_json/{blowup}/{name}.json`**
Stage 2 output. The 60 selected instances, named `{blowup}_{structure}_{difficulty}_{index}`. Candidate contents plus difficulty, assigned bin (blowup, structure, difficulty) and master-seed sample index. This acts as the source of truth for an instance, once it has been selected.

**`instances_dzn/nfa/{blowup}/{name}.dzn`**
Stage 3 output. Data file for the NFA-propagator run. Contains the NFA transition tables plus problem parameters and per-constraint `q0` / `F` arrays.

**`instances_dzn/dfa/{blowup}/{name}.dzn`**
Stage 3 output. Data file for the DFA-propagator run and the decomposition run. Contains the minimal DFA transition tables, with the same shape as the NFA `.dzn`.

Blowup directories are numbered for sort order: `0_low_blowup`, `1_medium_blowup`, `2_high_blowup`.

---

### Reproducibility

A single master seed drives all randomised generation and sampling, and is recorded in every instance `.json`. Rerunning the pipeline from that seed reproduces the candidate pool, the selected 60, and the `.dzn` files exactly. Once stage 4 begins, neither the candidate pool nor the selection may change — if a cell is under-populated during selection, expand parameter ranges and rerun stages 1–2 *before* any run of `run_experiments.py`.
