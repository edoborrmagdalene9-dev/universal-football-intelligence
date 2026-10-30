# Historical 1X2 slip audit — deployment and use

## What was added
- An additive **Historical 1X2 slip screen** in the existing Slip & Odds Lab.
- POST API route: `/api/slip/historical-audit`.
- Downloads and caches the public `schochastics/football-data` Parquet results archive on first use, then screens up to 50 picks.
- Existing OCR, manual slip parsing, strict risk audit, calculator and other UFI modules remain in place.

## Input
One fixture per line:

`YYYY-MM-DD | Competition | Home team | Away team | Home/Draw/Away`

The UI requires explicit fixture names and selection. It does not infer a home/draw/away selection from vague bet-slip text.

## Runtime requirements
Render build command: `pip install -r requirements-historical-audit.txt && python -m compileall -q tools`

Keep the existing start command: `python tools/ufi_multi_provider_server.py`.

## Honest limitations
- The archive contains results, not historical bookmaker odds.
- Its transparent smoothed frequency baseline is not trained/calibrated and does not establish positive expected value.
- Historical cutoff, per-pick model cutoff, sample counts and insufficient history are shown.
- Current injuries, lineups, tactical changes and market prices are not included in this screen.
- A failed download or missing dependency must show an error, never a successful audit.

## Verification
Run `python -m unittest discover -s tests -p "test_historical_1x2_audit.py" -v`, then smoke-test the deployed POST route with one valid fixture and one invalid date. Do not consider the feature end-to-end verified until both succeed.
