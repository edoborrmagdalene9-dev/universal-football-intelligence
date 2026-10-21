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
- `app.py`: local Streamlit dashboard for data validation, backtesting, ownership and simulation.
- `src/pipeline.py`: match/contest CSV validation and chronological baseline backtesting.
- `src/data_acquisition.py`: opt-in StatsBomb Open Data season downloader and source manifest.
- `tests/`: unit tests.

## Launch the dashboard
```bash
python -m streamlit run dfs_optimizer/app.py
```
The dashboard runs locally. Once installed, it can analyse local CSVs offline.

## Obtain public research data
List currently available StatsBomb competition-season IDs:
```bash
python -m dfs_optimizer.src.data_acquisition --list
```
Download a selected competition-season after choosing IDs from that listing:
```bash
python -m dfs_optimizer.src.data_acquisition --competition-id 2 --season-id 44
```
Replace the example IDs with the actual IDs listed by the command. The downloader stores data locally and writes a source manifest. It does not bundle data in this repository. Check the provider's current terms, attribution and publication requirements before use. Historical DFS contest entries must be sourced separately under permitted terms.

## Modelling cautions
- Dixon–Coles is a low-score correction to a scoreline model, not itself a full bivariate Poisson model.
- Team xG alone cannot identify individual fantasy points; minutes, event rates and exact platform scoring are needed.
- A Dirichlet distribution alone is not a learned ownership model. Historical contest-entry data and calibration are required.
- Portfolio tail/payout optimization needs joint outcome simulation, contest payout structure and opponent-field assumptions. Variance alone is not a reliable substitute.
- Do chronological out-of-sample backtests, compare simple baselines, record missing data, and avoid leakage.
- Live data, real-time lineup news, player tracking/biomechanics, fitted copula dependence, full platform scoring, and payout-calibrated tournament objectives remain future work.

See `../docs/ufi-dfs-optimizer-roadmap.md` and `../docs/ufi-integrated-app.md` for staged requirements.
