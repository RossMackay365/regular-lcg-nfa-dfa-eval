%
% Car Sequencing Model
%
% A production-line ordering problem where cars carrying various options
% must be sequenced so that, for each option, at most m of any b consecutive
% cars install that option.
%
% Written by Ross Mackay, with reference to:
%   https://github.com/MiniZinc/minizinc-benchmarks/blob/master/cars/cars.mzn
%
% Part of: Ross Mackay, BSc thesis,
%   "NFA vs DFA Representations for the Regular Constraint in Lazy Clause
%   Generation: A Comparative Evaluation" (2026).
%

include "globals.mzn";

int: n_cars;
int: n_options;

set of int: steps = 1..n_cars;
set of int: options = 1..n_options;

int: mode; % 0 = DFA, 1 = NFA

int: Q;
int: S;

array[options] of int: q0;
array[options] of set of int: F;
array[options, 1..Q, 1..S] of int: d_dfa;
array[options, 1..Q, 1..S] of set of int: d_nfa;

array[steps, options] of var 1..S: use;

constraint forall (p in options) (
    if mode = 0 then
        regular(
            [use[s, p] | s in steps],
            Q, S,
            array2d(1..Q, 1..S, [d_dfa[p, q, s] | q in 1..Q, s in 1..S]),
            q0[p],
            F[p]
        )
    else
        regular_nfa(
            [use[s, p] | s in steps],
            Q, S,
            array2d(1..Q, 1..S, [d_nfa[p, q, s] | q in 1..Q, s in 1..S]),
            q0[p],
            F[p]
        )
    endif
);

solve satisfy;

output [
  "Car sequencing result:\n",
  "Rows = cars, Columns = options\n\n"
] 
++
[
  "Car " ++ show(s) ++ ": " ++
  concat([ show(use[s,p]) ++ if p < n_options then " " else "" endif
         | p in options ]) ++ "\n"
  | s in steps
];