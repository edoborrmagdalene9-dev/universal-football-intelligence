# Universal Football Intelligence (UFI)

A local-first football research dashboard for exploring real match-event data, comparing teams and players where data is available, generating transparent scoreline scenarios, and backtesting forecasts.

## Current scope

- StatsBomb Open Data competition and match browser
- Match event and shot analysis, including xG where supplied by the source
- Transparent Poisson scoreline scenario explorer based on observed goal rates
- Bet-slip text and decimal-odds implied-probability helper
- Forecast log, manual settlement, Brier score, CSV export, and browser-local persistence
- JSON import/export for research records

## Data limitations

StatsBomb Open Data covers selected competitions and seasons only. This dashboard is not a complete live-data feed. It does not claim to have full-pitch tracking, complete player weak-foot data, or verified eFootball-style player play-style labels for every player. Missing data must remain unknown rather than be guessed.

## Run it

Open `index.html` in a modern browser, or publish the repository with GitHub Pages.

## Enable GitHub Pages

In the repository, open **Settings → Pages**. Choose **Deploy from a branch**, select `main` and `/(root)`, then save. Wait for GitHub Pages to publish the site.

## Responsible use

Scenario probabilities are estimates, not guarantees. Do not treat a model output as a sure bet. Track predictions against later results and evaluate calibration before trusting them.