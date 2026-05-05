%
% Pentominoes Model
%
% A grid-tiling puzzle where the board must be filled with pentomino pieces
% (each covering exactly five cells in one of 12 distinct shapes).
%
% Written by Ross Mackay, with reference to a model by Mikael Zayenz Lagerkvist (2020):
%   https://github.com/zayenz/minizinc-pentominoes-generator/blob/main/model/pentominoes.mzn
%
% Part of: Ross Mackay, BSc thesis,
%   "NFA vs DFA Representations for the Regular Constraint in Lazy Clause
%   Generation: A Comparative Evaluation" (2026).
%

include "globals.mzn";

int: size;
int: tiles;

int: mode; % 0 = DFA, 1 = NFA

int: n_expressions;
int: Q;
int: S;

array[1..n_expressions] of int: q0;
array[1..n_expressions] of set of int: F;
array[1..n_expressions, 1..Q, 1..S] of int: d_dfa;
array[1..n_expressions, 1..Q, 1..S] of set of int: d_nfa;

int: marker = tiles+1;
set of int: Tiles = 1..tiles;
set of int: TilesAndMarker = Tiles union {marker};

array[1..size, 1..size] of var Tiles: board;
array[int] of var TilesAndMarker: board_and_markers = [
  if column <= size then board[row, column] else marker endif
  | row in 1..size, column in 1..size+1
];

constraint forall (e in 1..n_expressions) (
    if mode = 0 then
        regular(
            board_and_markers,
            Q, S,
            array2d(1..Q, 1..S, [d_dfa[e, q, s] | q in 1..Q, s in 1..S]),
            q0[e],
            F[e]
        )
    else
        regular_nfa(
            board_and_markers,
            Q, S,
            array2d(1..Q, 1..S, [d_nfa[e, q, s] | q in 1..Q, s in 1..S]),
            q0[e],
            F[e]
        )
    endif
);

solve :: int_search(board, input_order, indomain_min, complete) satisfy;

output [
   "board = \n", show2d(board), ";\n"
];