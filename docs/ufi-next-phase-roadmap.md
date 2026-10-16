# UFI next-phase roadmap: from results to football intelligence

This roadmap keeps UFI grounded in observable football evidence. It does not treat missing player facts as known, and it separates match-result forecasting from player/tactical research.

## Phase 1 — trustworthy historical foundation

- Download permitted public-domain fixtures/results through the OpenFootball workflow.
- Validate required columns, scored-match coverage, manifest row counts, and source provenance.
- Run regression tests before data ingestion.
- Forecast all fixtures on the same calendar date before adding any results from that date to training history.
- Compare the team-goal model with a simple rolling league-outcome baseline.
- Report accuracy, multiclass Brier score, log loss, sample count, skipped rows, and per-league metrics.
- Keep each prediction row so errors can be investigated, not just hidden in a single score.

## Phase 2 — richer match and team features

Add features only when their source and timestamp are known:
- rolling goals for/against, home/away splits, opponent strength, and rest days;
- recent form with decay, while avoiding double-counting overlapping windows;
- red cards and match events only from sources that provide them;
- odds snapshots only from a source whose terms permit this use, with capture timestamps;
- lineup and injury availability only where the source provides reliable records.

Every feature must be computed as it would have been known before kickoff. Missing information remains missing; it must not be silently filled with a guessed value.

## Phase 3 — player intelligence registry

Maintain one player record per stable source ID where available, with:
- player name, team, competition, season, and source identifiers;
- preferred foot, weak-foot evidence, role, and observed play-style labels;
- minutes, starts/substitute appearances, and the match window supporting each observation;
- source URL, observation date, confidence, and evidence notes;
- a distinction between directly sourced facts, analyst observations, and model-derived estimates.

eFootball labels such as “Fox in the Box” or “Orchestrator” are game-specific classifications. Store them as a separate tag set rather than asserting that a real player objectively has the same official label. A dominant foot or style should not be inferred from one clip or a small sample.

## Phase 4 — substitutes and tactical context

For every substitution, record minute, score at the time, outgoing/incoming player, role, and available event evidence. Evaluate impact against comparable match states and minutes, controlling for scoreline, opponent, red cards, and selection bias. A player entering when the team is already losing should not automatically be blamed for the result.

## Phase 5 — evaluation before betting use

- Keep chronological holdouts by season; never tune on the final test period.
- Compare probabilities against simple baselines and, when lawfully available, timestamped bookmaker odds.
- Evaluate calibration and log loss/Brier score, not accuracy alone.
- Report sample sizes and uncertainty; break results down by league and season.
- Track closing-line comparisons or returns only when odds and settlement rules are complete and independently verified.
- Never call a model profitable from historical accuracy alone; paper-test new versions before risking money.

## Current limits

OpenFootball results do not provide player footedness, lineups, injuries, bookmaker odds, event sequences, or continuous player tracking. Those require separate data sources and permissions. The current Poisson baseline is a first benchmark, not a complete football simulator or an automated sure-bet engine.
