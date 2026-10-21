# Additive DFS Soccer Optimizer

This is an **additive, isolated research module** for Universal Football Intelligence (UFI). It does not replace or modify existing match prediction, football biomechanics, player analysis, slip auditing, or other app features.

## Status
Research baseline only, not a production-ready or profitable system. Use a platform-specific player pool, salary/position rules, scoring rules, and permitted data sources before evaluating real contests.

## Install and test
Python 3.10+:
```bash
python -m pip install -r dfs_optimizer/requirements.txt
python -m pytest dfs_optimizer/tests -q
```

## Included
- `src/dc_model.py`: Poisson baseline plus Dixon–Coles low-score correction and score-grid summaries.
- `src/optimizer.py`: binary integer-programming lineup solver via PuLP/CBC.
- `src/portfolio.py`: Hamming distance and overlap checks.
- `src/projections.py`: configurable player-point expectation helper.
- `src/cli.py`: offline synthetic demo.
- `tests/`: unit tests.

## Modelling cautions
- Dixon–Coles is a low-score correction to a scoreline model, not itself a full bivariate Poisson model.
- Team xG alone cannot identify individual fantasy points; minutes, event rates and exact platform scoring are needed.
- A Dirichlet distribution alone is not a learned ownership model. Historical contest-entry data and calibration are required.
- Portfolio tail/payout optimization needs joint outcome simulation, contest payout structure and opponent-field assumptions. Variance alone is not a reliable substitute.
- Do chronological out-of-sample backtests, compare simple baselines, record missing data, and avoid leakage.
- Live scraping and automated lineup submissions are intentionally not enabled by this initial offline foundation.

See `../docs/ufi-dfs-optimizer-roadmap.md` for staged requirements.
