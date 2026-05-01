## NFA vs DFA Representations for the Regular Constraint in Lazy Clause Generation: A Comparative Evaluation

This repository is the reproducibility package for Ross Mackay's thesis
"NFA vs DFA Representations for the Regular Constraint in Lazy Clause
Generation: A Comparative Evaluation".

---

### Experimental Structure

The experiment compares NFA and DFA propagators for the regular constraint
across 60 problem instances, varying blowup ratio, difficulty, and automaton
structure (cyclic vs acyclic). Each instance is solved once with each
propagator.

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
on the NFA using dk.brics.automaton. This file is the source of truth. The
corresponding .dzn file is generated from it and can be regenerated at any
time by running scripts/generate_dzn.py.

**instances/{blowup_level}/{instance_name}.dzn**
The MiniZinc data file, generated from the corresponding .json file. Contains
the NFA transition table formatted for MiniZinc, along with sequence length
and domain size. Both propagator runs use this same file. The DFA propagator
derives the DFA internally at initialisation by running subset construction on
the NFA transition table, using the same procedure as during instance
generation. The expected DFA state count recorded in the .json file can be
used to verify this derivation is correct.

**model/{problem_type}.mzn**
The MiniZinc model for the problem type. One model file covers all instances
of that problem type regardless of blowup ratio, difficulty, or automaton
structure. The model does not change between propagator runs.

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