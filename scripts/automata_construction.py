from FAdo.reex import str2regexp
import os
import time

## Print Automaton Structure
def print_automaton(name, automaton):
    Q, S, d, q0, F = automaton

    print(f"\n=== {name} ===")

    # Q (States)
    print("States (Q):", list(range(1, Q + 1)))

    # Σ (Alphabet)
    print("Alphabet (Σ):", list(range(1, S + 1)))

    # q0
    print("\nInitial state (q0):")
    print(" ", q0)

    # F
    print("\nFinal states (F):")
    print(" ", sorted(F))

    # δ (Transition Function)
    print("\nTransitions (δ):")

    for state in sorted(d.keys()):
        for symbol in sorted(d[state].keys()):
            target = d[state][symbol]
            print(f"  δ({state}, {symbol}) -> {target}")

## Generate Automata Diagram
def save_diagram(automaton, filepath, is_dfa: bool):
    # Create Output Directory If Needed
    name = "dfa" if is_dfa else "nfa"
    out_dir = os.path.join(filepath, "diagram")
    os.makedirs(out_dir, exist_ok=True)

    # Create Output Path
    full_path = os.path.join(out_dir, name)

    # Generate Diagram
    automaton.display(filename=full_path)

## Helper Function to Unwrap Singleton Initial State
def unwrap_singleton(s):
    if isinstance(s, set) and len(s) == 1:
        return next(iter(s))
    return s

## Map Library NFA Structure to MiniZinc Format
def encode_nfa(nfa):
    ## State Length & Alphabet Length
    Q = len(nfa.States)
    alphabet = sorted(nfa.Sigma)
    symbol_to_int = {a: i + 1 for i, a in enumerate(alphabet)}
    S = len(alphabet)

    ## Start and Final States
    assert len(nfa.Initial) == 1, f"Expected exactly one initial state, got {len(nfa.Initial)}"
    q0 = next(iter(nfa.Initial)) + 1
    F = {idx + 1 for idx in nfa.Final}

    ## Transition Function
    d = {si: {ai: set() for ai in range(1, S + 1)} for si in range(1, Q + 1)}
    for src_idx, transitions in nfa.delta.items():
        for symbol, targets in transitions.items():
            if symbol not in symbol_to_int:
                continue
            d[src_idx + 1][symbol_to_int[symbol]] = {t + 1 for t in targets}

    return Q, S, d, q0, F

## Map Library DFA Structure to MiniZinc Format
def encode_dfa(dfa):
    ## State Length & Alphabet Length
    Q = len(dfa.States)
    alphabet = sorted(dfa.Sigma)
    symbol_to_int = {a: i + 1 for i, a in enumerate(alphabet)}
    S = len(alphabet)

    ## Start and Final States
    q0 = dfa.Initial + 1
    F = {idx + 1 for idx in dfa.Final}

    ## Transition Function
    d = {si: {ai: 0 for ai in range(1, S + 1)} for si in range(1, Q + 1)}
    for src_idx, transitions in dfa.delta.items():
        for symbol, target in transitions.items():
            d[src_idx + 1][symbol_to_int[symbol]] = target + 1

    return Q, S, d, q0, F


## Feasibility Check - BFS over NFA for var_count steps
def is_feasible(nfa_tuple, var_count):
    _, S_size, d, q0, F = nfa_tuple
    accepting = set(F)
    frontier  = {q0}
    for _ in range(var_count):
        next_frontier = set()
        for state in frontier:
            inner = d.get(state, {}) if isinstance(d, dict) else {}
            for sym in range(1, S_size + 1):
                dst = inner.get(sym, set()) if isinstance(inner, dict) else set()
                next_frontier |= dst
        frontier = next_frontier
        if not frontier:
            return False
    return bool(frontier & accepting)


## Timed Automata Build (Single Regex)
#
# Performs Four Time-Measured Steps:
#   1. Glushkov NFA construction (regex string -> NFA)
#   2. Right-bisim NFA reduction (Glushkov NFA -> reduced NFA, stored)
#   3. Subset construction         (Glushkov NFA -> un-minimised DFA)
#   4. DFA minimisation            (un-min DFA  -> minimal DFA, stored)
#
# Subset construction runs on the raw Glushkov NFA, not the reduced one, 
# so the NFA-side and DFA-side reduction strategies are cleanly separated
# in the measurements.

def build_automata_pair(regex_str, sigma_extra=None):
    # Step 1: Glushkov NFA
    t0 = time.perf_counter()
    regex = str2regexp(regex_str)
    nfa_g = regex.nfaGlushkov()
    nfa_glushkov_ms = (time.perf_counter() - t0) * 1000.0

    # Augment Alphabet If Needed (Ensures NFA's Share Alphabet for Nonograms/Pentominoes)
    if sigma_extra:
        for sym in sigma_extra:
            nfa_g.Sigma.add(sym)

    nfa_glushkov_states = len(nfa_g.States)

    # Step 2: Right-Bisimulation NFA Reduction (stored NFA)
    t0 = time.perf_counter()
    nfa_r = nfa_g.rEquivNFA()
    nfa_rbisim_ms = (time.perf_counter() - t0) * 1000.0
    # Preserve augmented alphabet on the reduced NFA.
    if sigma_extra:
        for sym in sigma_extra:
            nfa_r.Sigma.add(sym)
    nfa_rbisim_states = len(nfa_r.States)

    # Step 3: Subset Construction (unminimised DFA)
    t0 = time.perf_counter()
    dfa_u = nfa_g.toDFA()
    dfa_subset_ms = (time.perf_counter() - t0) * 1000.0
    dfa_subset_states = len(dfa_u.States)

    # Step 4: DFA Minimisation (stored DFA)
    t0 = time.perf_counter()
    dfa_m = dfa_u.minimal()
    dfa_min_ms = (time.perf_counter() - t0) * 1000.0
    dfa_min_states = len(dfa_m.States)

    metrics = {
        "nfa_glushkov_ms":     nfa_glushkov_ms,
        "nfa_glushkov_states": nfa_glushkov_states,
        "nfa_rbisim_ms":       nfa_rbisim_ms,
        "nfa_rbisim_states":   nfa_rbisim_states,
        "dfa_subset_ms":       dfa_subset_ms,
        "dfa_subset_states":   dfa_subset_states,
        "dfa_min_ms":          dfa_min_ms,
        "dfa_min_states":      dfa_min_states,
    }

    return encode_nfa(nfa_r), encode_dfa(dfa_m), metrics


## Automata Construction Pipeline
def construct_automata(regex_list, sigma_extra=None, feasibility_var_counts=None):
    builds = [build_automata_pair(r, sigma_extra=sigma_extra) for r in regex_list]
    nfa_tuples = [b[0] for b in builds]
    dfa_tuples = [b[1] for b in builds]
    metrics    = [b[2] for b in builds]

    if feasibility_var_counts is not None:
        for nfa_t, vc in zip(nfa_tuples, feasibility_var_counts):
            if not is_feasible(nfa_t, vc):
                return None

    return nfa_tuples, dfa_tuples, metrics
