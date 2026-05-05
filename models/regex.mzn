%
% Regex Model
%
% A synthetic problem where a sequence of variables over a fixed alphabet
% must spell a string accepted by a given regular expression; included to
% populate experimental cells the four real-problem types do not reach.
%
% Written by Ross Mackay, with reference to a model by Julius Gvozdiovas (2025):
%   https://github.com/JulGvoz/nfa-propagator-explanations/blob/227196987c770e9fe682fd581ceed04f93b80b64/experiments/problems/regex/regex.mzn
%
% Part of: Ross Mackay, BSc thesis,
%   "NFA vs DFA Representations for the Regular Constraint in Lazy Clause
%   Generation: A Comparative Evaluation" (2026).
%

include "globals.mzn";

int: var_count;

int: mode; % 0 = DFA, 1 = NFA

int: Q;
int: S;
int: q0;
set of int: F;

array[1..Q, 1..S] of int: d_dfa;
array[1..Q, 1..S] of set of int: d_nfa;

array[1..var_count] of var 1..S: variables;

constraint
    if mode = 0 then
        regular(variables, Q, S, d_dfa, q0, F)
    else
        regular_nfa(variables, Q, S, d_nfa, q0, F)
    endif;

solve satisfy;
