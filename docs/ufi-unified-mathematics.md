# UFI unified mathematics: football, human movement, probability and market odds

## Purpose

This is the research design for the next UFI intelligence layer: connect the user's football-physics ideas, player and tactical evidence, match probabilities, and the odds visible on uploaded betting slips. The objective is calibrated probability estimates and evidence-based price comparison—not a guaranteed-pick machine.

## One connected evidence-to-decision pipeline

1. **Read the slip, don't trust OCR blindly.** Extract fixture, market, selection, and decimal odds from each image. Keep the original image available for review, assign field-level OCR confidence, and require confirmation for uncertain teams, markets, or digits. Deduplicate repeated selections and resolve the exact fixture before analysis.
2. **Build the real match record.** Join historical results, event data, lineups, minutes, substitutions, player IDs, and team context only where source terms allow it. Preserve source, timestamp, competition, season, and missingness. Never pretend a results-only file contains player or tracking information.
3. **Represent the players and match state.** Where evidence exists, encode preferred/weak foot, role, observed style, minutes, substitute status, rest, opponent, scoreline, red cards, and tactical context. Keep real-world observations separate from eFootball labels such as “Fox in the Box” or “Orchestrator.” A label is not a verified fact unless its source supports that claim.
4. **Use physics where the data can identify it.** At event or tracking level, measurable features can include shot distance and angle, body/ball geometry, movement speed, acceleration, pressure, passing lanes, and keeper position. The goal mouth and pitch are geometric constraints. These features may help explain shot or event probabilities when reliable coordinates exist. They cannot be reconstructed from final scores alone, and Newtonian mechanics does not by itself predict a whole match.
5. **Estimate match outcomes with probabilistic models.** Establish simple baselines first, then compare calibrated goal models (Poisson or Dixon–Coles where appropriate), team-strength/Elo models, and player/event models. Combine models only when chronological validation shows a benefit; do not assume an arbitrary 50/50 blend is best. Monte Carlo sampling can turn estimated scoring distributions into scoreline, 1X2, totals, and both-teams-to-score probabilities.
6. **Treat “quantum-style maths” as a testable modelling idea, not magic.** UFI may experiment with probabilistic state representations, Bayesian updating, uncertainty distributions, and interactions between features. Quantum-inspired mathematics has no automatic predictive advantage for football; it must beat simpler models on held-out matches after accounting for complexity and calibration. Actual quantum computing is not required.
7. **Compare UFI with the bookmaker's price.** Convert decimal odds to raw implied probabilities p = 1 / odds; calculate market overround and normalize for a first-pass no-vig market probability. Compare UFI's calibrated probability with the market estimate and calculate expected return EV = p_UFI × decimal_odds − 1 for a one-unit stake, before fees, limits, and settlement rules. A positive estimated EV is a hypothesis, not proof of an edge. Use conservative uncertainty intervals and minimum evidence thresholds; if the evidence is weak, return “no bet / insufficient evidence.”
8. **Analyze the whole slip, not only each leg.** Estimate each selection's probability and odds, detect duplicated or conflicting markets, flag same-match correlation, calculate combined odds, and distinguish the naive product of leg probabilities from a model that accounts for dependence. If joint probabilities cannot be supported by data, clearly mark the combined estimate as unreliable rather than multiplying probabilities as if every leg were independent.
9. **Test in time order.** Freeze predictions before kickoff, use only features known at that timestamp, and evaluate untouched chronological periods. Report Brier score, log loss, calibration, sample size, per-league/market performance, uncertainty, and paper ROI only when complete, authorized, pre-kickoff odds and verified settlements exist. Compare against a market baseline. Keep every prediction so misses can be examined.
10. **Learn from results without fooling ourselves.** Update parameters only from settled, time-ordered records. Use ablation tests to learn whether footedness, substitutions, physics-derived features, or a new mathematical component actually improves forecasts. Avoid tuning repeatedly on the same test set.

## The user's high-goal scenario idea

The number of scoreline scenarios should not be chosen because a bigger number seems more powerful. Choose a goal grid from the training data's scoring distribution and validate tail coverage. For a Poisson rate lambda, the probability beyond a cap K is P(G > K) = 1 − sum(P(G = k), k = 0..K). Report this omitted tail mass. Increase the cap adaptively when tail mass exceeds a chosen tolerance, and test extreme-score coverage on held-out matches. A 15- or 20-goal cap is a computational boundary, not a way to force a match into a more likely result.

## Required evidence gates

- **Slip gate:** fixture and odds parsed; uncertain OCR reviewed; market rules identified.
- **Data gate:** source and permitted use recorded; team names and fixture joined unambiguously.
- **Timing gate:** every feature and odds quote existed before kickoff.
- **Player gate:** stable player IDs and match participation/minutes verified before player data affects predictions.
- **Physics gate:** coordinate definitions and tracking/event quality are known; no invented body or ball measurements.
- **Model gate:** calibration and performance tested out of sample against baselines.
- **Market gate:** odds margin, market type, correlation, settlement, and uncertainty handled.
- **Betting gate:** default output is a ranked research shortlist or “no bet,” never “sure bet.” Start with paper evaluation.

## Current implementation status

The repository already has a chronological Elo/Poisson backtest, a coordinated Phase 1–3 pipeline, a player evidence registry audit, odds timestamp checks, and a browser slip/odds workspace. This document specifies how those pieces should connect over time; it does not claim that screenshot OCR, complete player data, tracking physics, quantum-inspired models, or an automatic edge detector are already fully implemented. The public OpenFootball results pipeline remains results-only, so it cannot alone deliver the complete system described here.

## Immediate implementation order

1. Verify the newest integrated GitHub Actions run and fix any regressions.
2. Add a market-aware evaluation layer for user-supplied, authorized odds snapshots: no-vig probabilities, expected value, uncertainty, and comparisons to UFI forecasts.
3. Improve slip-image extraction with confidence and explicit user review, then map parsed selections to exact fixtures and markets.
4. Add suitable player-match data with stable IDs and pre-kickoff timestamps.
5. Add event-level geometry/physics features only when source data supports them.
6. Experiment with Bayesian or other quantum-inspired probability representations only as challengers to the simpler validated models.
7. Keep paper-trading results separate from real-world profit claims.
