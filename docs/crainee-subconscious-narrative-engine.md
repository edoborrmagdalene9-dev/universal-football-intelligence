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
