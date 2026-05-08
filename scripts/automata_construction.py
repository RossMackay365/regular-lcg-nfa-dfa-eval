from FAdo.reex import str2regexp
import os

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

## Regex to NFA (Glushkov Construction)
def regex_to_nfa(regex_str):
    regex = str2regexp(regex_str)
    nfa = regex.nfaGlushkov()
    save_diagram(nfa, "output", is_dfa=False)
    return nfa

## NFA to Minimal DFA
def nfa_to_min_dfa(nfa):
    dfa = nfa.toDFA()
    min_dfa = dfa.minimal()
    save_diagram(min_dfa, "output", is_dfa=True)
    return min_dfa

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


## Automata Construction Pipeline
def construct_automata(regex_str):
    nfa = regex_to_nfa(regex_str)

    dfa = nfa_to_min_dfa(nfa)

    nfa_enc = encode_nfa(nfa)
    dfa_enc = encode_dfa(dfa)

    return nfa_enc, dfa_enc