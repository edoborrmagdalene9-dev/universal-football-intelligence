# FantasyFi Quantitative DFS Engine (additive module)

This branch adds a FantasyFi-specific research layer alongside the existing UFI
match modelling, dashboard, backtesting, simulation, and DFS code. It does not
replace existing modules.

## Implemented in this branch

- `dfs_optimizer/src/scoring_engine.py`: explicit FantasyFi rulebook; tackles score zero and are ignored; completed-pass actual scoring is `floor(passes/5)`; goals and shots-on-target are both scored when the shot-on-target count includes the goal; 55-minute defensive clean-sheet rule; cards, own goals, penalty misses, saves and penalty saves; expected points and penalty event EV.
- `dfs_optimizer/src/predictive_models/dixon_coles.py`: SciPy maximum-likelihood fit with exponential recency weights (`xi=0.0065)), low-score tau correction and normalized score grid. Clean-sheet probabilities and expected goals are derived from the grid.
- `dfs_optimizer/src/ownership_engine.py`: smoothed ownership, leverage index and contrarian constraints.
- `dfs_optimizer/src/optimizer/pulp_optimizer.py`: ILP single lineup and sequential portfolio with salary/position/team caps and minimum symmetric-difference diversification.
- `dfs_optimizer/src/automation/main.py`: offline CSV CLI that writes an entry CSV.
- `.github/workflows/pipeline.yml`: manual/scheduled workflow scaffold and tests. Scheduled runs are not a guarantee of 60-minute pre-lock timing: GitHub cron is UTC, can be delayed, and a real lineup provider/API plus platform-specific lock times must be configured.

## Important scoring mathematics

Actual pass points: `floor(completed_passes / 5)`. For expected passes without a count distribution, the xP helper uses the linear approximation `E[passes]/5`; supply a pass-count PMF to model the floor exactly.

Penalty attempt EV for a forward, when a scored penalty includes one shot-on-target event:
`EV = p*(40+6) + (1-p)*(-20) = 66p - 20`; break-even is `20/66 ≈ 30.3%`. At 70% conversion, EV is +26.2 points. This is the taker's event EV; the opposing goalkeeper's +50 penalty-save bonus is a separate player outcome, not a deduction from taker points.

A defender goal plus a shot on target gives +66 event points before appearance, passes, clean sheet or other events. This is a high-ceiling scenario, not a reliable expected outcome.

## Input and validation limits

The scoring engine expects canonical event/stat fields; provider-specific event feeds need an explicit mapping. The Dixon-Coles model needs dated match results and enough representative fixtures; it does not itself estimate player xG, player role, pressing, aerial target density, or confirmed starting XI. The ownership model needs historical contest entries or trustworthy projections; without those, leverage is a scenario rather than a learned fact. Set-piece/aerial and goalkeeper penalty-save features are not fabricated where data is absent.

The optimizer's captain multiplier is optional and only correct for a platform that actually has captain/MVP rules. Positional slot labels, salary caps, roster size, team caps, ownership cap and minimum leverage plays must match the active contest. Portfolio constraints can make later lineups infeasible; this is reported rather than silently weakening constraints. The current sequential portfolio implementation maximizes projected points while enforcing minimum roster Hamming distance; it is not a full implementation of Hunter et al.'s probabilistic top-heavy payout/correlation objective, and it does not simulate opponent outcomes or prize structures.

## Research catalog (queued for documented review, not claimed recursively ingested)

- Hunter et al. DFS integer programming: https://arxiv.org/abs/1604.01455
- Grody et al. DFS LP optimization: https://arxiv.org/abs/2411.11012
- Hall et al. stochastic DFS portfolio optimization: http://www.columbia.edu/~mh2078/DFS_Revision_1_May2019.pdf
- Dixon-Coles / time weighting explainer: https://dashee87.github.io/football/python/predicting-football-results-with-statistical-modelling-dixon-coles-and-time-weighting/
- PredictionEngine Dixon-Coles guide: https://predictionengine.app/learn/dixon-coles-soccer-model
- Optionally Bayes integer programming: https://optionallybayes.com/posts/intprog_dfs/
- RotoGrinders ownership/leverage: https://rotogrinders.com/articles/dfs-strategy-predicting-ownership-1360237
- FBref scraper repository: https://github.com/hubertsid/football-data-scraper
- Football data webscraping toolkit: https://github.com/sahil-gidwani/football-data-webscraping
- PuLP guide: https://benalexkeen.com/linear-programming-with-python-and-pulp-part-2/
- Unified ingestion architecture: https://gist.github.com/hungson175/b804219579b3c3f6deb53dd0421d071a

An initial high-level review of Hunter et al.'s paper confirms its central portfolio idea is to approximate the probability that at least one entry wins using joint entry-score relationships, then optimize expected score subject to variance/correlation controls; the current Hamming-distance portfolio solver is a simpler baseline, not a reproduction of that method. The Dixon-Coles correction applies tau only to 0-0, 0-1, 1-0 and 1-1, and weights historical log-likelihood contributions by exponential recency weights. Grody et al. concerns daily fantasy baseball and is a methodological reference, not evidence that the same objective wins in soccer. No recursive hyperlink traversal or exhaustive source ingestion is claimed. Source terms, licensing, data availability, citations, and reproducibility must be reviewed before any source is integrated. Do not scrape sites or use datasets for commercial model training unless permitted.

## Local commands

```bash
python -m pip install -r dfs_optimizer/requirements.txt
python -m pytest dfs_optimizer/tests -q
python -m dfs_optimizer.src.automation.main --players players.csv --roster-size 9 --salary-cap 100 --positions-json '{"GK":1,"DEF":3,"MID":3,"FWD":2}'
```

The values above are examples only; replace them with the actual FantasyFi contest configuration. GitHub Actions run 39685486625 on commit 80e66ce42b1a2e711db05f9830b30426d9087c41 passed Python compilation and all 30 tests (6 dependency deprecation warnings). Later source changes must be revalidated by the next CI run.


## Functional workarounds added after the initial draft

### 1. Repeatable test gate
The repository's GitHub Actions test workflow runs `python -m pytest dfs_optimizer/tests -q` on pushes to feature branches and pull requests. A configured workflow is not proof of a pass: check the Actions run associated with the latest commit and inspect logs if it fails. The code was not marked production-validated until a green run is visible.

### 2. Official lineup readiness gate
`dfs_optimizer/src/lineup_gate.py` validates a user/provider-supplied official lineup snapshot. It requires a timezone-aware kickoff and confirmation timestamp, status marked confirmed/official, unique player IDs, exactly 11 starters per team, a fresh confirmation timestamp, and kickoff 45–75 minutes away. The dashboard blocks optimization by default unless this gate passes. This is the fail-closed workaround while no authorized live-lineup API is configured; it never fabricates confirmed XIs.

### 3. Historical player event data
`dfs_optimizer/src/data_acquisition.py --include-events --max-matches 3` optionally downloads selected historical StatsBomb Open Data match events and lineups in addition to results. Then run:
```bash
python -m dfs_optimizer.src.statsbomb_player_stats --data-root data/external/statsbomb --output data/external/statsbomb/player_match_stats.csv
```
Upload the resulting CSV in the dashboard. StatsBomb coverage is selected, not complete, and its open-data terms are intended for research; cite StatsBomb and check current terms before publishing. The adapter currently approximates on-field minutes and goals conceded from match events/scores. Aerial metrics unavailable in event records remain unpopulated rather than invented.

### 4. Player-level feature and distribution estimates
`dfs_optimizer/src/player_data.py` ingests canonical per-player/per-match CSV data and estimates recent per-90 rates for passes, interceptions, cards, goals, assists, chances created, saves, aerial-win rate and set-piece shots. It uses Beta(1,1) smoothing for penalty conversion/save rates and retains sample counts. Include zero-minute player-fixture rows whenever available; otherwise appearance probabilities are selection-biased. The historical goal rate is a proxy, not true xG. Pass-count PMFs are used only when expected minutes match the observed profile minutes; otherwise the model uses its documented linear approximation.

### 5. Top-heavy portfolio objective
`dfs_optimizer/src/portfolio_simulation.py` evaluates portfolio score distributions by Monte Carlo using shared simulated player outcomes across lineups, and optionally compares them with a supplied opponent field. It reports 50th/95th/99th percentile best-entry scores and field-relative win/top-percentile estimates only when opponent entries are provided. This is a transparent practical workaround, not an exact reproduction of Hunter et al.'s Gaussian pairwise approximation or Hall et al.'s full opponent-choice model. Player score standard deviations and opponent entries must be representative; otherwise the output is a scenario, not a calibrated chance of winning.

### Safe operating sequence
1. Run tests and require a green CI run.
2. Download a small historical StatsBomb sample with `--include-events --max-matches 3` and inspect the manifest/skipped records.
3. Convert it to player-match CSV; manually review a few known matches against source event pages.
4. Upload historical player stats and a current salary/position slate to the FantasyFi optimizer page.
5. Upload an official confirmed lineup CSV with current timestamps; the app fails closed if the snapshot is stale or outside the configured lock window.
6. Compare single-lineup projections and multi-entry simulations to a simple baseline on held-out historical slates before using entries.

StatsBomb source: https://github.com/hudl/open-data and specification: https://github.com/hudl/open-data/tree/master/doc. Dixon–Coles source: https://rss.onlinelibrary.wiley.com/doi/pdf/10.1111/1467-9876.00065. Hunter et al.: https://arxiv.org/abs/1604.01455. Hall et al.: https://pubsonline.informs.org/doi/pdf/10.1287/mnsc.2019.3528.
