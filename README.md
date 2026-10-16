# Universal Football Intelligence (UFI)

A local-first football research workstation for exploring real match-event data, tactical evidence, player observations, scoreline scenarios, slip odds and forecast validation.

## Published app structure

- `index.html` — application shell and modules
- `styles.css` — responsive desktop/mobile interface
- `app.js` — data source adapter, calculations, UI and local persistence

## Modules

1. **Real match data:** fetches the public StatsBomb Open Data competition index, selected season match lists, event files and lineup files where available.
2. **Match & tactical lab:** event filters, team/player search, event type summaries, shot/xG summaries, source-coordinate pitch plot and CSV export.
3. **Player intelligence:** editable profiles for role/style notes, preferred foot and weak-foot evidence, source URL, confidence, plus a substitution observation log. These records are user-maintained, not automatically verified universal player facts.
4. **Scenario engine:** independent Poisson scoreline grid, 1X2, over 1.5/2.5/3.5 and both-teams-to-score summaries, visible goal-cap tail mass and assumptions checklist.
5. **Slip & odds lab:** parses pasted selection text, calculates decimal-odds implied probability and combined odds, supports manual selection editing, correlation group notes and local saving.
6. **Backtesting:** settled 1X2 forecasts, normalized probabilities, accuracy, multiclass Brier score, log loss and CSV export.
7. **Research library:** source links, match notes, player observations, hypotheses and experiments.
8. **Workspace backup:** export/import saved local records as JSON.

## Additional historical data sources

- **Football-Data.co.uk:** valuable historical results, bookmaker odds and selected match statistics across multiple leagues/seasons. Its stated terms restrict use to private individuals and exclude commercial or data-training products using automated bots/scrapers/AI. Because UFI is AI-assisted, bulk ingestion and model training are **not enabled** until permission is confirmed. See [the source assessment and safe integration plan](docs/data-sources/football-data-co-uk.md).
- Do not commit third-party bulk match datasets or API secrets to this public repository. Preserve source provenance, missing values and odds timestamps, and use chronological backtesting without future-data leakage.

## Authenticated historical data adapter

- [TheStatsAPI integration notes](docs/data-sources/thestatsapi.md)
- [Local historical match downloader](tools/thestatsapi_download.py)
- The downloader keeps API keys out of code and writes datasets to the git-ignored `data/private/thestatsapi/` directory.
- **Not yet data-loaded:** an API key and permitted account access are required. Start with one league/season and check current quota/pricing before broad downloads. The client currently downloads finished match records and metadata only; odds, xG, events, lineups, player statistics and tracking need separate adapters and validation.

## Run / deploy

The app is static and can be hosted with GitHub Pages. In the repository, open **Settings → Pages**, select **Deploy from a branch**, choose `main` and `/(root)`, and save. The public website URL usually follows `https://<owner>.github.io/<repository>/`; confirm the exact URL and deployment status in GitHub Pages settings.

## Data and technical limits

- StatsBomb Open Data contains selected competitions/seasons only. It is not a full live all-league feed and does not require an embedded API key for public repository files.
- Network access is required to fetch match data. Browser cross-origin access or source availability may change.
- Event coordinates are event locations from the dataset, not full optical player tracking or every player's continuous movement.
- There is no automatic universal SportyBet booking-code decoder or robust screenshot OCR in this version.
- Complete verified weak-foot labels, eFootball-style play styles, injuries, current availability and causal substitute impact cannot be inferred for every player. Record sources and keep unknowns unknown.
- LocalStorage data is stored in the current browser/device and does not automatically sync across devices. Export workspace backups regularly.
- Independent Poisson scenarios are a transparent baseline, not a complete match simulator. Goal caps omit tail probability. Probabilities are estimates, never guaranteed outcomes.
- Backtesting is only meaningful when forecasts are logged before outcomes, data leakage is avoided, and enough unseen matches are evaluated against baselines.

## Responsible use

This is a football research and evaluation tool, not a promise of betting profit. Verify source data, record uncertainty, protect private information and never treat an output as a sure bet.