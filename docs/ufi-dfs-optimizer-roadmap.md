# UFI DFS Optimizer Roadmap

This is an additive research module. Existing UFI features and files must remain unchanged.

## Stage 1 — reproducible baseline
- Define exact platform scoring, roster rules, player IDs, salary and eligibility.
- Validate Dixon–Coles against independent Poisson and market-implied baselines.
- Keep timestamps and source provenance; prevent pre-match data leakage.
- Run unit tests and the synthetic offline demo.

## Stage 2 — player projections
Required: expected minutes, player-level goal/assist/event rates, opponent, role/position, confirmed availability, scoring rules, salary and timestamp. Team xG cannot determine individual fantasy points on its own.

## Stage 3 — ownership and contest objective
Ownership projections require historical contest ownership/entry data and calibration. A Dirichlet distribution alone does not learn ownership from player attributes. Ultimately estimate payout/rank distribution against the actual payout structure and field assumptions.

## Stage 4 — correlated portfolio simulation
Model shared team goals, assists, minutes, substitutions and opponent effects. Evaluate portfolios with joint simulation, expected payout, top-percentile rate, drawdown and sensitivity checks. Compare with single-lineup and random feasible baselines.

## Stage 5 — live data and automation
Only add connectors after confirming access rights, terms, rate limits, data schemas and failure handling. Use secrets for credentials. A scheduled workflow must not assume all competitions lock at one time; require configurable fixture-specific lock times and test mode. Do not auto-submit entries or spend funds without explicit user-controlled approval.

## Deferred, not falsely claimed complete
The current baseline does not yet implement fitted time-decay Dixon–Coles parameters, Dirichlet ownership regression, calibrated leverage, a full stochastic portfolio objective, captain/MVP salary multipliers, or live ingestion. These are later milestones, each needing data and tests.
