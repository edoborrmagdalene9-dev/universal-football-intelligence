# Functional workarounds: DFS simulation and contest evaluation

These modules are **additive** and do not replace the existing optimizer, score grid,
correlation helpers, or earlier research modules.

## 1. Joint opponent ownership

`ownership_workarounds.py` uses historical contest entries as whole-lineup bootstrap
samples, preserving combinations actually observed. It also reports marginal and pair
ownership. If entries are unavailable, weighted sampling from marginal ownership is
available but explicitly labeled a baseline; it does not learn correlations or salary
dependencies. Do not describe the fallback as learned joint ownership. Use only data
you are licensed to access, and retain contest/date/platform metadata to prevent leakage.

## 2. Upper-tail player simulation

`event_simulator.py` simulates individual event counts (Poisson) and maps events to
platform points. A shared lognormal match factor induces basic same-match dependence.
This is a functional, inspectable starting point for P50/P95/P99—not a calibrated
copula or an event-tracking reconstruction. Calibrate event rates and dispersion using
time-ordered historical data, include player minutes and team/score state, then evaluate
quantile coverage out of sample. A P99 from a small sample is noisy; increase simulations
only after the event distributions are credible.

## 3. Continuous-time score states

`continuous_time_states.py` uses competing exponential goal hazards and updates rates
after each goal. The state is the current lead/draw/trail status, so state transitions
happen at event times rather than fixed checkpoints. The included rate estimator is only
a smoothed league baseline; fit team/opponent/venue/time and score-state-specific
hazards from timestamped match data before using forecasts.

## 4. MIQP without a compatible solver

`optimizer_fallback.py` exactly enumerates feasible lineups for small candidate pools,
using the same explicit mean + quadratic covariance − ownership-penalty objective.
It is exponential and intentionally refuses large pools instead of pretending to solve
them. For larger pools, install and validate a compatible MIQP solver or use the existing
MILP optimizer as a clearly labeled mean-only fallback. Variance is not equivalent to
winning probability.

## 5. Contest winnings and ties

`contest_simulator.py` computes ranks, tie-split prizes, payout, top-1 rate, and net
results from simulated player scores and opposing lineups. Its simple payout mapping
must be populated with the exact contest's payout table and entry fee. To make the
comparison meaningful, simulate candidate and opponent lineups against the same player
outcome realization, include field size and duplicate lineups, and report expected
payout, ROI, top-1/top-X rates, and uncertainty intervals. The current module is a
transparent first implementation, not a validated end-to-end profitability engine.

## Validation checklist

1. Add tests for platform scoring rules, late substitutions, missing data, and ties.
2. Run `python -m unittest discover -s dfs_optimizer/tests -v` from repository root.
3. Use chronological train/validation/test splits; never random-split future match rows
   into training data.
4. Compare against simple baselines and check calibration of means and upper quantiles.
5. Run sensitivity analyses for contest size, payout structure, ownership uncertainty,
   entry fee, and model error.
6. No forecast or optimizer can guarantee profit; account for fees, variance, and risk.
