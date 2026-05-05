from collections import deque
from automata.fa.dfa import DFA

def nfa_to_min_dfa(Q, S, d, q0, F):
    """
    Convert NFA to minimal DFA.
    """

    # -----------------------------
    # 1. Subset Constructionk
    # -----------------------------
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

    dfa_d = {
        (q, a): dfa_trans[(q, a)]
        for q in range(1, dfa_Q + 1)
        for a in range(1, S + 1)
    }

    # -----------------------------
    # 2. Build DFA & Minimize
    # -----------------------------
    transitions = {
        str(q): {
            str(a): str(dfa_d[(q, a)])
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

    # -----------------------------
    # 3. Convert Back to MiniZinc Format
    # -----------------------------
    state_list = sorted(min_dfa.states)
    remap = {s: i + 1 for i, s in enumerate(state_list)}

    min_Q = len(state_list)
    min_q0 = remap[min_dfa.initial_state]
    min_F = {remap[s] for s in min_dfa.final_states}

    min_d = {}

    for s in state_list:
        for a in range(1, S + 1):
            min_d[(remap[s], a)] = remap[min_dfa.transitions[s][str(a)]]

    return min_Q, S, min_d, min_q0, min_F