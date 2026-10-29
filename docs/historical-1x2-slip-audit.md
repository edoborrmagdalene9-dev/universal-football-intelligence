# Historical 1X2 slip audit (additive module)

This tool adds a historical home/draw/away screening step without replacing UFI's existing score models, surprise/tactical engines, 5400 gate, odds filters, or live-data tools.

## Source and license
- Dataset: [schochastics/football-data](https://github.com/schochastics/football-data)
- Archive: `data/results/games.parquet`, described by the source as 1,237,935 matches across 207 domestic top-tier leagues and 20 international competitions, 1888–2023.
- License: Open Data Commons Attribution License (ODC-BY 1.0). Preserve attribution to the dataset creator/source. The source warns that older records can contain errors and team identities may be inconsistent.
- This is results-only historical evidence. It is **not** a file of historic pre-match odds, and it does not establish what a bookmaker's price or a model probability was before kickoff.

The Football-Data.co.uk archive was also investigated. Its historical results and odds are useful in principle, but its current site terms describe use as private individuals only and exclude automated bots/scrapers/AI data-training products. This integration therefore does not download or ingest that archive.

## Install
Python 3.10+ is recommended. Install the optional reader dependencies:

```bash
python -m pip install pandas pyarrow
```

## Run
Prepare a UTF-8 CSV, for example:

```csv
date,competition,home_team,away_team,selection
2026-10-30,Premier League,Arsenal,Everton,Home
2026-10-30,Premier League,Team A,Team B,Draw
2026-10-30,La Liga,Team C,Team D,Away
```

Then run from the repository root:

```bash
python tools/historical_1x2_audit.py my-slip.csv --out historical-1x2-audit.json
```

The first run downloads the public Parquet archive to `.cache/ufi-historical/games.parquet`; subsequent runs reuse the cache. Use `--refresh` to fetch it again. The dataset is not committed into Git, avoiding a very large binary in the repository. The JSON report includes the archive's actual latest date, historical sample sizes, baseline H/D/A probabilities, selected-outcome probability, and a risk-screen label.

## Interpretation / guardrails
- `HIGH_RISK_SCREEN` means the selected outcome has under 25% probability under this simple smoothed historical-frequency baseline. `REVIEW` means under 38%. These are investigation flags, not proven spoilers.
- The baseline uses competition-level outcome frequencies, the home team's historical home-side result frequencies, and the away team's historical away-side frequencies. It is deliberately transparent and is not claimed to be calibrated.
- Historical rows dated on/after a fixture date are excluded when the fixture date is supplied. If no valid date is supplied, the tool reports the available archive cutoff and uses all records currently in the archive.
- Team-name mismatches, limited team history, neutral venues, competition changes, and the dataset cutoff can weaken results. The archive's documented end date is 2023, so today's picks need current fixtures, lineup/news, and market evidence as additional independent checks.
- Never call a pick a guaranteed spoiler or claim a guaranteed win/profit. Compare this screen with UFI's existing models and validation gates; do not bypass or delete them.

## App integration status
The script and this guide are an additive repository module. The existing static mobile/web UI and Render data proxy are not modified by this commit, so the feature is **not yet wired into a visible in-app button or automatic slip-ingestion flow**. A follow-up integration must add a controlled backend endpoint or explicit upload workflow and test it on the deployed service before calling it end-to-end complete.
