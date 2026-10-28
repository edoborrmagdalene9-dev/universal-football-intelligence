# Crainee Temporal, Squad & Referee Chaos Gate

This is an experimental contextual-risk heuristic that can be used alongside the 5400 Bookie-Edge Gate. It does not establish a positive betting edge and is not a calibrated probability model.

## Formula
For each player, the squad asset contribution is:

`marketValue × exp(-0.015 × (age - 27)^2) × log10(caps + 10)`

Missing player fields use the user's example defaults (market value 1,000,000; age 26; caps 30) and the UI reports them. Team contributions are summed. Squad power is `clamp(log10(homeScore + awayScore + 1) / 15, 0, 1)`.

The referee flow factor is `min(1.2, activeAverageWhistleGap / 100)`, selecting the first-half or second-half supplied gap by elapsed time. Time weight is `clamp(currentSecond, 0, 5400) / 5400`. Composite score is `squadPower × refereeFlowFactor × (1 + timeWeight)`. A score below 0.25 is discarded.

For an eligible score, the maximum stake cap is `min(5%, 5% × compositeScore)` of the entered bankroll. This is a mechanical cap, not advice to stake that amount; a zero bankroll yields zero. No forced minimum stake is used.

## Limitations and required validation
- Market value, age and caps do not by themselves model availability, playing time, position, form, tactics, or causal match outcomes.
- Average time between whistles is a weak proxy for referee style; historical distributions and match-specific events are preferable.
- The time multiplier increases the composite score with elapsed time by construction. It does not prove growing forecast accuracy.
- Do not treat a high score as an expected-value edge. Combine only with independently calibrated outcome probabilities and same-market, de-vigged prices.
- The interface uses user-supplied squad and referee data; it is not connected to a live provider automatically.
- The gate cannot guarantee profit. Test chronologically on unseen matches and compare with baselines before relying on it.
