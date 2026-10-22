# UFI sourced integrations and operational setup

## Executable connectors
- StatsBomb Open Data: source https://github.com/statsbomb/open-data. Python functions in dfs_optimizer/src/source_connectors.py fetch the public competition index, selected matches and events. Coverage is selective. Events are not optical tracking; event locations must not be treated as continuous motion.
- Open-Meteo: https://open-meteo.com/en/docs. The fetch_open_meteo function retrieves temperature, humidity, precipitation and wind near kickoff. Attribute Open-Meteo under CC BY 4.0 and respect service terms/rate limits.
- OpenFootball: https://github.com/openfootball provides open historical results. The Dixon-Coles fitter accepts normalized rows with date, home_team, away_team, home_goals, away_goals. Preserve source/version and evaluate chronologically.
- Football-Data.co.uk: https://www.football-data.co.uk/data.php provides historical scores/odds/basic stats, but its terms describe private-person use and restrict commercial/automated AI scraping. Manual authorized import only unless terms or a license change.
- Player events: StatsBomb event records can support derived metrics only for covered matches. The connector explicitly labels event locations as event_location_not_tracking.
- 3D movement: derive_player_kinematics needs measured timestamped coordinates; actual 3D speed requires measured z_m. Use a licensed optical-tracking provider or authorized tracking file.
- Ownership: estimate_historical_ownership calculates posterior means and Beta credible intervals from authorized long-form contest-entry exports. It is contest- and slate-specific.
- Calibration: ChronologicalIsotonicCalibrator trains on earlier observations and reports Brier, log loss and calibration error on a later holdout. It is not trained until a sufficiently large historical forecast/outcome dataset is supplied.
- Captain/vice and risk: optimize_captain_vice_lineup jointly chooses roster, captain and vice with configurable salary multipliers. scenario_risk_report measures covariance, upper-tail and lower-tail outcomes from shared Monte Carlo scenarios.

## Scheduled 60-minute pre-lock automation
GitHub Actions workflow .github/workflows/ufi-prelock.yml runs every 15 minutes and checks fixtures inside the next 60 minutes. To enable:
1. Repository Settings -> Secrets and variables -> Actions: add secret UFI_FIXTURE_FEED_URL pointing to an authorized fixture JSON endpoint.
2. Add secret UFI_LINEUP_API_BASE_URL if the fixture feed lacks per-fixture lineup_url; add UFI_LINEUP_API_TOKEN only if the licensed provider requires it.
3. Add repository variable UFI_LINEUP_TRUSTED_HOSTS containing comma-separated exact provider hostnames. Do not use wildcard hosts.
4. Fixture payload format: {"fixtures":[{"fixture_id":"...","kickoff_utc":"2026-10-22T18:00:00Z","lineup_url":"https://trusted-host/..."}]}. Lineup payload needs players (or lineups) with player_id, team_id, status and source_timestamp.
5. Run the workflow manually and inspect the ufi-prelock-audit artifact. It fails closed on untrusted hosts and stale data.

Alternative: set repository variable UFI_LINEUP_PROVIDER=api_sports, secret UFI_LINEUP_API_TOKEN, and variables UFI_API_SPORTS_LEAGUES (comma-separated league IDs) and UFI_API_SPORTS_SEASON (season year). The adapter queries https://v3.football.api-sports.io/fixtures and /fixtures/lineups with the documented x-apisports-key header. Official docs: https://www.api-football.com/documentation-v3#tag/Fixtures/operation/get-fixtures-lineups. Lineups are available only for covered competitions and typically appear 20–40 minutes before kickoff; this provider may be paid or quota-limited. The recorded timestamp is retrieval time, not a claimed provider publication time. No credentials are bundled. Without provider configuration, scheduled runs skip. A universal official lineup API for all leagues is not freely available.

## The 300-field source audit
metric_source_catalog() outputs all 300 unique fields with a source family, URL or required provider, status and limitation. currently_populated=False is intentional: a source strategy is not an observed value. audit_source_coverage distinguishes a column being present from non-null coverage. Fields unsupported by public sources remain marked unavailable until a licensed provider or measured dataset supplies them.

## Research source register
dfs_optimizer/src/research_source_catalog.py registers the user-provided papers, tutorials and repositories: Hunter et al.; Grody et al.; Hall et al.; Dixon-Coles; PredictionEngine; Optionally Bayes; RotoGrinders; StatsBomb; OpenFootball; Football-Data; PuLP guide; ingestion gist; Open-Meteo; and scikit-learn. Run `python scripts/index_research_sources.py` from the repository root to create research_source_graph.json. The crawler honors robots.txt, only follows the seeded host allowlist, limits depth/pages, and records page titles/link graph/hashes rather than copying whole articles. This is a traceable register and link-discovery workaround, not a claim that every linked citation and outbound link has been exhaustively read. Crawling is bounded by licensing, relevance and security rather than following arbitrary links indefinitely.
