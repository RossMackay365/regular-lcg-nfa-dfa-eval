%
% Regex Model
%
% A synthetic problem where a sequence of variables over a fixed alphabet
% must spell a string accepted by a given regular expression.
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

int: n_constraints;
int: Q;
int: S;

array[1..n_constraints] of int: q0;
array[1..n_constraints] of set of int: F;

array[1..n_constraints, 1..Q, 1..S] of int: d_dfa;
array[1..n_constraints, 1..Q, 1..S] of set of int: d_nfa;

array[1..var_count] of int: weights;

array[1..var_count] of var 1..S: variables;

var int: objective = sum(i in 1..var_count)(weights[i] * variables[i]);

constraint forall (e in 1..n_constraints) (
    if mode = 0 then
        regular(variables, Q, S, d_dfa[e, 1..Q, 1..S], q0[e], F[e])
    else
        regular_nfa(variables, Q, S, d_nfa[e, 1..Q, 1..S], q0[e], F[e])
    endif
);

solve :: int_search(variables, input_order, indomain_min) maximize objective;
