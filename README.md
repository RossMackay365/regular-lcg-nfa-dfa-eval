## NFA vs DFA Representations for the Regular Constraint in Lazy Clause Generation: A Comparative Evaluation

This repository is the reproducibility package for Ross Mackay's thesis
"NFA vs DFA Representations for the Regular Constraint in Lazy Clause
Generation: A Comparative Evaluation".

---

### Experimental Structure

The experiment compares four approaches to enforcing the regular constraint
across 60 problem instances, varying blowup ratio, difficulty, and automaton
structure (cyclic vs acyclic). Each instance is run four times: with the NFA
propagator on NFA data, with the DFA propagator on DFA data, and with solver
decomposition on each of those two data formats. This design allows the effect
of the propagator and the effect of the automaton representation to be assessed
independently.

The instances come from three problem types: car sequencing, rostering, and
synthetic high-blowup constructions. These are modelled differently in MiniZinc
but are all compared on the same axes. The problem type is not the unit of
comparison, the automaton structure is. Two instances from different problem
types can belong to the same experimental group if they share the same blowup
ratio, difficulty, and cyclic/acyclic classification.

---

### Instance Structure

Each instance consists of three files:

**automata/{blowup_level}/{instance_name}.json**
The source definition of the instance. Contains the NFA transition table,
accepting states, start state, and metadata. The blowup ratio and DFA state
count are computed during instance generation by running subset construction
followed by minimization on the NFA using dk.brics.automaton. The blowup ratio
is therefore the ratio of minimal DFA states to NFA states. This file is the
source of truth. The corresponding .dzn files are generated from it and can be
regenerated at any time by running scripts/generate_dzn.py.

**instances/nfa/{blowup_level}/{instance_name}.dzn**
The MiniZinc data file for NFA-format runs, generated from the corresponding
.json file. Contains the NFA transition table formatted for MiniZinc, along
with sequence length and domain size. Used for both the NFA propagator run and
the NFA decomposition run.

**instances/dfa/{blowup_level}/{instance_name}.dzn**
The MiniZinc data file for DFA-format runs, generated from the corresponding
.json file by running subset construction followed by minimization on the NFA
transition table. Contains the minimal DFA transition table formatted for
MiniZinc, along with sequence length and domain size. The expected DFA state
count recorded in the .json file can be used to verify that this derivation
produced the correct result. Used for both the DFA propagator run and the DFA
decomposition run.

**model/{problem_type}.mzn**
The MiniZinc model for the problem type. One model file covers all instances
of that problem type regardless of blowup ratio, difficulty, or automaton
structure. The model does not change between runs; the choice of propagator
versus decomposition is determined by the solver configuration at run time.

---

### Instance Naming Convention

Instances follow the pattern:

    {blowup}_{structure}_{difficulty}_{index}

For example: medium_cyclic_hard_03 is the third hard instance with a
medium blowup cyclic automaton.

- Blowup: low (< 2x), medium (2-10x), high (> 10x)
- Structure: cyclic or acyclic
- Difficulty: easy or hard (based on node count)
- Index: distinguishes instances within the same experimental group