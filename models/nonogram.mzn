%
% Nonogram Model
%
% A grid-colouring puzzle where each row and column has a clue specifying
% the lengths of consecutive runs of filled cells, and the solver must
% find a colouring consistent with every clue.
%
% Written by Ross Mackay, with reference to a model by Julius Gvozdiovas (2025): 
%   https://github.com/JulGvoz/nfa-propagator-explanations/blob/227196987c770e9fe682fd581ceed04f93b80b64/experiments/problems/nonogram/nonogram.mzn
%
% Part of: Ross Mackay, BSc thesis,
%   "NFA vs DFA Representations for the Regular Constraint in Lazy Clause
%   Generation: A Comparative Evaluation" (2026).
%

include "globals.mzn";

int: width;
int: height;

int: mode; % 0 = DFA, 1 = NFA

int: Q;
int: S;

array[1..height] of int: row_q0;
array[1..height] of set of int: row_F;
array[1..height, 1..Q, 1..S] of int: row_d_dfa;
array[1..height, 1..Q, 1..S] of set of int: row_d_nfa;

array[1..width] of int: col_q0;
array[1..width] of set of int: col_F;
array[1..width, 1..Q, 1..S] of int: col_d_dfa;
array[1..width, 1..Q, 1..S] of set of int: col_d_nfa;

array[1..height, 1..width] of var 1..S: grid;

constraint forall (r in 1..height) (
    if mode = 0 then
        regular(
            [grid[r, c] | c in 1..width],
            Q, S,
            array2d(1..Q, 1..S, [row_d_dfa[r, q, s] | q in 1..Q, s in 1..S]),
            row_q0[r],
            row_F[r]
        )
    else
        regular_nfa(
            [grid[r, c] | c in 1..width],
            Q, S,
            array2d(1..Q, 1..S, [row_d_nfa[r, q, s] | q in 1..Q, s in 1..S]),
            row_q0[r],
            row_F[r]
        )
    endif
);

constraint forall (c in 1..width) (
    if mode = 0 then
        regular(
            [grid[r, c] | r in 1..height],
            Q, S,
            array2d(1..Q, 1..S, [col_d_dfa[c, q, s] | q in 1..Q, s in 1..S]),
            col_q0[c],
            col_F[c]
        )
    else
        regular_nfa(
            [grid[r, c] | r in 1..height],
            Q, S,
            array2d(1..Q, 1..S, [col_d_nfa[c, q, s] | q in 1..Q, s in 1..S]),
            col_q0[c],
            col_F[c]
        )
    endif
);

solve satisfy;

function string: cell(int: x) =
    if x == 2 then "#" else "." endif;

output [
  "Nonogram Solution:\n\n"
] ++
[
  concat([ cell(fix(grid[r,c])) | c in 1..width ]) ++ "\n"
  | r in 1..height
];