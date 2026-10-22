# UFI integrated research app

## Start locally
Python 3.10+:
```powershell
python -m pip install -r dfs_optimizer/requirements.txt
python -m streamlit run dfs_optimizer/app.py
```
The app opens a local dashboard. Internet is needed to install dependencies or obtain external datasets, not to analyse local CSVs.

## Current surfaces
- Match CSV validation, duplicate/malformed row reporting.
- Expanding-window chronological score-grid baseline with validation and held-out test metrics.
- Exact-scoreline hit rate, result accuracy and multiclass Brier score.
- Historical contest entry upload and empirical player/pair ownership summaries.
- Event-level player-points simulation with quantiles.
- Continuous-time goal-event score-state sandbox.
- CSV/JSON report export and CI test workflow.

## Data acquisition and terms
No real dataset is bundled or falsely labelled as validated. Use official provider pages and preserve source, retrieval date, competition, season, terms, schema version and transformation steps in a manifest.

- StatsBomb Open Data: https://github.com/hudl/open-data . Selected competitions/seasons only; attribution and other conditions apply. Check the current agreement before use or publication.
- Football-Data.co.uk: https://www.football-data.co.uk/ provides historical results and some statistics/odds. Check current terms and data dictionary.
- These sources do not include historical paid DFS contest entries by default. Ownership analysis requires contest-entry data whose terms permit the intended use. Do not bypass gated access.

## Backtest design
Each forecast uses only earlier-dated matches. The baseline estimates global home/away scoring rates from an expanding history. This verifies the pipeline and provides a benchmark, not a final model.

Next: fit team attack/defence and time decay on training data only; add provider-specific event and lineup parsers; calibrate minutes/event rates and dependence out of sample; implement platform scoring and payout tables; compare mean, ceiling, portfolio and payout-aware objectives using identical simulated outcomes; add provenance, missingness/drift alerts and uncertainty intervals.

A passing CI run proves tested code paths work; it does not prove forecast quality or profitability. Existing modules remain intact; future capabilities should be isolated behind adapters.
