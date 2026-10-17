# UFI player intelligence registry

This CSV is an evidence ledger, not an automatic player-truth database. Start with `data/private/player_registry.csv` copied from `data/templates/player_registry_template.csv`. Do not fill unknown values by guessing.

## Fields and evidence rules

- `player_id`: stable ID from the cited source when available; never merge names alone if identity is uncertain.
- `source_name` and `source_url`: provenance for each claim. Keep source terms/licensing in mind.
- `preferred_foot`: use `left`, `right`, `both` or `unknown`.
- `weak_foot_evidence`: specific observable evidence and sample context; do not infer weak foot from one highlight.
- `role` and `observed_style_tags`: analyst labels supported by match evidence, not personality claims.
- `efootball_style_tags`: separate game-specific labels such as Fox in the Box or Orchestrator. These are not official real-world labels.
- `minutes_observed`, starts, substitute appearances and evidence window: exposure context matters.
- `confidence_0_to_1`: confidence in the recorded claim, with a note explaining why.
- `record_type`: `source_fact`, `analyst_observation` or `model_estimate`.
- `analyst_notes`: include counterexamples and uncertainty, not only supporting evidence.

## Substitution impact

For each substitution, preserve match ID, minute, score at entry, red-card state if known, incoming/outgoing player IDs, role, source and event evidence. Compare similar match states and minutes; raw win/loss after entry is not causal proof of impact.

## Current data availability

OpenFootball has no player registry fields, lineups, footedness or tracking. The template intentionally contains headers only. Populate it from sources you are authorized to use; the model must not invent missing facts.


## Event-based player profile (browser app)

The Player Intelligence module can now build a descriptive profile for each player who has an attributed event in the currently loaded StatsBomb match. It summarizes event count, shots, goals, source-provided xG, passes and completed-pass event convention, carries, pressures, duels, interceptions, recoveries, clearances, blocks, assists/key-pass indicators where supplied, and first/last recorded event minute. When lineups have separately been loaded, it also marks players found in the lineup and records source position labels. The table can be exported to CSV.

This is deliberately a **single-match event summary**, not a player ability score. Event coverage varies by competition/season; first/last event minutes are not minutes played; no event summary establishes preferred foot, weak foot, substitute impact, or a universal style such as “Orchestrator”. Those require separate source-backed evidence and multi-match exposure. This feature does not yet feed the prediction model.


## Multi-match player evidence dataset

The browser app can save the current single-match event profile into a local player-match evidence dataset. Repeat for additional matches; rows are deduplicated by match ID, team and player. The aggregate table sums observed event counts across saved matches and shows match count and date window. It does **not** calculate per-90 rates because reliable player minutes are not established by first/last event timestamps. It does not yet feed forecasts. Export the CSV or workspace backup to move the data to another device; local browser storage does not sync automatically. Identity changes, transfers, competition coverage and source omissions must be reviewed before comparing players.
