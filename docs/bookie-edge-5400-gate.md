# 5400 Bookie-Edge Gate

## Purpose
The gate screens candidate markets for conservative expected value and data quality. It does not infer bookmaker intent from a suspended market or price movement, and it cannot guarantee a winning selection.

## 5400 rule
A standard 90-minute match contains 5,400 seconds. The interface maps elapsed match minutes to at most 5,400 elapsed checkpoints. It reevaluates when the user or live-data pipeline supplies fresh inputs; it does not manufacture 5,400 independent observations from repeated values, and it cannot certify future checkpoints that have not occurred. A selection only passes the current evaluation when all configured hard filters pass.

## Candidate JSON
Each candidate requires:
- `selection`
- `odds`: decimal odds > 1
- `modelProbability`: estimated probability from 0 to 1, strictly between endpoints
- `marketProbability`: de-vigged market probability from 0 to 1
- `uncertainty`: uncertainty estimate in probability units (0 to 1)
- `sourceUpdatedAt`: source-side ISO timestamp, not just browser capture time
- `validationMatches`: number of independent out-of-sample validation matches
- `snapshots`: distinct timestamped market snapshots

The current conservative lower probability is `max(0, modelProbability - 1.645 × uncertainty)`. Conservative EV is `lowerProbability × decimalOdds - 1`. Conservative edge is `lowerProbability - marketProbability`. The selection is discarded when source data is stale/future-dated, fields are invalid, validation/snapshot counts are too small, uncertainty exceeds the limit, probability is below the floor, conservative EV is below the threshold, or conservative edge is too small.

This lower-bound calculation is a heuristic screening rule, not a statistically calibrated confidence interval unless the uncertainty input is calibrated accordingly. Configure marketProbability from a correctly de-vigged market for the same outcome/market; don't compare a score probability with a 1X2 probability.

## Limitations
- No provider API is assumed to be connected to this gate automatically.
- It is a screening UI and doesn't place bets.
- A bookmaker may suspend markets for many operational or risk reasons; suspension is not proof of a trap.
- Odds and probabilities are uncertain; even a candidate passing the gate can lose.
- Thresholds must be tuned and evaluated on chronological unseen data. Do not use the feature as proof of profit or as a guarantee.

