# Historical 1X2 slip audit — deployment and use

## What was added
- A new **Historical 1X2 slip screen** in the existing Slip & Odds Lab.
- A new POST route: `/api/slip/historical-audit`.
- The route downloads and caches the public `schochastics/football-data` Parquet results archive on first use, then screens up to 50 picks.
- Existing OCR, manual slip parsing, strict audit, calculator and other modules are untouched.

## Input
One fixture per line:

`YYYY-MM-DD | Competition | Home team | Away team | Home/Draw/Away`

Example:

`2026-10-30 | Premier League | Arsenal | Chelsea | Home`

The UI deliberately requires the user to confirm fixture names and selection. It does not infer a home/draw/away selection from vague bet-slip text.

## Required Render build configuration
The existing service was previously reported to use `python -m compileall -q tools` as its build command. That command does not install Parquet dependencies. Set the Render service build command to:

```sh
pip install -r requirements-historical-audit.txt && python -m compileall -q tools
```

Keep the existing start command unchanged:

```sh
python tools/ufi_multi_provider_server.py
```

Do not replace existing environment variables. The dataset is cached under `.cache/ufi-historical` by default; on an ephemeral Render filesystem it may need to be downloaded again after a restart/redeploy.

## Honest limitations
- The archive is historical results, not historical bookmaker odds.
- The baseline is a transparent, smoothed frequency screen; it is not trained/calibrated and does not establish positive expected value.
- Historical cutoff, sample sizes and insufficient team history are shown. The system does not guarantee identification of a "spoiler".
- Current injuries, lineups, tactical changes and market prices are not included in this historical-only screen.
- A failed data download or missing dependency returns a visible error; it must not be interpreted as a successful audit.

## Verification
Run:

```sh
python -m unittest discover -s tests -p "test_historical_1x2_audit.py" -v
```

Then verify on the deployed Render origin:
1. Open Slip & Odds Lab.
2. Enter one fixture using the five-field format.
3. Run the screen and confirm the source cutoff, sample counts and probabilities render.
4. Export the JSON report.
5. Test an invalid row and confirm a clear validation error.
