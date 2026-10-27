# Optional Gemini research adapter

This is an additive research helper, not a prediction engine and not a market-qualification authority.

## Configuration
- Set `GEMINI_API_KEY` as a private environment secret on the server. Never place it in source code, client-side JavaScript, logs, commits, or chat.
- Optional `GEMINI_MODEL` defaults to `gemini-2.5-flash`; confirm model access and account limits before enabling it.
- The adapter does not fetch source material itself. It only structures supplied source records. Callers must collect real source URLs, timestamps, and content first.
- The response is labelled `RESEARCH_LEADS` and `verified: false`; claims must be checked against their cited source before they can influence the model or qualification gates.
- Missing source material or missing credentials returns `NEEDS_DATA`; it does not fabricate lineup, injury, referee, weather, event, or probability data.

## Blacklist helper
`evaluate_market_blacklist` checks the home and away team against the operations store for the requested market and competition. A market-specific exclusion does not automatically exclude other markets. A survivor from this helper still has to pass the independent filtering prompt, validated rule, freshness, and data-completeness gates.

## Tests
Run:
```sh
python -m unittest tests.test_ufi_operations_brain tests.test_ufi_gemini_research -v
```

## Not yet claimed
This module is not yet wired into the production fixture/research pipeline, the 21:00 WAT worker, or a durable overnight queue. Do not claim unattended Gemini research until those integrations, persistent storage, source coverage, CI, and a production smoke test have all passed.
