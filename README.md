# Automatic data and walk-forward evaluation

- [Automatic data and validation workaround](docs/automatic-data-and-validation-workaround.md) documents the secret-safe backend architecture and provider limitations.
- `tools/ufi_live_data_proxy.py` exposes `/api/health`, `/api/fixtures?date=YYYY-MM-DD`, `/api/live`, and `/api/fixture?id=ID` using a server-side `SPORTMONKS_API_TOKEN`. Deploy it to a trusted HTTPS backend and configure the backend URL in the Exact-score intelligence panel. The provider token must never be entered in the browser or committed to Git.
- The Exact-score intelligence panel now supports fixture/live-feed loading and refreshes the live endpoint every 30 seconds while the app page is open after you connect. It can populate team names from a provider fixture. **It does not yet automatically infer goal rates or claim live probabilities are validated.**
- `tools/exact_score_walkforward.py` evaluates two transparent baselines on historical results using rolling-origin predictions: league-average independent Poisson and rolling team attack/defence rates. Example: `python tools/exact_score_walkforward.py results.csv --min-history 100 --window 10 --out report.json`. Input columns: `date,home_team,away_team,home_goals,away_goals`. The script is results-only; richer xG/player/tactical features require separately sourced data and ablation tests.
- Live provider coverage, xG entitlement, quotas and current pricing depend on the provider plan. Automatic refresh only works when a backend is deployed, a valid secret is configured, and the provider supports the requested competitions. Missing or stale data must remain visibly missing.


- [Live market shock, weather and unseen-match validation](docs/live-market-shock-and-walkforward-backtest.md) documents the new price-movement circuit breaker, Open-Meteo lookup and chronological exact-score evaluation panel.
- The Exact-score panel now refreshes the configured live feed every 10 seconds while connected; backend live cache is 5 seconds. This is provider polling, not a millisecond feed. The new `/api/weather?lat=..&lon=..&date=YYYY-MM-DD&hour=0..23` route returns hourly Open-Meteo weather for supplied stadium coordinates and UTC kickoff hour.
- The market-shock panel compares timestamped 1X2 prices, pauses on large/stale/future-dated changes, and only makes bounded adjustments for fresh modest shifts. It does not automatically know the cause of a price move and must not be treated as a prediction guarantee.
- The historical UI backtest uses prior matches only and compares a rolling team-rate Poisson model with a league-average baseline. It is results-only; player/tactical/live-feed/odds-shock improvements still need timestamped aligned historical data and separate unseen tests.
- The secret-safe proxy exposes `/api/inplay-odds?id=FIXTURE_ID&bookmaker=BOOKMAKER_ID&market=MARKET_ID`; the app can poll a configured provider bookmaker/market every 5 seconds and compare timestamped price snapshots. Sportmonks in-play odds are not available on every plan; a provider bookmaker ID does not automatically mean SportyBet odds.


## Multi-provider live-data integration

The existing single-provider proxy remains available. For the expanded provider adapter routes and normalized match-context console, deploy the new entrypoint `tools/ufi_multi_provider_server.py` using the Render blueprint in `render.yaml`. Set credentials only in the backend secret manager; `.env.example` contains blank placeholders.

Read [multi-provider live data and quota strategy](docs/multi-provider-live-data.md) before enabling providers. New endpoints include `/api/providers/status`, `/api/matches`, `/api/odds/sportsgameodds`, `/api/odds/the-odds-api`, `/api/odds/sharpapi`, `/api/weather/weatherapi`, `/api/ev`, and `/api/arbitrage`. The Exact-score intelligence view now includes a provider console that calls the backend; keys are not entered in the browser.

Provider keys exposed in chat, screenshots or repository files should be revoked and replaced before deployment. Free-tier quotas and league coverage are finite; caching and selective polling reduce usage but cannot guarantee unlimited requests. Provider response normalization is not the same as validated live probability modeling.
