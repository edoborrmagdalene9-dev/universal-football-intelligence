# Crainee Background Engine — Match-Can-Break-This-Way Simulator

This additive module flags hypothetical structural fractures using an underdog head-start toggle, defensive-error tendency, transition pacing, weather friction, referee disruption and a simplified 5400-unit pitch coordinate.

## Important corrections to the supplied draft
- `underdogScoredFirst` is true only when explicitly supplied as true. The original `value || true` made it always true.
- Missing nested objects receive safe defaults rather than throwing.
- Inputs are range-checked.
- The existing confidence-percentage feature is retained as a heuristic signal-strength indicator: `confidence = min(100, ruptureIndex / breakThreshold × 100)`. `confidenceStatus` is `HEURISTIC_SIGNAL_PERCENT_NOT_CALIBRATED_PROBABILITY` and `confidenceIsProbability` is `false`. This percentage is **not** the chance of an upset; it only indicates how strongly this hand-built index crosses its configured threshold.
- Scorelines are scenario candidates for exploration, not model probabilities or guaranteed outcomes.

## Example
```js
const {simulateMatchBreakScenarios}=require('./crainee-background-break-engine');
const result=simulateMatchBreakScenarios({
  ballPositionUnit: 5400,
  underdogScoredFirst: true,
  favorite: {defenderErrorTendency: 8},
  underdog: {attackerTransitionPacing: 9},
  environment: {isHeavyRainOrWind: false},
  referee: {whistleFrequencyChaos: 1.4}
});
```

Both rupture index and confidence percentage are heuristic signals, not calibrated probabilities. For example, 62.5% does **not** mean a 62.5% chance of an upset. Validate and calibrate against held-out historical fixtures before interpreting any output probabilistically.
