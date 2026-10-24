# Automatic data and exact-score validation: practical workaround

## What can and cannot be automatic

The static GitHub Pages UI cannot safely hold a paid-provider API key. Browser-only calls either expose the key or depend on public feeds that do not cover every league or metric. The reliable pattern is:

1. **Frontend:** GitHub Pages remains the existing UI.
2. **Secret-safe data proxy:** deploy `tools/ufi_live_data_proxy.py` to a small HTTPS backend (Replit, Render, or a VPS). Store `SPORTMONKS_API_TOKEN` as a server environment secret, never in JavaScript, HTML, Git, logs, or exported reports.
3. **Live match centre:** the proxy exposes `/api/live`, `/api/fixtures?date=YYYY-MM-DD`, `/api/fixture?id=PROVIDER_FIXTURE_ID`, and `/api/health`. The fixture response requests score/state, participants, events, lineups and statistics in one API call. The provider plan must cover the target league and xG fields.
4. **Refresh policy:** live scores/events are cached for 15 seconds; date fixtures for 5 minutes. Respect provider rate limits and plan quotas. If the provider fails, show stale/unknown data and its fetch time—never silently treat old data as current.
5. **Historical training:** continue using UFI's existing permitted OpenFootball and StatsBomb sources. Their coverage differs: results-only records can fit score-rate baselines; event/xG/player features require competitions with those fields. Do not fill missing xG with invented numbers.
6. **Forecast evaluation:** fit only on earlier matches and score on later unseen matches. Compare a league-average Poisson baseline, rolling team attack/defence rates, and the richer feature model on identical test fixtures. Log exact-score log loss, 1X2 Brier/log loss, calibration bins, coverage and sample size. Tactical/player features are retained only if the time-ordered test shows repeatable improvement.
7. **Live-state estimates:** after the score/time changes, update remaining-goal distributions using historical match states matched by minute, score difference, red cards and pre-match strength. Until that conditional model has adequate out-of-time validation, display current score/events and mark live probabilities **experimental / unavailable**, rather than pretending the pre-match Poisson grid is a live model.

## Provider choice and cost reality

Sportmonks documents a single fixture endpoint with nested score, state, event, lineup and statistics includes, plus xG where included by the plan. See [its match-centre integration guide](https://www.sportmonks.com/blogs/how-to-build-a-match-page-with-the-sportmonks-football-api/). The public/free plan is limited by league coverage, and paid coverage/quotas can change. Confirm the leagues and xG entitlement before paying. The proxy is provider-specific; it does not make a provider subscription free.

Alternative providers include API-Football; its documentation describes fixtures/events, lineups and player statistics, but the exact fields and access depend on the plan: [API-Football docs](https://apifootball.com/documentation/).

## Deploy the proxy

- Deploy `tools/ufi_live_data_proxy.py` as a Python web service with start command `python tools/ufi_live_data_proxy.py`.
- Add environment variable `SPORTMONKS_API_TOKEN` in the hosting provider's secret/environment settings.
- Set `UFI_ALLOWED_ORIGIN` to the exact deployed UFI Pages origin, e.g. `https://edoborrmagdalene9-dev.github.io` (or the origin actually shown in your address bar).
- Use HTTPS; do not expose an unauthenticated proxy to unrestricted public use. Add host-level access control/rate limits before public production use.
- Test `/api/health`, then `/api/fixtures?date=YYYY-MM-DD`, then `/api/live`. An empty response may mean no fixtures, unavailable league coverage, or provider schema/plan restrictions; inspect the provider's response safely without printing the token.
- The current static exact-score panel is still a manual-input baseline until the API endpoint is connected in the UI. This proxy creates the safe data route, but does not itself deploy the backend or activate provider access.

## Honest acceptance gates

- **Historical calibration:** use a chronological train/validation/test split; freeze each forecast before kickoff; compare against baselines on the same fixtures; report confidence intervals and sample size.
- **Live state:** verify minute, score, event sequence and data age; reconcile duplicate/out-of-order events; invalidate or flag stale feeds; train and validate remaining-goal probabilities on historical in-play snapshots.
- **Lineups/cards/substitutions/shots/xG:** store source name, provider match ID, source timestamp, fetched timestamp, field-level missingness and corrections. xG is provider/model-specific; do not mix it as if definitions are identical.
- **Tactical/player feature tests:** ablate feature groups one at a time on chronological unseen fixtures. Report log loss/Brier changes and uncertainty. Do not claim a feature helps merely because it explains one miss.
- **Fail-safe:** if API key, provider, coverage, freshness or data-quality checks fail, show unavailable/unknown and fall back only to clearly labelled historical baseline. No “sure score” or automatic stake escalation.
