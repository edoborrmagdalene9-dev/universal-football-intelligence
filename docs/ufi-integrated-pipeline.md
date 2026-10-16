# UFI integrated Phase 1–3 pipeline

The integrated runner coordinates match prediction, player-evidence auditing, and timestamp-aware paper validation in one run.

## Run locally

From the repository root with Python 3.10+ (standard library only):

```bash
python -m unittest discover -s tests -p "test_*.py" -v
python tools/ufi_integrated_pipeline.py --matches output/openfootball/matches.csv --out output/openfootball/integrated
```

The matches CSV can be created with the OpenFootball downloader documented in [openfootball.md](data-sources/openfootball.md). The integrated runner calls the advanced chronological backtest and writes:

- `output/openfootball/integrated/advanced/metrics.json`
- `output/openfootball/integrated/advanced/advanced_predictions.csv`
- `output/openfootball/integrated/advanced/paper_betting_ledger.csv`
- `output/openfootball/integrated/ufi_integrated_report.json`
- `output/openfootball/integrated/ufi_integrated_report.md`

## Phase 1 — match model

The current benchmark compares Elo, rolling venue-specific goal-rate Poisson, a fixed 50/50 ensemble, and a league-frequency baseline. All fixtures on a calendar date are forecast before results from that date update the model because this results source does not provide reliable kickoff timestamps. Review accuracy, Brier score and log loss together; lower Brier/log loss are better.

## Phase 2 — player evidence

Copy `data/templates/player_registry_template.csv` to the git-ignored path `data/private/player_registry.csv` and populate only sourced observations. Keep unknown footedness/style values unknown, cite source URLs, and separate real-world observations from game-specific tags such as “Fox in the Box” and “Orchestrator”.

The integrated pipeline audits player records and evidence coverage. It deliberately does **not** use player fields in match forecasts yet: the OpenFootball results-only dataset does not identify which players appeared in each match, their minutes, or the timestamp at which player information became available. The next integration requirement is a licensed/suitable player-match participation dataset with lineups, starts/sub appearances and minutes, joined to fixtures using stable player IDs and kickoff timing. Until then, player-aware predictions would be unsupported.

## Phase 3 — odds and paper validation

Copy `data/templates/pre_match_odds_template.csv` to the git-ignored path `data/private/pre_match_odds.csv` and add odds only when the source terms permit your intended use. Required columns include:

- Match key: `date,league_code,home_team,away_team`
- Decimal odds: `home_odds,draw_odds,away_odds`
- Time evidence: `captured_at_utc,kickoff_at_utc` as timezone-aware ISO 8601 timestamps, with capture time strictly earlier than kickoff
- Provenance: `source_name,source_url`

Run the integrated command again. Only matched records with valid odds and pre-kickoff timestamps enter the flat-one-unit paper ledger. ROI remains null when no eligible odds join exists. Never put private data, API keys or credentials in this public repository; `data/private/` is git-ignored.

## Current gate status and honest limits

A successful workflow means the pipeline executed and its checks passed. It does not mean all three data requirements are complete: the default public workflow has results but no sourced player records or supplied odds, so player-aware forecasting remains gated and betting ROI is not computed. No model can guarantee winning bets. Evaluate on multiple unseen chronological windows and compare to a market baseline before making claims about edge.
