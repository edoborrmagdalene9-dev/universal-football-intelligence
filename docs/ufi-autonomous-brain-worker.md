# UFI autonomous brain worker (additive)

This worker coordinates existing UFI APIs; it does not replace the UI, prediction engines, odds panel or historical backtests.

## Initial behaviour
- Polls today's and tomorrow's fixture endpoints plus /api/live.
- Sends a review-only Telegram/email kickoff reminder inside UFI_KICKOFF_ALERT_MINUTES (default 10).
- Captures timestamped live snapshots in SQLite.
- Optional live review trigger: 0-0 at minutes 10-25, at least 3 combined shots on target OR at least 8 total shots and 20 dangerous attacks, plus a provider-returned explicitly labelled Over 0.5 first-half price between 1.18 and 1.25.
- Does not place bets, infer missing stats as zero, invent odds, or call this a validated edge.

## Important production gates
1. Sportmonks provider bookmaker/market IDs are not SportyBet IDs automatically. Configure UFI_BOOKMAKER_ID and UFI_OVER05_HT_MARKET_ID only after verifying returned market/outcome labels and prices.
2. The trigger numbers are research hypotheses, not proven profitable thresholds. A historical 88% win-rate cutoff is insufficient: test chronologically, account for multiple testing, compute confidence intervals, and compare price-implied break-even probability and expected value on unseen matches.
3. The current API feed may not include reliable shots/dangerous attacks or a live price for every match. The worker skips a signal when required fields/price are absent.
4. Email requires SMTP settings; Telegram requires bot token/chat ID. Store secrets only in host/GitHub secrets. Never commit tokens.
5. SQLite works for local tests. A Render Cron Job's filesystem is ephemeral: production deduplication and historical snapshots require a durable database or persistent store. Do not schedule this as a production cron until persistence is configured.
6. Five-minute polling can miss short price windows; provider updates may be slower. This is polling, not a guaranteed millisecond feed.

## Environment variables
UFI_BACKEND_URL (default deployed backend); UFI_STATE_DB (local SQLite path); TELEGRAM_BOT_TOKEN; TELEGRAM_CHAT_ID; SMTP_HOST; SMTP_PORT (default 587); SMTP_USERNAME; SMTP_PASSWORD; SMTP_FROM; ALERT_EMAIL_TO; UFI_KICKOFF_ALERT_MINUTES (10); UFI_LIVE_MINUTE_MIN (10); UFI_LIVE_MINUTE_MAX (25); UFI_MIN_TOTAL_SHOTS_ON_TARGET (3); UFI_MIN_TOTAL_SHOTS (8); UFI_MIN_TOTAL_DANGEROUS_ATTACKS (20); UFI_TARGET_ODDS_MIN (1.18); UFI_TARGET_ODDS_MAX (1.25); UFI_BOOKMAKER_ID; UFI_OVER05_HT_MARKET_ID.

## Local validation
python -m unittest tests.test_ufi_live_brain_worker -v
python -m py_compile tools/ufi_live_brain_worker.py

## Next
Configure durable storage and secrets; validate provider payloads on multiple competitions; capture live snapshots; train per-league/per-state rules using chronological holdout tests; expose a rulebook with sample size, out-of-sample hit rate, confidence interval, odds band, expected value, calibration and last retrain date. Only promote rules after they pass these gates.
