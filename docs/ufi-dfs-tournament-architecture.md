# UFI DFS Tournament Architecture — Additive Extension

All new code is added alongside existing UFI components. No previous modules or features are replaced or deleted.

## Added components

- `opponent_model.py`: empirical joint player-pick frequencies, Dirichlet-multinomial sampling across lineup archetypes, normalized roster overlap, and duplication summaries.
- `tactical.py`: explicit score-state and tactical-matchup multipliers for event-rate baselines.
- `miqp.py`: optional CVXPY adapter requiring a compatible installed mixed-integer non-convex quadratic solver. It raises an error if no compatible solver is available and never silently falls back to the existing linear solver.
- `test_opponent_tactical.py`: tests joint picks, overlap, and tactical-rate helpers.

## Limitations that matter

1. Individual ownership percentages do not identify joint lineup ownership. Learn joint pick rates from historical entries where permitted. Dirichlet-multinomial lineup archetypes do not automatically learn salary-driven player dependencies.
2. The overlap metric is intersection size divided by the geometric mean of roster sizes. It is normalized overlap, not strict Pearson correlation. Expected payout depends on the field, scores, payout table, ties, entry count and fees; low overlap alone does not guarantee a payout increase.
3. Tactical multipliers are supplied assumptions until estimated from event logs and tested out of sample.
4. The current game-state code uses discrete checkpoints, not a fitted continuous-time Markov chain. A CTMC requires estimated transition intensities and event timestamps.
5. The MIQP adapter is a research scaffold. Maximizing variance is not the same as maximizing the 99th percentile or tournament payout, and non-convex MIQP solver support varies. The existing MILP remains unchanged.
6. Multivariate-normal simulations can be inaccurate for discrete, bounded, zero-inflated fantasy events. Event-level or copula simulation remains future work.
7. No model guarantees profit. Use licensed data, contest-specific scoring/payouts, calibration, chronological holdout tests, uncertainty intervals, and bankroll limits.

## Next stages

1. Collect time-stamped historical event logs, substitutions, salaries, scoring rules, contest entries and payout tables.
2. Estimate state-conditioned minutes and event rates, plus tactical matchup effects.
3. Estimate and regularize the joint player covariance structure.
4. Validate 95th/99th percentile distributions on held-out fixtures.
5. Simulate opposing lineups, contest ranks, payout distributions and ties.
6. Compare existing ILP, simulation-based search, and compatible MIQP methods before choosing an objective.
7. Review every diff for deletions before merging any future change.
