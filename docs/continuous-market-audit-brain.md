# Continuous market-audit brain (additive)

POST /api/audit/slip accepts a JSON object containing survival_threshold and fixtures. Each fixture requires home, away and selections; optional evidence includes home_xg, away_xg, lineups_confirmed, key_creator_available, data_age_minutes, passive_build_up, high_transition_rate, attacker_goal_share and goal_contributors.

Every fixture is evaluated concurrently in an isolated pocket. Deterministic faults retain source-field provenance. Hard mutex conflicts require explicit structured state assertions. Passive build-up and transition threat are retained together because counters, direct play and set pieces can make them coexist.

Probabilities use an explicit market_probability or an independent-Poisson score matrix from supplied xG. Supported markets: goal totals 1.5/2.5/3.5, BTTS, double chance, 1X2 and team multigoals 1-3. Each selection returns KEEP, DITCH or NEEDS_DATA. Default survival threshold is 55%. Unsupported markets are never cleared.

Redis is used when REDIS_URL and redis-py are configured. Otherwise SQLite is used as a fallback; on Render Free without a persistent disk, /tmp storage is ephemeral. A managed Redis or PostgreSQL resource is required for durable shared pockets and a true continuously running worker.

Limitations: xG probabilities are baseline Poisson estimates, not calibrated player/tactical forecasts. Player goal-origin data is descriptive only until time-aligned backtesting validates it. Odds are compared with raw break-even probability, not de-vigged market probability. No bet placement or automatic stake escalation occurs.
