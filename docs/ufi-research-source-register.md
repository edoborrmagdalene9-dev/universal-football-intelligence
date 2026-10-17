# UFI research source register

This register links the supplied research list to the project's implementation decisions. It is a curated reading map, not a claim that every source has been fully read or independently peer-reviewed. Primary academic work and official dataset/operator documentation take precedence over secondary explainers and promotional blogs.

## A. Football aerodynamics and mechanics
1. John W. M. Bush, [The Aerodynamics of the Beautiful Game (2013)](https://thales.mit.edu/bush/wp-content/uploads/2013/11/Beautiful-Game-2013.pdf) — MIT mathematics author manuscript on drag, spin/Magnus effects, surface roughness and trajectories. Relevant to ball-flight physics, not direct match-result prediction. Related institutional record: [MIT DSpace](https://dspace.mit.edu/entities/publication/2e973612-e01f-4857-a455-983b1150f82b).
2. A. M. Nathan, [On the Flight of the American Football](https://arxiv.org/html/0706.0366v1) — comparative projectile mechanics; American football differs from soccer, so parameters cannot be transferred uncritically.
3. [The Magnus Effect and the American Football](https://www.usna.edu/MNEDept/_files/documents/brownell_files/JSE%2016.pdf) — comparative sports-ball aerodynamics.
4. Goff et al., [An Aerodynamic Analysis of Recent FIFA World Cup Balls](https://arxiv.org/pdf/1710.02784) — ball design/aerodynamics; needs appropriate measured conditions.
5. Asai et al., [The Aerodynamics of Soccer Balls](https://arxiv.org/pdf/nlin/0611033) — soccer-specific aerodynamics.
6. Flow Thermo Lab, [Magnus Effect on a Rotating Soccer Ball](https://www.flowthermolab.com/magnus-effect-on-a-rotating-soccer-ball/) — secondary explainer; verify against primary work.
7. ResearchGate, [Magnus effect role in sports especially football](https://www.researchgate.net/publication/383192218_An_exploration_of_Magnus_effect_role_in_sports_especially_in_football) — repository copy; verify publication metadata/methods.
8. Related work: Paudel & Yan, [High-fidelity full-flight soccer ball aerodynamics (published 2025)](https://link.springer.com/article/10.1007/s00466-025-02705-2); Alam et al., [Effects of surface structure on soccer ball aerodynamics](https://www.sciencedirect.com/science/article/pii/S1877705812016396); [MIT News: How does a soccer ball swerve?](https://news.mit.edu/2014/explained-how-does-a-soccer-ball-swerve-0617).

**Implementation limit:** the current app lacks measured spin, launch velocity, continuous ball trajectory, wind, humidity, turf friction and full tracking coordinates. These papers inform future physics experiments; do not fabricate those inputs from final scores or event locations.

## B. Statistical prediction
9. Dixon & Coles (1997), [Modelling Association Football Scores and Inefficiencies in the Football Betting Market](https://doi.org/10.1111/1467-9876.00065) — primary reference for score dependence and market analysis.
10. Dashee87, [Dixon-Coles and time weighting](https://dashee87.github.io/football/python/predicting-football-results-with-statistical-modelling-dixon-coles-and-time-weighting/) — educational implementation; audit assumptions and leakage controls.
11. GoalIQ, [Dixon-Coles explainer](https://www.goaliqai.com/dixon-coles-model-football-predictions/) — secondary explainer, not evidence of profit.
12. Football Bet Prediction, [Dixon-Coles model explanation](https://football-bet-prediction.com/articles/dixoncoles-model-explained-improving-poisson/) — secondary explainer; cross-check formulas.
13. ResearchGate, [An Exploration of Predictive Football Modelling](https://www.researchgate.net/publication/338028907_An_exploration_of_predictive_football_modelling) — inspect full text, sample, baselines and leakage handling.
14. Prediction Engine, [Dixon-Coles implementation guide](https://predictionengine.app/learn/dixon-coles-soccer-model) — secondary learning source.
15. Opisthokonta, [Statistical soccer scoring models and identifiability constraints](https://opisthokonta.net/?p=939) — practical team parameter discussion.
16. Karlis et al., [Extending Dixon-Coles to women's football](https://arxiv.org/pdf/2307.02139) — research extension; population transfer requires testing.

**Implementation rule:** compare Elo, Poisson and fitted Dixon-Coles chronologically; report Brier/log loss/calibration and compare with no-vig market probabilities. Complexity is not evidence of superiority.

## C. Spatial analytics and pitch control
17. Haziq J., [Pitch-control research proposal](https://haziqj.ml/teaching/fyp/research_proposals/18b9001.pdf) — proposal/learning resource; verify cited methods.
18. Tony ElHabr, [Soccer pitch control in R](https://tonyelhabr.rbind.io/posts/soccer-pitch-control-r/) — secondary implementation.
19. William Spearman, [Quantifying Pitch Control](https://www.researchgate.net/publication/334849056_Quantifying_Pitch_Control) — requires spatiotemporal player tracking.
20. [Scientific Reports pitch-control and stamina research (2025)](https://www.nature.com/articles/s41598-025-22778-6) — position, speed, acceleration and stamina as inputs.

**Implementation rule:** StatsBomb event coordinates are event locations, not continuous 25 Hz player tracking. Pitch control remains unavailable without legitimate tracking data.

## D. Betting prices, bankroll risk and promotions
21. Bettor Results, [Kelly Criterion guide](https://www.bettorresults.com/blog/kelly-criterion-bet-sizing-guide) — secondary risk-management explainer; sizing is highly sensitive to probability error.
22. SmartMatchPick, [Kelly Criterion in football betting](https://smartmatchpick.com/guides/kelly-criterion-football) — secondary explainer; verify assumptions.
23. BetCompare, [Bet9ja multi-bonus review](https://betcompare.ng/sports-betting-insights/bet9ja-multi-bonus-accumulator-bonus-review) — secondary, time-sensitive promotion information.
24. BetCompare, [SportyBet multiple-bet bonus terms](https://betcompare.ng/sports-betting-insights/sportybet-multiple-bet-bonus-full-terms-how-it-works-worked-example-2026) — secondary, time-sensitive.
25. Bet9ja Promotion Code portal, [Bonus terms](https://bet9japromotioncode.ng/bet9ja-bonus-terms) — third-party information; verify current operator terms.
26. SportyBet Nigeria, [Official bonuses and gifts help](https://www.sportybet.com/ng/m/help/how-to-play/others/bonuses-and-gifts) — operator source for its published terms.
27. SportyBet Tanzania, [Bonuses and gifts help](https://www.sportybet.com/tz/m/help/how-to-play/others/bonuses-and-gifts) — different jurisdiction; do not assume Nigerian terms match.
28. Bet9ja Shop, [Retail shop terms](https://shop.bet9ja.com/pages/sportfooter_terms/content) — check version and applicability.

**Implementation rule:** raw implied probability is 1/decimal odds; normalize complete markets for an initial no-vig comparison. A bonus changes payout terms, not match probability. Accumulator dependence and settlement rules matter.

## E. Dataset documentation and related primary sources
- [StatsBomb Open Data event specification](https://raw.githubusercontent.com/statsbomb/open-data/master/doc/StatsBomb%20Open%20Data%20Specification%20v1.1.pdf) — field definitions and event semantics.
- [MIT DSpace record for Bush's paper](https://dspace.mit.edu/entities/publication/2e973612-e01f-4857-a455-983b1150f82b) — institutional metadata.
- [Dixon-Coles DOI](https://doi.org/10.1111/1467-9876.00065) — primary statistical model reference.

## Research-to-code protocol
For every source-driven change, record the claim and page/section, source type, required inputs, data available in UFI, falsifiable hypothesis, baseline, chronological test and uncertainty. Link cataloguing is not equivalent to reading every paper in full. Different sports, jurisdictions and promotions are not interchangeable.

## Model experiments
1. Compare independent Poisson with fitted Dixon-Coles/time decay on held-out chronological fixtures.
2. Test no-vig market probabilities against model calibration, with pre-kickoff timestamps and permitted provenance.
3. Add player evidence only after stable player-match joins and verified minutes.
4. Prototype pitch control only with legitimate tracking data and compare against simpler spatial baselines.
5. Keep aerodynamics as a research layer until measured trajectory/spin/environment data exists.
6. Keep Kelly/stake sizing out of production decisions until probability calibration and edge uncertainty are defensible.
