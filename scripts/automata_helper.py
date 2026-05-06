from collections import deque
from automata.fa.dfa import DFA
from automata.fa.nfa import NFA

## Regex to NFA Builder for Pentominoes Generation Pipeline (Lagerkvist's Generation Produces Regex -> NFA Required for Model)
def regex_to_nfa_struct(regex_str, S):
    alphabet = {str(i) for i in range(1, S + 1)}
    nfa_obj = NFA.from_regex(regex_str, input_symbols=alphabet).eliminate_lambda()
    
    state_list = sorted(list(nfa_obj.states))
    remap = {state: i + 1 for i, state in enumerate(state_list)}
    
    Q_val = len(state_list)
    q0_val = remap[nfa_obj.initial_state]
    F_val = {remap[s] for s in nfa_obj.final_states}
    
    d_val = {}
    for state_from, transitions in nfa_obj.transitions.items():
        u = remap[state_from]
        for char, states_to in transitions.items():
            a = int(char)
            d_val[(u, a)] = {remap[v] for v in states_to}
            
    return Q_val, S, d_val, q0_val, F_val


## Converter from NFA to Minimal DFA (Subset Construction + Minimisation)
def nfa_to_min_dfa(Q, S, d, q0, F):
    """
    Convert NFA to minimal DFA using subset construction and DFA minification.
    """
    # 1. Subset Construction
    start = frozenset([q0])
    queue = deque([start])

    state_map = {start: 1}
    dfa_trans = {}
    dfa_accept = set()
    next_id = 2

    while queue:
        current = queue.popleft()
        current_id = state_map[current]

        if any(s in F for s in current):
            dfa_accept.add(current_id)

        for a in range(1, S + 1):
            next_subset = set()
            for q in current:
                next_subset.update(d[q][a])

            next_subset = frozenset(next_subset)
            if next_subset not in state_map:
                state_map[next_subset] = next_id
                queue.append(next_subset)
                next_id += 1

            dfa_trans[(current_id, a)] = state_map[next_subset]

    dfa_Q = len(state_map)
    dfa_q0 = state_map[start]

    # 2. Build DFA & Minimize
    transitions = {
        str(q): {
            str(a): str(dfa_trans[(q, a)])
            for a in range(1, S + 1)
        }
        for q in range(1, dfa_Q + 1)
    }

    dfa = DFA(
        states={str(i) for i in range(1, dfa_Q + 1)},
        input_symbols={str(i) for i in range(1, S + 1)},
        transitions=transitions,
        initial_state=str(dfa_q0),
        final_states={str(i) for i in dfa_accept},
    )

    min_dfa = dfa.minify()

    # 3. Convert Back to MiniZinc Format
    state_list = sorted(min_dfa.states, key=int)
    remap = {s: i + 1 for i, s in enumerate(state_list)}

    min_Q = len(state_list)
    min_q0 = remap[min_dfa.initial_state]
    min_F = {remap[s] for s in min_dfa.final_states}

    min_d = {}
    for s in state_list:
        for a in range(1, S + 1):
            min_d[(remap[s], a)] = remap[min_dfa.transitions[s][str(a)]]

    return min_Q, S, min_d, min_q0, min_F