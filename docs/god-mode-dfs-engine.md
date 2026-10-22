# UFI / FantasyFi advanced DFS engine — implementation and limitations

This is an additive research extension. Existing UFI pages, scoring, FantasyFi optimizer, event simulation, historical backtesting, StatsBomb/OpenFootball workflows and microbehavioral lab remain in place.

## Added modules
- 300-metric audit registry: six categories of 50 metrics. Registry fields are schema-only until licensed, timestamped observations are supplied; they are not claimed to be trained or available.
- Dixon-Coles model already present in the codebase: inspect and test the existing implementation before relying on it. The scoreline engine must report grid tail mass and be evaluated chronologically against simple Poisson and market baselines.
- Spatial kinematics: derive speed (m/s), acceleration (m/s²), distance and high-intensity distance from observed timestamped player coordinates. Fixture names or screenshots cannot reconstruct 3D trajectories. No automatic point bonus follows from pitch dimensions.
- Ownership engine already present; validate it against actual historical contest-entry selections. Ownership estimates without entry data are not live projections.
- Pre-lock helper: configured HTTPS JSON or CSV ingestion, freshness checks and confirmed-starter filtering. HTTPS does not prove official authority; configure an allowlisted licensed provider before any automatic player exclusion.
- Portfolio helpers: Hamming-distance diversity and captain/vice multiplier assignment. Existing PuLP/CBC is MILP, not MIQP. Quadratic covariance optimization requires a compatible solver and linearization or a true MIQP backend.

## Exact FantasyFi rulebook retained
Starter +4, substitute +2, forward goal +40, midfielder goal +50, defender/GK goal +60, shot on target +6, assist +20, chance created +3, each 5 completed passes +1 using floor, interception +4, tackle +0, goalkeeper save +6, penalty save +50, clean sheet +20 for DEF/GK at >=55 minutes, goal conceded -2, yellow -4, red -10, own goal -8, penalty missed -20. Confirm platform rules and avoid double-counting goal shots on target.

## 60-minute pre-lock operations
A fixture schedule and official licensed lineup endpoint are prerequisites. Convert each kickoff to UTC, check provider timestamp and identity, preserve source evidence, and fail closed when stale or ambiguous. This code does not bundle live provider credentials or claim to fetch official lineups automatically.

## Validation contract
Run chronological out-of-sample tests; report Brier score, log loss, calibration and uncertainty. Validate player score distributions against settled platform scores. Top-1 finishes cannot be guaranteed. Pitch width does not automatically increase interceptions or passing points; test such hypotheses on observed evidence. Respect provider licensing and rate limits.
