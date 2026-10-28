# Crainee Unconventional Outcome Engine

An additive exact-score exploration module for Universal Football Intelligence. It deliberately generates a separate shortlist that is not filtered by bookmaker odds or the main model's ranking.

## Behaviour
- **Break away from the favourite:** starts from a broad bounded score grid, excludes the main model's exact pick, and ranks materially different candidates for exploration.
- **Alternate realities:** includes early underdog goal, red-card disruption, favourite dominates but blanks, clinical underdog, chaotic open game, and late equaliser paths.
- **Controlled randomness:** pass a seed to reproduce the same candidate list. The result includes the seed and a stable seed hash.
- **Protect unexpected candidates:** returns `unconventionalShortlist` separately from optional `conventionalShortlist`. Each unconventional candidate is labelled `EXPLORED_POSSIBILITY`, has `probability: null`, and is never represented as a calibrated probability.

## API
```js
const { generateUnconventionalOutcomes } = require('./crainee-unconventional-outcome-engine');
const result = generateUnconventionalOutcomes({
  seed: 'fixture-2026-10-25-experiment-01',
  homeTeam: 'Home FC',
  awayTeam: 'Away FC',
  mainModelScore: { home: 2, away: 1 },
  conventionalShortlist: [{ home: 2, away: 1 }, { home: 1, away: 1 }],
  candidateCount: 12,
  maxGoals: 5
});
```

Candidates are exploratory possibilities, not probability estimates or betting recommendations. Randomness increases scenario coverage but does not itself make a forecast more accurate. Improvement must be measured on chronological, untouched fixtures against the existing model and simple baselines.
