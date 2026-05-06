%
% Shift Scheduling Model
%
% A workforce-scheduling problem where a sequence of daily shifts is assigned
% to a single worker, subject to regular-expressible rules over consecutive
% shifts (e.g. mandatory rest after a streak of night shifts).
%
% Written by Ross Mackay, with reference to a model used in the 2022 MiniZinc Challenge:
%   https://github.com/MiniZinc/mzn-challenge/blob/develop/2022/rotating-workforce-scheduling/rotating-workforce-scheduling.mzn
%
% Part of: Ross Mackay, BSc thesis,
%   "NFA vs DFA Representations for the Regular Constraint in Lazy Clause
%   Generation: A Comparative Evaluation" (2026).
%

include "globals.mzn";

int: sequence_length;
set of int: Positions = 1..sequence_length;

int: mode; % 0 = DFA, 1 = NFA

int: Q;
int: S;
int: q0;
set of int: F;

array[1..Q, 1..S] of int: d_dfa;
array[1..Q, 1..S] of set of int: d_nfa;

array[Positions] of var 1..S: schedule;

constraint
    if mode = 0 then
        regular(schedule, Q, S, d_dfa, q0, F)
    else
        regular_nfa(schedule, Q, S, d_nfa, q0, F)
    endif;

solve :: int_search(schedule, input_order, indomain_min) satisfy;

output [
  if i mod 7 = 1 then
    "\nWeek " ++ show((i - 1) div 7 + 1) ++ "\n"
  else
    ""
  endif
  ++ "  Day " ++ show(((i - 1) mod 7) + 1)
  ++ ": Shift " ++ show(schedule[i]) ++ "\n"
| i in Positions
];