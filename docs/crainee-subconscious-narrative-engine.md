# Crainee Subconscious Neural Databank & Fan Narrative Engine

This is an additive module; it does not replace existing engines.

Pipeline:
1. Positional sampler evaluates units 0–5400 every 180 units (31 samples), comparing identical height, composure, foot-skill and style-fit inputs across home/away DEFENSE, MIDFIELD and ATTACK.
2. Reality Supervisor applies the requested favorite (2:1) or underdog (1:1) baseline vector, score caps and scoreline/zone deduplication.
3. Fan Narrative Matcher adds conditional narrative hypotheses from missing-player names, weather and referee-disruption inputs and ranks candidates with the existing friction/context heuristic.
4. Full pipeline returns raw candidates, filtered candidates, ranked candidates, a short list and caveats.

Browser global: window.CraineeSubconsciousNarrativeEngine
Node module: require('./crainee-subconscious-narrative-engine.js')

Limitations: the grid is a simplified sample, not tracking data; the loop is not a microsecond simulator; no neural network, fan-sentiment corpus or automatic live feed is fabricated. Fan narrative is descriptive context, not predictive evidence. Quality scores are heuristic rankings, not probabilities. Validate chronologically held-out fixtures against baselines before making predictive claims.

 
## Subconscious pattern bank and fan-reaction ranking (v2)
- Fan-reaction candidates are generated per candidate scoreline for both fan bases, including tight-game/missed-chance draw reactions, dominance, referee complaints, defensive errors, finishing, missing starters, weather, streaks, coach pressure and caller-supplied narratives.
- The best matching reaction materially contributes to the ranking score. This is a deliberate candidate-ranking heuristic, not a calibrated probability.
- `calculateCrossDomainSignals` accepts numeric sequences from other domains and extracts momentum, normalized volatility, mean-reversion distance and a generic pattern signal. These features can be supplied as extra context, but their relevance to football is unproven until tested on chronological holdout matches; unrelated numbers are not magically predictive.
- The UI exposes a 5,400-unit clock advancing 180 units every 3 seconds. One sweep takes 90 wall-clock seconds; the display is a simulation clock, not live match time or actual microsecond computation.
- Missing players, weather, referee disruption, defensive-error signal, tactical-shift signal, team names/streaks and optional custom fan narratives are supported as caller-provided context. This does not automatically fetch those facts.
