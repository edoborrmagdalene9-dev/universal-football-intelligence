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
   - New: **Multi-match player evidence dataset** lets you save a loaded match’s player-event rows, deduplicates by match/team/player, aggregates totals across saved matches, and exports the evidence CSV. It remains descriptive and does not feed forecasts until exposure and identity are verified.
   - **Observed player event profile** builds a single-match summary from loaded event data (shots, goals, source xG, passes, carries, pressures, duels and other recorded actions), optionally attaches lineup position labels, and exports CSV. It does not infer footedness or universal playing style and does not yet feed forecasts.
4. **Scenario engine:** independent Poisson scoreline grid, 1X2, over 1.5/2.5/3.5 and both-teams-to-score summaries, visible goal-cap tail mass and assumptions checklist.
5. **Slip & odds lab:** extracts OCR text from uploaded screenshots, structures likely decimal odds and market labels, flags ambiguous rows for review, exports a structured CSV, calculates implied probability and combined odds only for valid prices, and supports manual editing/correlation notes. A fixture-candidate matcher compares explicit team pairs against the currently loaded StatsBomb competition-season list, records candidate ID/date/orientation, and flags missing or ambiguous matches; market-to-model matching is still separate. See [the slip-to-intelligence bridge guide](docs/ufi-slip-intelligence-bridge.md).
6. **Backtesting:** settled 1X2 forecasts, normalized probabilities, accuracy, multiclass Brier score, log loss and CSV export.
7. **Research library:** source links, match notes, player observations, hypotheses and experiments.
8. **Workspace backup:** export/import saved local records as JSON.

## Additional historical data sources

- **Football-Data.co.uk:** valuable historical results, bookmaker odds and selected match statistics across multiple leagues/seasons. Its stated terms restrict use to private individuals and exclude commercial or data-training products using automated bots/scrapers/AI. Because UFI is AI-assisted, bulk ingestion and model training are **not enabled** until permission is confirmed. See [the source assessment and safe integration plan](docs/data-sources/football-data-co-uk.md).
- Do not commit third-party bulk match datasets or API secrets to this public repository. Preserve source provenance, missing values and odds timestamps, and use chronological backtesting without future-data leakage.

## Free public-domain historical results

- [OpenFootball data source and local download guide](docs/data-sources/openfootball.md)
- [OpenFootball downloader](tools/openfootball_download.py)
- No API key is required. The script downloads available seasons for 15 configured leagues and normalizes fixtures/results into a local CSV.
- Output stays under `data/private/openfootball/`, which is git-ignored. The source is public domain, but the result files contain fixtures and scores only—not odds, player traits or full tracking data.

## Authenticated historical data adapter

- [TheStatsAPI integration notes](docs/data-sources/thestatsapi.md)
- [Local historical match downloader](tools/thestatsapi_download.py)
- The downloader keeps API keys out of code and writes datasets to the git-ignored `data/private/thestatsapi/` directory.
- **Not yet data-loaded:** an API key and permitted account access are required. Start with one league/season and check current quota/pricing before broad downloads. The client currently downloads finished match records and metadata only; odds, xG, events, lineups, player statistics and tracking need separate adapters and validation.

## Run / deploy

The app is static and can be hosted with GitHub Pages. In the repository, open **Settings → Pages**, select **Deploy from a branch**, choose `main` and `/(root)`, and save. The public website URL usually follows `https://<owner>.github.io/<repository>/`; confirm the exact URL and deployment status in GitHub Pages settings.

## Integrated Phase 1–3 research pipeline

- [How to run the integrated pipeline](docs/ufi-integrated-pipeline.md)
- `tools/ufi_integrated_pipeline.py` coordinates chronological match-model evaluation, player-registry evidence auditing, and timestamp-validated odds/paper evaluation.
- `tools/ufi_probability_market_audit.py` compares historical model probabilities with margin-normalized market probabilities, reports Home/Draw/Away probability gaps, and compares Brier/log-loss scores. It requires timestamped pre-kickoff odds and is research-only; see [the run guide](docs/ufi-integrated-pipeline.md#probability-versus-market-audit-new).
- The GitHub Actions workflow packages a unified JSON/Markdown report with predictions and metrics. Player attributes are intentionally not used as model features until sourced player-to-match participation data exists; ROI is omitted without eligible pre-match odds.

## Unified football mathematics research design

- [Unified architecture: football physics, human/player evidence, Bayesian and quantum-inspired probability experiments, betting-slip odds, market value, correlation, and rigorous validation](docs/ufi-unified-mathematics.md)
- This is a staged research design, not a claim that all components are implemented. Physics features require suitable event/tracking data; player-aware predictions require verified player-match participation; quantum-inspired methods must beat simpler models in chronological tests.

## UFI development roadmap

- [Evidence-first roadmap for data validation, leakage-safe forecasting, player intelligence, substitutes and evaluation](docs/ufi-next-phase-roadmap.md)

## Data and technical limits

- StatsBomb Open Data contains selected competitions/seasons only. It is not a full live all-league feed and does not require an embedded API key for public repository files.
- Network access is required to fetch match data. Browser cross-origin access or source availability may change.
- Event coordinates are event locations from the dataset, not full optical player tracking or every player's continuous movement.
- There is no automatic universal SportyBet booking-code decoder. Screenshot OCR uses Tesseract.js and requires internet access; fixture matching is a conservative candidate aid, not authoritative bookmaker mapping.
- Complete verified weak-foot labels, eFootball-style play styles, injuries, current availability and causal substitute impact cannot be inferred for every player. Record sources and keep unknowns unknown.
- LocalStorage data is stored in the current browser/device and does not automatically sync across devices. Export workspace backups regularly.
- Independent Poisson scenarios are a transparent baseline, not a complete match simulator. Goal caps omit tail probability. Probabilities are estimates, never guaranteed outcomes.
- Backtesting is only meaningful when forecasts are logged before outcomes, data leakage is avoided, and enough unseen matches are evaluated against baselines.

## Responsible use

This is a football research and evaluation tool, not a promise of betting profit. Verify source data, record uncertainty, protect private information and never treat an output as a sure bet.
- **Approximate player exposure audit:** player-match profiles now preserve lineup-derived appearance status and clearly labelled estimated minutes where the loaded lineup and substitution events support a rough estimate. These are not official minutes and are not forecast features; validate against an authoritative source before any per-90 calculation.


## Strict Slip Auditor
- Combines existing slip photo OCR, parsed markets, fixture candidate matching, scenario-to-market probabilities, player/lineup evidence and the saved forecast ledger.
- Adds per-leg cut/hold reasons, current-news search links, user-attested context checks, source URL and notes, replacement candidate tagging and JSON audit export.
- It deliberately leaves shortlist slots empty when three fully reviewed candidates cannot be qualified. Alternatives must be added and modelled individually; no match inherits another match's expected-goal assumptions.
- Current news/lineup checkboxes are user attestations, not automatically verified facts. The static app opens external searches but does not fetch/authenticate their contents.
- See [UFI research source register](docs/ufi-research-source-register.md) for the supplied reading list, related sources and implementation limits.
