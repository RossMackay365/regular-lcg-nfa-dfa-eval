# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

def _make_serialisable(obj):
    # Recursively Convert Sets, Tuples, Keys into JSON-Serialisable Form
    if isinstance(obj, (set, frozenset)):
        return sorted(_make_serialisable(x) for x in obj)
    if isinstance(obj, (tuple, list)):
        return [_make_serialisable(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _make_serialisable(v) for k, v in obj.items()}
    return obj


def serialize_automaton(automaton_tuple):
    Q, S_size, d, q0, F = automaton_tuple
    return {
        "Q":  int(Q),
        "S":  int(S_size),
        "d":  _make_serialisable(d),
        "q0": int(q0),
        "F":  sorted(int(s) for s in F),
    }


# ---------------------------------------------------------------------------
# Feasibility
# ---------------------------------------------------------------------------

# Takes Transition Step in DFA if Possible
def _dfa_step(d, state, symbol):
    inner = d.get(state) if isinstance(d, dict) else None
    if inner is None:
        return None
    dst = inner.get(symbol) if isinstance(inner, dict) else None
    if dst in (None, 0):
        return None
    return dst

# BFS over DFA - Checks for Reachable Accepting State (and thus feasible solution)
def is_feasible(dfa_tuple, var_count):
    Q, S_size, d, q0, F = dfa_tuple
    accepting = set(F)
    frontier = {q0}
    for _ in range(var_count):
        next_frontier = set()
        for state in frontier:
            for sym in range(1, S_size + 1):
                dst = _dfa_step(d, state, sym)
                if dst is not None:
                    next_frontier.add(dst)
        frontier = next_frontier
        if not frontier:
            return False
    return bool(frontier & accepting)


# ---------------------------------------------------------------------------
# Cyclic Check
# ---------------------------------------------------------------------------

# Build Adjacency List from Transition Function
def build_adj(Q, d):
    adj = {q: set() for q in Q}

    for q in Q:
        if q in d:
            for _, nxt in d[q].items():
                
                if nxt != q:
                    adj[q].add(nxt)

    return adj

# DFS to Detect Cycles in DFA
def dfs(node, adj, color):
    # color: 0 = unvisited, 1 = visiting, 2 = visited
    color[node] = 1

    for nei in adj[node]:
        if color[nei] == 1:
            # Cycle Detected
            return True 
        if color[nei] == 0:
            if dfs(nei, adj, color):
                return True

    color[node] = 2
    return False

# Check for Loops in DFA (Self-Loops Excluded)
def is_cyclic(dfa_tuple):
    Q, _, d, q0, _ = dfa_tuple

    adj = build_adj(Q, d)
    color = {q: 0 for q in Q}

    return dfs(q0, adj, color)