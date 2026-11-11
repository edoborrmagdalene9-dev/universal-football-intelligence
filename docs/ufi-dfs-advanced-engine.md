# UFI DFS Advanced Engine — Additive Extension

This extension is intentionally isolated under `dfs_optimizer/src/`. It does not replace the existing UFI match research, player intelligence, scoreline model, slip auditing, optimizer, or any other feature. All new paths are additive.

## New components

- `correlation.py`: construct covariance matrices from explicit standard deviations and pairwise correlations; validate symmetry/positive-semidefiniteness; compute lineup variance.
- `simulation.py`: reproducible 10,000+ draw joint Monte Carlo engine, per-player percentiles, and lineup ceiling quantiles.
- `game_state.py`: score-state transition distribution primitive, role/score-conditioned expected-minute adjustment, and explicit minute-distribution sampler.
- `ownership.py`: smoothed historical pick-share baseline, leverage index, and an exploratory ownership-adjusted value score.
- `scoring.py`: map low-level event rates or realized event counts to a configurable platform scoring matrix.
- `tests/test_advanced_dfs.py`: checks basic invariants and reproducibility.

## Current limitations — do not treat scaffolding as fitted intelligence

1. Covariance values must be estimated from historical player outcomes or supplied as clearly labelled assumptions. Pairwise intuition alone is not calibrated correlation.
2. The Monte Carlo engine currently uses a multivariate-normal approximation for fantasy points. It is a research baseline, not an event-level match simulator; it can create unrealistic tails and optional zero-clipping changes its moments.
3. The score-state module requires transition tables supplied by the caller. It does not estimate goal hazards, home/away scoring rates, or manager substitution tendencies from data yet. The minute sampler supports an explicit empirical distribution but does not fit one.
4. The Dirichlet ownership helper smooths observed pick counts. It is not LightGBM/XGBoost or a learned feature model. A trained ownership model needs historical contest pick rates, salary, form, fixture difficulty, contest context, and leakage-safe validation.
5. The event scoring mapper is only as accurate as the event-rate inputs and the platform's exact scoring rules. Confirm treatment of assists, clean sheets, cards, saves, tackles, interceptions, fouls drawn, penalties, and minutes bonuses.
6. The existing lineup solver is linear. A true MIQP optimizer that optimizes correlated variance/ceiling and contest payout is not claimed implemented here. Until a solver and objective are validated, use joint simulation to compare candidate lineups and portfolios rather than treating a weighted heuristic as optimal.
7. None of these modules guarantees positive returns. Evaluate with chronological out-of-sample backtests, calibration, baselines, bankroll constraints, and contest-specific payout structures.

## Suggested next stages

1. Gather licensed historical player-event, minutes/substitution, fantasy scoring, salary, and contest ownership data with source timestamps.
2. Build event-level rate models and a conditional minute distribution by role, manager, and score state.
3. Estimate/shrink covariance by event, team, role, and match context; inspect positive-semidefiniteness and stability.
4. Validate simulation distributions against held-out matches before increasing run counts.
5. Train ownership predictions only when historical contest-entry labels are available.
6. Add contest payout/rank simulation and a tested quadratic or simulation-based portfolio objective behind a separate interface.
7. Keep all changes additive; never remove or silently change existing UFI features.
