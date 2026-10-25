# Live market shock, weather lookup, and unseen-match validation

## Added app capabilities

- **Live match feed:** existing UFI proxy now requests score/state, events, lineups, statistics, referees and venue where the provider supplies them. The browser refresh interval is 10 seconds while the match feed is connected; the proxy cache is 5 seconds for live/fixture detail. This is polling, not a millisecond data stream.
- **Weather lookup:** `/api/weather?lat=..&lon=..&date=YYYY-MM-DD&hour=0..23` uses Open-Meteo hourly temperature, relative humidity, precipitation and wind. No API key is required. The app requires the user to supply verified stadium coordinates and kickoff hour in UTC. It returns source/fetch metadata and warns that gridded weather is not a stadium sensor.
- **Automatic in-play odds adapter:** `/api/inplay-odds?id=FIXTURE_ID&bookmaker=BOOKMAKER_ID&market=MARKET_ID` fetches a single fixture/bookmaker/market from Sportmonks when the account plan includes in-play odds. The browser can poll every 5 seconds and records both capture time and the provider's last-update timestamp. Match-winner labels must include Home, Draw and Away; incomplete market data is rejected. Free plans may not include in-play odds, and a provider bookmaker ID is not the same thing as SportyBet.
- **Market shock circuit breaker:** the app compares two timestamped 1X2 decimal-odds snapshots from the same market/bookmaker, removes each snapshot's overround by normalizing implied probabilities, calculates probability changes and relative price movement, and checks timestamp freshness. A large shift or stale/future timestamp pauses the current forecast. A modest fresh move only makes a small bounded adjustment to user-supplied remaining-goal xG; it does not infer a goal, red card, penalty or cause from prices alone.
- **Chronological exact-score backtest:** upload CSV columns `date,home_team,away_team,home_goals,away_goals` (optional `league` or `league_code`). Forecasts use earlier matches only; all matches on the same date are predicted before that date is added to history. It compares a rolling team attack/defence Poisson model against a league-average Poisson baseline, reporting out-of-sample exact-score top-1 hit rate and exact-score negative log likelihood. Results can be exported as CSV.

## Why the model must be allowed to discard a match

A sharp price move is a **review trigger**, not proof that the bookmaker is hiding a result or that a goal is certain. Possible causes include an actual event, a feed correction, a suspension/reopen, liquidity, differing bookmaker prices, or market noise. UFI should discard or pause when:
- snapshot timestamps are missing, stale, out of order or in the future;
- prices are not from the same market/bookmaker/market definition;
- the score/minute does not reconcile with the event feed;
- live feed age or provider status exceeds the configured freshness limit;
- the model's score-state inputs are incomplete or inconsistent.

Do not use an odds shock alone to force a scoreline or raise stakes. After a shock, refresh the match events and verify score, minute, cards, penalties, substitutions and VAR status. If the cause remains unknown, keep the forecast paused.

## Data-source limits

Sportmonks is the configured football provider in the backend adapter; the account must have a valid server-side `SPORTMONKS_API_TOKEN` and coverage for the competition/fields. The code cannot create a provider account, grant a subscription, or deploy a backend without the user's hosting/account authorization. Sportmonks documentation notes that in-play odds require advanced data access on supported plans; if the endpoint is unavailable, the monitor stops instead of inventing odds. The static GitHub Pages app cannot securely store provider secrets. Open-Meteo is the weather source and requires location/time inputs.

Official references:
- Sportmonks API documentation: https://docs.sportmonks.com/football/
- Sportmonks football API and coverage: https://www.sportmonks.com/football-api/
- Sportmonks in-play odds documentation: https://docs.sportmonks.com/v3/tutorials-and-guides/tutorials/odds-and-predictions/live-inplay-odds
- Open-Meteo API documentation: https://open-meteo.com/en/docs
- Football-Data.org API reference (alternative basic fixtures/results/lineups coverage): https://www.football-data.org/documentation/api

## Validation scope and acceptance gate

The backtest is a results-only walk-forward diagnostic. It does **not** yet backtest all live event, referee, lineup, weather, player-foot, odds-shock and tactical inputs, because those require timestamped historical snapshots aligned to each match. Do not claim those features improve accuracy until each feature group is tested on the same unseen fixtures and beats simple baselines on proper scoring rules.

Before calling this production-ready:
1. Deploy the proxy to a controlled HTTPS host and configure the token as a server secret.
2. Confirm provider competition coverage and that returned fixture payloads actually include referees, venue, lineups, events and stats for the selected league.
3. Verify source timestamps and stale-feed behaviour during live matches.
4. Run historical CSV tests with 100+ matches per evaluated competition where possible; preserve a final date range that is not used for tuning.
5. Add archived odds snapshots and live-state snapshots if odds-shock and in-play probabilities are to be calibrated retrospectively.
6. Report sample sizes, log loss, Brier score/calibration, baseline comparison and confidence intervals. A high top-1 exact-score hit rate on a tiny sample is not proof of an edge.
