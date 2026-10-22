# FantasyFi micro-behavioral engine (add-on)

This is additive to the existing UFI/FantasyFi pipeline. Existing scoring, player-data,
portfolio-simulation, optional MIQP, and Streamlit workspaces remain in place.

## New modules
- `dfs_optimizer/src/fantasyfi_monte_carlo.py`: vectorized Monte Carlo engine, default
  10,000 runs; returns mean, median, 5th, 95th and 99th percentiles, threshold rates,
  and the full simulation matrix. It uses existing scoring weights.
- `dfs_optimizer/src/microbehavioral_engine.py`: explicit registry for all 30 requested
  role, tactical matchup, event, environment, ownership, portfolio, late-swap and
  edge-decay inputs; adds transparent role tags, opt-in multipliers and pass-boundary
  diagnostics. It does not invent missing inputs or pretend coefficients are trained.
- `dfs_optimizer/src/fantasyfi_portfolio_optimizer.py`: multi-entry PuLP/CBC MILP
  optimizer using simulation means, 95th-percentile upside, ownership, roster rules,
  salary limits, aggregate exposure and pairwise overlap controls.
- `dfs_optimizer/tests/test_fantasyfi_microbehavioral_engine.py`: validation tests.

## Monte Carlo input
Required CSV columns: player_name, position, start_probability, mean_passes,
mean_interceptions, mean_shots_on_target, mean_goals, mean_assists, clean_sheet_prob,
mean_yellow_cards, mean_red_cards. Optional means include chances created, goalkeeper
saves, penalties saved/missed, own goals and goals conceded; optional minutes and team
columns allow additional scenario controls. Python API returns (summary, score_matrix).

## Run
From the repository root:
```bash
python -m pytest dfs_optimizer/tests -q
python -m compileall -q dfs_optimizer
```

## Mathematical/data limitations
1. Expected passes cannot be scored exactly as floor(E[passes]/5). Correct expected
   step points are E[floor(P/5)], requiring a calibrated pass-count distribution.
2. Monte Carlo count events are sampled from supplied marginal rates. Optional team
   shocks are not full match correlation. Unrelated goal, assist, shot, clean-sheet and
   concession projections may be mutually inconsistent.
3. Clean-sheet probability is supplied and gated by simulated minutes >=55. A mature
   implementation should jointly model minute-level substitutions and team score state.
4. The 30 feature slots cover all requested concepts. Referee effects, fatigue,
   travel, weather, marking, ownership recency, late swap and market edge decay require
   licensed observations and backtested coefficients; no synthetic data is presented as
   fact.
5. PuLP/CBC is MILP, not MIQP. A true covariance quadratic objective requires the
   existing optional CVXPY adapter and a compatible solver. Ownership and leaving salary
   unused do not guarantee uniqueness, rank or profit.
6. No live lineup, salary, ownership, referee, weather, fatigue or market provider is
   configured. Use permitted sources and preserve provenance. Research estimates only.
