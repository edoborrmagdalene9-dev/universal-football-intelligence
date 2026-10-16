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
