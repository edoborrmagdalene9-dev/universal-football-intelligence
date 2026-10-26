# Universal Football Intelligence (UFI)

UFI is an existing football research and exact-score analysis app. Changes in this repository are additive: preserve the existing browser app, Python proxy, prediction tools, historical evaluation, and tests.

## Current architecture and limits

- The static browser app is published through GitHub Pages.
- `tools/ufi_live_data_proxy.py` is the original secret-safe provider proxy. It exposes the existing health, fixtures, live, fixture, weather and in-play-odds routes.
- `tools/ufi_multi_provider_server.py` wraps the original proxy and adds multi-provider odds, weather, provider status/health, match-context normalization, expected-value arithmetic and arbitrage arithmetic. Run this entrypoint for the extended API.
- Backend API keys belong only in the backend environment/secret manager. `.env.example` contains blank placeholders; never commit real keys or put them in browser JavaScript.
- The normalized provider feed currently bridges into fixture matching. It does **not** automatically feed every prediction engine. Missing scores, events, lineups and statistics must remain unknown rather than being fabricated.
- Provider connectivity, league coverage, quota, event freshness and plan eligibility require live checks. A configured secret is not proof that a provider is reachable or that a particular endpoint is included in its free tier.
- `tools/exact_score_walkforward.py` compares rolling-origin independent-Poisson and league-average baselines on historical results. Results-only tests do not establish that tactical, player, live-feed or market features improve unseen-match accuracy.
- No model can guarantee correct scores or profit. Keep probability calibration, chronological holdouts, market-margin handling and uncertainty visible.

## Run the existing Python backend

Python is kept unchanged. Install no new framework merely to run the proxy; the current server uses the Python standard library for its HTTP server and outbound requests.

```sh
python tools/ufi_multi_provider_server.py
```

The server listens on `PORT` (default 8080) and prints a startup message. Set secrets as environment variables in the host's secret manager. See [multi-provider live data and quota strategy](docs/multi-provider-live-data.md).

## Hosting note — no Render or Railway

The repository does not require Render or Railway. A Replit project can run the existing Python entrypoint without converting it to another language. However, Replit's free Starter publishing is limited and the published link expires after 30 days; republishing is required, and that is not a verified permanent, always-on free backend. Do not assume unlimited free hosting or enable paid usage without checking the account's current limits first. The current GitHub Pages site remains static and will not reach a backend until its HTTPS base URL is configured in the app.

## Existing data and validation documentation

- [Automatic data and validation workaround](docs/automatic-data-and-validation-workaround.md)
- [Live market shock, weather and unseen-match validation](docs/live-market-shock-and-walkforward-backtest.md)
- [Multi-provider live data and quota strategy](docs/multi-provider-live-data.md)

## Multi-provider API routes

- `GET /api/providers/status` — reports whether secrets are configured; does not test connectivity.
- `GET /api/providers/health?providers=sportsgameodds,theoddsapi,weatherapi,sharpapi,openmeteo` — performs explicit live checks and may consume provider quota; results are cached for five minutes.
- `GET /api/matches` — normalized fixture/match context from configured providers.
- `GET /api/odds/sportsgameodds?sportID=SOCCER&leagueID=EPL&oddsAvailable=true&limit=50`
- `GET /api/odds/the-odds-api?sport=soccer_epl&regions=uk&markets=h2h`
- `GET /api/odds/sharpapi` — provisional until the account-specific SharpAPI endpoint contract is verified.
- `GET /api/weather/weatherapi?q=lat,lon`
- `GET /api/weather?lat=..&lon=..&date=YYYY-MM-DD&hour=0..23` — Open-Meteo weather estimate.
- `GET /api/ev?probability=0.25&odds=4.5` — transparent expected-return arithmetic.
- `GET /api/arbitrage?odds=2.1,3.8,3.9` — checks caller-supplied exhaustive outcomes for theoretical arbitrage.

Provider keys previously exposed in chats, screenshots or repository files should be revoked and rotated before deployment. Free tiers have finite quotas; caching and selective polling reduce usage but cannot guarantee unlimited requests.
