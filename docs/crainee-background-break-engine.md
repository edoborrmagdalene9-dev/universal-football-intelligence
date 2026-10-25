# Crainee Background Engine — Match-Can-Break-This-Way Simulator

This additive module flags hypothetical structural fractures using an underdog head-start toggle, defensive-error tendency, transition pacing, weather friction, referee disruption and a simplified 5400-unit pitch coordinate.

## Important corrections to the supplied draft
- `underdogScoredFirst` is true only when explicitly supplied as true. The original `value || true` made it always true.
- Missing nested objects receive safe defaults rather than throwing.
- Inputs are range-checked.
- The output does not manufacture a confidence percentage from a rupture score. `confidence` is null and `confidenceStatus` is `NOT_ESTIMATED`.
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

The rupture index is a heuristic signal. Validate usefulness on held-out fixtures before treating it as predictive.
