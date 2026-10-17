# UFI Model Brain — research-grounded operating rules

Purpose: a traceable research guide for Universal Football Intelligence (UFI). This file is not a claim that all sources were fully accessible or that the app already implements every method. It separates established mechanics from features requiring data and validation.

## Operating doctrine

1. Evidence provenance first. Every input must be labelled public source, user-entered note, computed output, model estimate, or unknown. Record data timestamps, source URLs, market definitions and exact fixture ID. OCR text is provisional until checked.
2. Model before narrative. An LLM may summarize, challenge assumptions and list what to verify. It must not invent odds, lineups, injuries, player foot preference, weather, tracking coordinates, xG or probabilities. Its answer cannot turn HOLD into a cleared bet.
3. Fit and test. Fit attack/defence strengths on historical scorelines with time decay; compare independent Poisson, Dixon-Coles and simple league/home-away baselines. Test on later unseen matches. Track log loss, multiclass Brier, ranked probability score, calibration and performance by league/market. Do not optimize on the same test period used to report performance.
4. Probability and price. Decimal odds imply 1/odds before overround correction. For an exact market only, EV per unit stake is p*odds - 1. If p is uncalibrated, odds missing, settlement unclear, or market differs, EV is not established. Account for dependence in accumulators; multiplying leg probabilities assumes independence and is often wrong.
5. Physics is a conditional layer, not magic. Drag, Reynolds number, surface roughness, spin and Magnus effects affect a ball's trajectory. They do not directly determine match results. A useful shot-level physics model needs measured launch speed/angle/spin, ball properties, wind and trajectory/shot context plus outcome data. Without this, do not add a made-up physics score.
6. Spatial and biomechanical layer. Pitch control needs time-stamped player and ball coordinates, velocities, acceleration/reaction assumptions and team context. Event coordinates are sparse event locations, not full optical tracking. Dominant/weak foot, height/weight, style and substitute impact must be source-backed and time-relevant; missing data stays unknown.
7. Context and news. Recent form must be opponent-adjusted and split by venue with adequate sample size. Injuries/suspensions/lineups need recent reliable reports; search headlines (including GDELT) are leads, not confirmation. Schedule congestion and motivation should be explicit hypotheses, not guessed narrative.
8. Risk gate. Hard-stop only for verifiable contradictions (e.g. wrong/settled/historical fixture, invalid odds or impossible input). Unknown evidence, model disagreement, stale prices or unverified news should generally HOLD. “No red flag found” does not mean safe.
9. Replacement discipline. Replacement picks require a current fixture, exact market/settlement, verified price, model estimate for that market, independent baseline comparison and calibrated out-of-sample evidence. Otherwise show “NO QUALIFIED REPLACEMENT”; never fill a 3-leg ticket just to satisfy a format.
10. Bankroll. Kelly is a stake-sizing rule, not a match predictor. Use only after a robust positive edge is demonstrated; estimation error, correlated legs and bookmaker limits argue for conservative fractional sizing. Never present a staking formula as a way to guarantee profit.

## Source review register

The 24 URLs supplied by the project owner are preserved below. Pages and papers were opened where available on 2026-10-17; some links returned an internal error or maintenance page. Those entries remain references, not claims that their contents were fully reviewed. Prefer original academic papers and official bookmaker terms over SEO summaries.

### Fluid mechanics and ball aerodynamics
1. J. W. M. Bush, MIT, The Aerodynamics of the Beautiful Game — https://thales.mit.edu/bush/wp-content/uploads/2013/11/Beautiful-Game-2013.pdf
2. A. M. Nathan, On the Flight of the American Football (sports-ball comparison, not soccer-specific betting evidence) — https://arxiv.org/html/0706.0366v1
3. The Magnus Effect and the American Football — https://www.usna.edu/MNEDept/_files/documents/brownell_files/JSE%2016.pdf
4. Goff & Chin, Bifurcation and Chaos in Trajectories of Knuckleballs and Smooth Spheres — https://arxiv.org/pdf/1710.02784
5. Asai et al., The Aerodynamics of Soccer Balls — https://arxiv.org/pdf/nlin/0611033
6. FlowThermoLab, Magnus Effect on a Rotating Soccer Ball — https://www.flowthermolab.com/magnus-effect-on-a-rotating-soccer-ball/
7. ResearchGate, An Exploration of Magnus Effect Role in Sports, Especially in Football — https://www.researchgate.net/publication/383192218_An_exploration_of_Magnus_effect_role_in_sports_especially_in_football

### Quantitative predictive modelling
8. GoalIQ, Dixon-Coles overview — https://www.goaliqai.com/dixon-coles-model-football-predictions/
9. Dashee87, Predicting Football Results with Statistical Modelling: Dixon-Coles and Time-Weighting — https://dashee87.github.io/football/python/predicting-football-results-with-statistical-modelling-dixon-coles-and-time-weighting/
10. Football Bet Prediction, Dixon-Coles overview — https://football-bet-prediction.com/articles/dixoncoles-model-explained-improving-poisson/
11. ResearchGate, An Exploration of Predictive Football Modelling — https://www.researchgate.net/publication/338028907_an_exploration_of_predictive_football_modelling
12. Prediction Engine, Dixon-Coles guide (page showed maintenance) — https://predictionengine.app/learn/dixon-coles-soccer-model
13. Opisthokonta, Dixon-Coles model implementation — https://opisthokonta.net/?p=939
14. Karlis et al., Extending the Dixon and Coles Model: An Application to Women's Football Data — https://arxiv.org/pdf/2307.02139

### Spatial analytics and pitch control
15. Haziq J., pitch-control research proposal — https://haziqj.ml/teaching/fyp/research_proposals/18b9001.pdf
16. Tony ElHabr, Creating a Soccer Pitch Control Model in R — https://tonyelhabr.rbind.io/posts/soccer-pitch-control-r/

### Financial risk and bookmaker terms
17. Bettor Results, fractional Kelly guide — https://www.bettorresults.com/blog/kelly-criterion-bet-sizing-guide
18. SmartMatchPick, Kelly criterion in football — https://smartmatchpick.com/guides/kelly-criterion-football
19. BetCompare, Bet9ja multi-bonus review — https://betcompare.ng/sports-betting-insights/bet9ja-multi-bonus-accumulator-bonus-review
20. BetCompare, SportyBet multiple-bet bonus guide — https://betcompare.ng/sports-betting-insights/sportybet-multiple-bet-bonus-full-terms-how-it-works-worked-example-2026
21. Bet9ja Promotion Code portal, bonus terms — https://bet9japromotioncode.ng/bet9ja-bonus-terms
22. SportyBet Nigeria, bonuses and gifts help — https://www.sportybet.com/ng/m/help/how-to-play/others/bonuses-and-gifts
23. SportyBet Tanzania, bonuses and gifts help — https://www.sportybet.com/tz/m/help/how-to-play/others/bonuses-and-gifts
24. Bet9ja shop terms — https://shop.bet9ja.com/pages/sportfooter_terms/content

## Model implementation roadmap

- Added to the web UI: multi-provider AI evidence challenge; up to three providers called concurrently; configured fourth provider is sequential fallback; results remain advisory and are attached to the current risk-audit export.
- Not solved by adding LLMs: verified SportyBet live odds, official lineups/injury feed, complete event/tracking coverage, calibrated fixture-specific replacement predictions, or evidence that the model beats bookmaker prices after margin.
- Next quantitative step: create a reproducible historical training/evaluation pipeline, fit league-specific Dixon-Coles and simple baselines, store model version and data cutoff, produce out-of-sample calibration, and only then let exact-market probabilities enter EV/risk gating.


## Additional primary/adjacent sources discovered while following the supplied references

25. Dixon & Coles (1997), original peer-reviewed paper, *Modelling Association Football Scores and Inefficiencies in the Football Betting Market*, Journal of the Royal Statistical Society Series C, DOI 10.1111/1467-9876.00065 — https://rss.onlinelibrary.wiley.com/doi/abs/10.1111/1467-9876.00065. This is the canonical source for the score model and historical market evaluation; its old-period reported returns are not evidence of current profitability.
26. Hudl StatsBomb Open Data official README — https://github.com/hudl/open-data/blob/master/README.md. Documents the free-data repository's competitions, matches, events, lineups, selected 360 data, and attribution expectations. The open dataset is selected coverage, not a universal live feed.
27. Kovalchik (2023), *Player Tracking Data in Sports*, Annual Review of Statistics and Its Application — https://doi.org/10.1146/annurev-statistics-033021-110117. Reviews high-resolution spatiotemporal tracking and analytics methods, with data/method limitations; supports the rule that player-level spatial claims require actual tracking data.
