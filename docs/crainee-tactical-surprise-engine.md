# Crainee Tactical Surprise Engine

Additive browser/CommonJS module: `crainee-tactical-surprise-engine.js`. It exposes three component evaluators and a combined evaluator, and injects a new Tactical Surprise page into the existing UFI UI without rewriting existing modules.

## Components
- **Spatial grid:** one-dimensional 0–5400 ball coordinate, zone-based rating mismatch and spatial stretch.
- **Tactical edge:** defensive-line height × transition speed, winger/fullback mismatch, time progression and fatigue/substitute inputs.
- **Style friction:** explicitly labelled player-style matchup signals and a nonlinear interaction with grid position.
- **Combined report:** shows each subscore, flags and limitations; it does not convert them to probabilities.

## Important corrections versus the supplied draft
- Values are validated and bounded; zero is not silently replaced by JavaScript's `||` defaults.
- Original spatial midpoint and zone logic are retained in spirit, but the style engine uses a consistent exported namespace and handles missing teams safely.
- The supplied draft's “confidence” percentages and “Bookie margin bypassed” claim were removed. These are heuristic scores without calibration evidence, not exploit probabilities or a guaranteed shock prediction.
- Time/fatigue growth is restrained, and all output is explicitly labelled as an experimental signal.

## Inputs and data limitations
The UI uses user-entered ratings and example JSON; it does not connect a live player-tracking, lineup, fatigue, or event provider. 0–5400 is a conceptual coordinate, not a physical pitch model or player tracking stream. Defaults are illustrative and must be replaced by sourced observations.

## Validation
Run `node --test tests/crainee-tactical-surprise-engine.test.cjs`. Tests cover all three components, invalid ranges, asymmetric styles, and combined output. This does not establish predictive lift. Before treating the engine as predictive, evaluate chronologically on historical matches using only pre-match information for pre-match forecasts, compare with existing baselines, and report calibration and exact-score log loss/Brier score where applicable.
