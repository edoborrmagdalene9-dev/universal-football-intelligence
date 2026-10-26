# UFI multi-provider live data

## Credential safety

Never put provider keys in HTML, JavaScript, issue comments, logs, or Git. Use the backend environment/secret manager. If a key was pasted into a chat, screenshot, repository, or shared document, revoke/rotate it and issue a replacement before deployment. The example file contains empty placeholders only.

## Run the existing Python backend

The original Python implementation is preserved. Run the expanded entrypoint:

```sh
python tools/ufi_multi_provider_server.py
```

It listens on `PORT` (default 8080). Configure credentials only as backend environment secrets. The GitHub Pages frontend must call an HTTPS backend URL; it must never receive provider credentials.

### Replit compatibility and free-tier caveat

The repository includes a `.replit` run configuration for the existing Python entrypoint; it does not convert the backend to JavaScript or replace the app. Import this GitHub repository into Replit to run it in the workspace. Publishing availability and runtime are controlled by Replit's current account limits. Starter includes one published app, but the published link expires after 30 days and must be republished. Therefore this is **not confirmed permanent always-on free hosting**. Do not activate paid deployments or billing to make it work without first approving that cost. The public GitHub Pages frontend remains disconnected until an HTTPS backend URL is configured.

## API routes

- `GET /api/providers/status` — configured/not-configured status only, not a connectivity test.
- `GET /api/providers/health?providers=sportsgameodds,theoddsapi,weatherapi,sharpapi,openmeteo` — explicit live connectivity checks. Clicking the UI button makes real provider requests and can consume quota. Results cache for five minutes. Test one provider with `&provider=theoddsapi` to limit quota use.
- `GET /api/matches` — normalized fixtures and match context from a configured provider.
- `GET /api/odds/sportsgameodds?sportID=SOCCER&leagueID=EPL&oddsAvailable=true&limit=50`
- `GET /api/odds/the-odds-api?sport=soccer_epl&regions=uk&markets=h2h`
- `GET /api/odds/sharpapi` — provisional adapter for the configured base URL; confirm its exact endpoint/query contract against SharpAPI's account-specific documentation before relying on it.
- `GET /api/weather/weatherapi?q=lat,lon` or add `&date=YYYY-MM-DD` for forecast data.
- `GET /api/weather?lat=..&lon=..&date=YYYY-MM-DD&hour=0..23` — Open-Meteo hourly estimate, no API key required.
- `GET /api/ev?probability=0.25&odds=4.5` — transparent expected-return arithmetic.
- `GET /api/arbitrage?odds=2.1,3.8,3.9` — checks supplied mutually exclusive exhaustive outcomes for a theoretical arbitrage margin.

The provider console dispatches normalized `/api/matches` results into the main app. The main-app bridge merges valid home/away fixtures into the existing fixture-matching workspace. It does **not** yet feed every prediction engine automatically. It must not claim missing scores, events, lineups or statistics. Provider response shapes differ, and SharpAPI's schema remains provisional until verified against the account-specific contract.

## Quota-saving strategy

- Prefer cached reads: SportsGameOdds is cached for 10 minutes; The Odds API for 90 seconds; SharpAPI for 120 seconds; WeatherAPI for 30 minutes.
- Request one necessary market and one region, avoid polling finished fixtures, and fetch only events in the required time window.
- Use a provider selector/fallback policy: detailed football feed for fixture/event data when configured; odds providers for prices; Open-Meteo first for ordinary weather; WeatherAPI only when additional fields or coverage are needed.
- Do not call fallback providers after a definitive empty response unless coverage is uncertain; record which source supplied each field.
- Provider quotas and coverage are finite. Caching and selective refresh reduce consumption but cannot guarantee unlimited requests.

## Operational caveats

`/api/providers/status` only confirms that a secret exists. It does not make a paid API available on a free plan or prove live connectivity. The Odds API quota headers are exposed when supplied by the provider. SportsGameOdds updates may be delayed and are not a second-by-second live feed. Weather is a gridded estimate, not stadium sensor telemetry. Exact-score EV depends on independently validated probabilities and fresh prices; it is not a profit guarantee.
