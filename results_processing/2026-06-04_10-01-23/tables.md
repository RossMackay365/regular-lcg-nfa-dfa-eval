### Geometric mean automaton construction time (ms) by blowup bin and pipeline step

| Bin    | Glushkov (ms) | Bisimulation (ms) | Subset Construction (ms) | Minimisation (ms) |
| ------ | ------------- | ----------------- | ------------------------ | ----------------- |
| Low    | 95.982        | 1733.493          | 80.417                   | 1650.458          |
| Medium | 3.963         | 9.360             | 3.614                    | 29.511            |
| High   | 4.454         | 12.559            | 119.124                  | 4019.061          |
| Total  | 11.921        | 58.846            | 32.593                   | 580.639           |

### Geometric mean solve time (s) by blowup bin and configuration (instances solved by every config)

| Bin    | Solved (n) | NFA (s) | DFA (s) | Decomp (s) |
| ------ | ---------- | ------- | ------- | ---------- |
| Low    | 35         | 2.991   | 2.734   | 3.629      |
| Medium | 44         | 0.485   | 1.686   | 2.918      |
| High   | 40         | 0.542   | 12.124  | 11.154     |
| Total  | 119        | 0.860   | 3.773   | 4.883      |

### Geometric mean solve time (s) by problem type and configuration (instances solved by every config)

| Problem Type | Solved (n) | NFA (s) | DFA (s) | Decomp (s) |
| ------------ | ---------- | ------- | ------- | ---------- |
| Nonogram     | 24         | 0.620   | 0.613   | 1.180      |
| Polyominoes  | 10         | 130.554 | 87.449  | 46.204     |
| Regex        | 85         | 0.522   | 4.353   | 5.597      |
| Total        | 119        | 0.860   | 3.773   | 4.883      |

### Geometric mean solve time excluding reconstruction cost (s) by blowup bin and configuration (instances solved by every config)

| Bin    | Solved (n) | NFA (s) | DFA (s) | Decomp (s) |
| ------ | ---------- | ------- | ------- | ---------- |
| Low    | 35         | 2.945   | 2.682   | 3.629      |
| Medium | 44         | 0.249   | 0.680   | 2.918      |
| High   | 40         | 0.281   | 4.486   | 11.154     |
| Total  | 119        | 0.513   | 1.903   | 4.883      |

### Geometric mean solve time excluding reconstruction cost (s) by problem type and configuration (instances solved by every config)

| Problem Type | Solved (n) | NFA (s) | DFA (s) | Decomp (s) |
| ------------ | ---------- | ------- | ------- | ---------- |
| Nonogram     | 24         | 0.816   | 0.811   | 1.180      |
| Polyominoes  | 10         | 46.106  | 31.807  | 46.204     |
| Regex        | 85         | 0.270   | 1.687   | 5.597      |
| Total        | 119        | 0.513   | 1.903   | 4.883      |

### Geometric mean nogood statistics by blowup bin (NFA vs DFA propagator; instances where neither NFA nor DFA timed out)

| Blowup Bin     | Valid Problems | NFA Nogoods | NFA Avg Nogood Length | NFA Avg LBD | DFA Nogoods | DFA Avg Nogood Length | DFA Avg LBD |
| -------------- | -------------- | ----------- | --------------------- | ----------- | ----------- | --------------------- | ----------- |
| Low (<2×)      | 42             | 101.23      | 10.77                 | 5.506       | 101.20      | 10.77                 | 5.505       |
| Medium (2–10×) | 46             | 1052.56     | 5.44                  | 5.442       | 1052.56     | 5.44                  | 5.442       |
| High (>10×)    | 40             | 928.27      | 5.63                  | 5.628       | 928.27      | 5.63                  | 5.628       |
| Total          | 128            | 480.93      | 6.83                  | 5.521       | 480.88      | 6.83                  | 5.521       |

### Geometric mean nogood statistics by problem type (NFA vs DFA propagator; instances where neither NFA nor DFA timed out)

| Problem Type | Valid Problems | NFA Nogoods | NFA Avg Nogood Length | NFA Avg LBD | DFA Nogoods | DFA Avg Nogood Length | DFA Avg LBD |
| ------------ | -------------- | ----------- | --------------------- | ----------- | ----------- | --------------------- | ----------- |
| Nonogram     | 24             | 78.21       | 14.21                 | 4.800       | 78.16       | 14.21                 | 4.798       |
| Polyominoes  | 17             | 111.24      | 7.60                  | 6.382       | 111.24      | 7.60                  | 6.382       |
| Regex        | 87             | 1013.45     | 5.56                  | 5.560       | 1013.45     | 5.56                  | 5.560       |
| Total        | 128            | 480.93      | 6.83                  | 5.521       | 480.88      | 6.83                  | 5.521       |
