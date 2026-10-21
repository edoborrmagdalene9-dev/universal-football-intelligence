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

The values above are examples only; replace them with the actual FantasyFi contest configuration. Tests have not been represented as passing until executed in a connected runtime.
