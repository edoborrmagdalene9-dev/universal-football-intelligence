# UFI data readiness and evidence-pipeline repair

Status date: 2026-11-24

## Architecture

- The interactive browser application is published through GitHub Pages at `https://edoborrmagdalene9-dev.github.io/universal-football-intelligence/`.
- Render hosts the JSON backend at `https://universal-football-intelligence.onrender.com`; its root is not the browser UI. The `/api/health` route is the backend health check.
- The browser fixture loader previously fetched SportyBet and ESPN directly but did not call the Render multi-provider normalized fixture route. It therefore bypassed the provider aggregation backend.

## Live read-only provider observations

Observed from Render on 2026-11-24:

| Provider | Configuration / connectivity | Interpretation |
|---|---|---|
| Sportmonks | `/api/health` reported tokenConfigured=true; date fixture request returned no accessible records and used fallback | Token exists; requested-date fixture coverage is not verified |
| SportsGameOdds | Connectivity probe succeeded; one record returned in health probe | Accessible league coverage is plan-limited; current default is MLS |
| The Odds API | Connectivity probe succeeded; 20 records returned for EPL; 498 requests remaining after probe | Working for tested sport; quota must be protected |
| WeatherAPI | Connectivity probe succeeded; current weather response returned | Working for tested location |
| SharpAPI | Response received | Provisional; endpoint/query contract must be verified before critical evidence use |
| Open-Meteo | HTTP 429 during probe | Rate-limited; WeatherAPI is an available fallback |

The previous `/api/matches?sport=soccer_epl` implementation returned the first non-empty provider feed, which was SportsGameOdds' default MLS feed. It short-circuited before trying The Odds API even though the direct EPL odds route returned 20 records. The revised normalized endpoint aggregates configured provider records, supports a bounded comma-separated `sports` list (maximum 16), deduplicates by teams/kickoff, and merges source/odds provenance.

## Browser integration

The browser's "Load current fixtures" workflow now requests the Render `/api/matches` route for a bounded eight-competition The Odds API list and combines those records with the existing SportyBet and ESPN sources. It deduplicates fixture rows and carries the provider evidence payload through fixture matching. SportyBet remains the source for SportyBet-specific prices; other bookmaker prices are not relabelled as SportyBet prices.

## 400-signal audit changes

- The strict slip workflow now constructs its signal evidence before invoking the 400-signal evaluator. Previously the evidence was only serialized after evaluation and therefore could not influence the evaluator.
- The evaluator consumes explicit per-signal evidence and preserves evidence provenance (`FETCHED` / `ESTIMATED`) separately from check result (`ASSESSED`).
- `PENDING`, `FAIL`, and `NOT_APPLICABLE` remain distinct.
- Total coverage and applicable-check coverage are reported separately. `NOT_APPLICABLE` is never counted as a pass.
- Pre-match live-state-only checks and demonstrably irrelevant market-family checks can be `NOT_APPLICABLE`.
- A fixture match is not accepted as proof of a confirmed starting XI. Confirmed lineups still require an official team sheet or a separately labelled projection.

## Remaining evidence gaps (must not be fabricated)

The current patch does not make unavailable data magically available. Further work is required to connect and validate:
- SofaScore / FotMob / Transfermarkt / official club and league sources for team/player history, player heights, injuries, lineups and player-level statistics.
- Five/ten-match form, home/away splits, xG/xGA, shots and player contributions in a common schema.
- Referee assignments, pitch/weather location resolution, travel/rest and tactical formation inputs.
- Physical duel / height / jump proxies with explicit sample sizes and ESTIMATED provenance.
- All five Crainee engines, all nine Pirates layers, congestion analysis, Dixon-Coles prediction, joint accumulator probability, and final value/Kelly gate in a single verified orchestration run.

## Safety and release status

This patch is additive and does not alter production environment variables or secrets. It has not been deployed to Render. Merge/deploy only after the updated CI suite passes. Provider health probes can consume API quota; routine fixture discovery uses cache and a bounded league list. Do not expose provider secret values in logs or browser responses.
