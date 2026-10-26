# UFI multi-provider live data

## Important credential safety
Never put provider keys in HTML, JavaScript, issue comments, logs, or Git. Use the host's environment/secret manager. If a key was pasted into a chat, screenshot, repository, or shared document, revoke/rotate it and issue a replacement before deploying. The example file contains empty placeholders only.

## Deploy
Use the Render blueprint at `render.yaml`, or start the server with:

```sh
python tools/ufi_multi_provider_server.py
```

Configure the variables in the backend secret manager. The GitHub Pages frontend should call the HTTPS backend URL; it should never receive provider credentials. The server retains the original Sportmonks routes and adds:
- `GET /api/providers/status` — configured/not-configured status only, not a connectivity test.
- `GET /api/odds/sportsgameodds?sportID=SOCCER&leagueID=EPL&oddsAvailable=true&limit=50`
- `GET /api/odds/the-odds-api?sport=soccer_epl&regions=uk&markets=h2h`
- `GET /api/odds/sharpapi` — provisional adapter for the supplied base URL; confirm its exact endpoint/query contract in SharpAPI's own account docs before relying on it.
- `GET /api/weather/weatherapi?q=lat,lon` or add `&date=YYYY-MM-DD` for forecast data.
- `GET /api/weather?lat=..&lon=..&date=YYYY-MM-DD&hour=0..23` — Open-Meteo; no key needed; includes temperature, humidity, precipitation, precipitation probability and wind speed.
- `GET /api/ev?probability=0.25&odds=4.5` — transparent expected-return arithmetic.
- `GET /api/arbitrage?odds=2.1,3.8,3.9` — checks the supplied mutually exclusive outcomes for a theoretical arbitrage margin.

The new odds routes are adapters, not proof that all feeds are connected to the UI/model. Provider response shapes differ; normalize events into the shared UFI match context before the prediction supervisor consumes them. SharpAPI's schema is marked provisional until verified from provider documentation.

## Quota-saving strategy
- Prefer cached reads: SportsGameOdds is cached for 10 minutes (matching the documented free-tier update cadence); The Odds API is cached for 90 seconds; SharpAPI for 120 seconds; WeatherAPI for 30 minutes.
- Request one necessary market and one region, avoid polling finished fixtures, and fetch only events inside the required time window. Do not poll every provider for every page refresh.
- Use a provider selector/fallback policy: detailed football feed for fixture/event data when configured; use odds providers for prices; use Open-Meteo first for ordinary weather; use WeatherAPI only when its additional fields or coverage are needed.
- Never call a fallback provider after a definitive empty response unless coverage is uncertain; record which source supplied each field.
- Free tiers have finite limits and coverage. No implementation can guarantee that requests never run out. Cache, scheduled refresh, conditional refresh, and provider usage monitoring reduce consumption.

## Operational caveats
`/api/providers/status` only confirms that a secret exists. It does not make a paid API available on a free plan or prove live connectivity. Odds API quota headers are returned when supplied by the provider. SportsGameOdds free-tier updates may be delayed; it is not a suitable second-by-second live feed. Weather is a gridded forecast, not stadium sensor telemetry. Exact-score EV depends on independently validated probabilities and fresh prices; it is not a profit guarantee.
