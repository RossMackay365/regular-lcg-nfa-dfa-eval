### Geometric mean automaton construction time (ms) by blowup bin and pipeline step

| Bin    | Glushkov (ms) | Bisimulation (ms) | Subset Construction (ms) | Minimisation (ms) |
| ------ | ------------- | ----------------- | ------------------------ | ----------------- |
| Low    | 95.982        | 1733.493          | 80.417                   | 1650.458          |
| Medium | 3.963         | 9.360             | 3.614                    | 29.511            |
| High   | 4.454         | 12.559            | 119.124                  | 4019.061          |
| Total  | 11.921        | 58.846            | 32.593                   | 580.639           |

### Geometric mean automaton construction time (ms) by problem type and pipeline step

| Problem Type | Glushkov (ms) | Bisimulation (ms) | Subset Construction (ms) | Minimisation (ms) |
| ------------ | ------------- | ----------------- | ------------------------ | ----------------- |
| Nonogram     | 33.423        | 85.352            | 8.371                    | 107.611           |
| Polyominoes  | 349.868       | 55145.249         | 1121.804                 | 40072.966         |
| Regex        | 4.201         | 10.983            | 20.247                   | 333.415           |
| Total        | 11.921        | 58.846            | 32.593                   | 580.639           |

### Geometric mean solve time (s) by blowup bin and configuration (instances solved by every config)

| Bin    | Solved (n) | NFA (s) | DFA (s) |
| ------ | ---------- | ------- | ------- |
| Low    | 24         | 12.641  | 11.443  |
| Medium | 22         | 35.473  | 29.808  |
| High   | 43         | 1.312   | 11.856  |
| Total  | 89         | 5.461   | 14.749  |

### Geometric mean solve time (s) by problem type and configuration (instances solved by every config)

| Problem Type | Solved (n) | NFA (s) | DFA (s) |
| ------------ | ---------- | ------- | ------- |
| Nonogram     | 22         | 8.791   | 8.254   |
| Polyominoes  | 2          | 686.951 | 416.097 |
| Regex        | 65         | 4.006   | 16.198  |
| Total        | 89         | 5.461   | 14.749  |

### Geometric mean solve time excluding reconstruction cost (s) by blowup bin and configuration (instances solved by every config)

| Bin    | Solved (n) | NFA (s) | DFA (s) |
| ------ | ---------- | ------- | ------- |
| Low    | 24         | 22.494  | 20.614  |
| Medium | 22         | 35.354  | 29.355  |
| High   | 43         | 1.004   | 5.027   |
| Total  | 89         | 5.513   | 11.300  |

### Geometric mean solve time excluding reconstruction cost (s) by problem type and configuration (instances solved by every config)

| Problem Type | Solved (n) | NFA (s) | DFA (s) |
| ------------ | ---------- | ------- | ------- |
| Nonogram     | 22         | 16.295  | 15.547  |
| Polyominoes  | 2          | 663.877 | 398.566 |
| Regex        | 65         | 3.352   | 9.134   |
| Total        | 89         | 5.513   | 11.300  |

### Geometric mean nogood statistics by blowup bin (NFA vs DFA propagator; instances where neither NFA nor DFA timed out)

| Blowup Bin     | Valid Problems | NFA Nogoods | NFA Avg Nogood Length | NFA Avg LBD | DFA Nogoods | DFA Avg Nogood Length | DFA Avg LBD |
| -------------- | -------------- | ----------- | --------------------- | ----------- | ----------- | --------------------- | ----------- |
| Low (<2×)      | 24             | 45.08       | 11.56                 | 4.551       | 45.16       | 11.60                 | 4.556       |
| Medium (2–10×) | 22             | 260.41      | 4.80                  | 4.800       | 260.41      | 4.80                  | 4.800       |
| High (>10×)    | 43             | 1149.66     | 5.79                  | 5.788       | 1149.66     | 5.79                  | 5.788       |
| Total          | 89             | 348.17      | 6.58                  | 5.195       | 348.34      | 6.58                  | 5.196       |

### Geometric mean nogood statistics by problem type (NFA vs DFA propagator; instances where neither NFA nor DFA timed out)

| Problem Type | Valid Problems | NFA Nogoods | NFA Avg Nogood Length | NFA Avg LBD | DFA Nogoods | DFA Avg Nogood Length | DFA Avg LBD |
| ------------ | -------------- | ----------- | --------------------- | ----------- | ----------- | --------------------- | ----------- |
| Nonogram     | 22             | 47.26       | 12.56                 | 4.505       | 47.36       | 12.61                 | 4.510       |
| Polyominoes  | 2              | 28.11       | 5.04                  | 5.040       | 28.11       | 5.04                  | 5.040       |
| Regex        | 65             | 695.49      | 5.43                  | 5.432       | 695.49      | 5.43                  | 5.432       |
| Total        | 89             | 348.17      | 6.58                  | 5.195       | 348.34      | 6.58                  | 5.196       |
