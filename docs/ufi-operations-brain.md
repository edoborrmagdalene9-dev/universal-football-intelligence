# UFI operations brain (additive)

This module adds shared policy primitives without replacing existing score engines.

## Included
- Nigeria wall clock uses `Africa/Lagos`; at exactly 21:00 WAT, phase changes from `qualification` to `nightly_preparation`.
- Persistent SQLite tables for blacklist, versioned market rules, fixture decisions, three unit ledgers, and phase-run status.
- Blacklist supports all-market (`all`/`*`) or market-specific scope and optional competition/expiry.
- Qualification fails closed unless the filtering prompt explicitly passes, a linked rule has status `validated`, required data is present and fresh, and configured odds conditions pass.
- Three independent unit ledgers, idempotent settlement keys, absorber/boost mode, four-life counter, and one qualifying daily failure pause per unit.
- Unit accounting never transfers funds between units. A cycle success resets lives to four and mode to normal as specified.

## Critical current limits
- The user's exact natural-language filtering/blacklisting prompt has not yet been supplied to the repository as a machine-readable policy. Until wired and tested, `prompt_pass` must not be assumed true; the gate rejects unknown policy status.
- This module does not itself ingest fixtures, historical odds, event timelines, or Telegram messages. Existing adapters and workers must call it; this commit does not claim those integrations are complete.
- SQLite is only durable if the deployment has persistent storage. Ephemeral GitHub-hosted runners lose local files after the run. Configure a persistent database/storage layer before unattended scheduled execution.
- The existing experimental live worker is separate and still requires verified provider coverage and secrets.
- The 21:00 transition is a phase decision primitive, not a process-kill command. Settlement, audit logging and state persistence must continue during nightly preparation.
- No staking is placed automatically. The result `QUALIFIED_FOR_REVIEW` is not a guarantee of a winning or profitable bet.

## Local checks
Run:
```sh
python -m unittest tests.test_ufi_operations_brain -v
```

## Suggested secure configuration
Store Telegram credentials in GitHub Actions/Render secrets, never source files. Do not enable real alerts until a chat ID, token, provider contract, persistent state, and an end-to-end delivery test are configured. The token visible in the supplied screenshot should be revoked and replaced.
