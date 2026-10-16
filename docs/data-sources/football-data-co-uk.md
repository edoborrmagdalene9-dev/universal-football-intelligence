# Football-Data.co.uk source assessment for UFI

Source: https://football-data.co.uk/data  
Download index: https://football-data.co.uk/downloadm.php  
Reviewed: 2026-10-16

## Why this source matters

Football-Data.co.uk publishes historical match-level results, bookmaker odds and, for many competitions/seasons, basic match statistics in CSV/Excel form. Its published coverage includes the main English, Scottish, German, Italian, Spanish, French, Dutch, Belgian, Portuguese, Turkish and Greek divisions, plus extra leagues including Argentina, Austria, Brazil, China, Denmark, Finland, Ireland, Japan, Mexico, Norway, Poland, Romania, Russia, Sweden, Switzerland and the USA. Coverage differs by league and season.

Useful fields can include:
- Match date, home/away teams, full-time and half-time goals/results
- Bookmaker 1X2 odds and, where available, totals and Asian-handicap odds
- Shots, shots on target, corners, fouls, cards and referee fields in supported files/seasons
- Opening/pre-closing and closing odds in some seasons; coverage and column names vary

This is valuable for historical baselines, market comparison, scoreline modelling and chronological backtesting. It is **not** player-tracking data: it does not provide continuous player coordinates, exact sprint speeds, hip orientation, jump height, or complete ball trajectories.

## Important source-use restriction

The source's own data page states that the free spreadsheet data is intended for private individuals and not for commercial or data-training products using automated bots, scrapers or AI. UFI is an AI-assisted project, so do not bulk-download, scrape, train on, redistribute, or commit the source files to this public repository unless the source owner confirms that the intended use is permitted.

The public UFI repository must not contain copied bulk datasets from this source. The source links can be documented, and UFI can support data obtained under appropriate permission or terms. Contact Football-Data.co.uk to ask about permission/licensing for an AI-assisted, personal research/backtesting workflow before automating ingestion or model training.

## Integration requirements once permission is confirmed

1. Keep original files unchanged in a local, non-public data directory; do not commit them to Git.
2. Record source URL, retrieval date, league code, season, original filename and file hash in a manifest.
3. Treat each season/league as schema-variable. Never assume every file has the same columns.
4. Parse dates with explicit day/month handling and retain the original date value for audit.
5. Preserve missing values as missing; never fill absent shots, odds, referee or statistics with zero.
6. Keep bookmaker opening/pre-closing odds distinct from closing odds. Never use closing odds as a feature for a prediction that is meant to be made earlier.
7. Standardise team names with a documented alias table while retaining the original source name.
8. Validate duplicates, impossible scores, invalid odds and match-date/team mismatches before use.
9. Use chronological walk-forward evaluation; every feature must be available at the forecast timestamp. Fit transformations only on training data.
10. Report league/season coverage, missingness and source limitations in every evaluation.

## Suggested canonical match schema

- `source`, `source_url`, `retrieved_at`, `file_hash`
- `country`, `league_code`, `league_name`, `season`
- `match_date`, `kickoff_time`, `home_team_raw`, `away_team_raw`
- `home_goals_ft`, `away_goals_ft`, `full_time_result`
- `home_goals_ht`, `away_goals_ht`, `half_time_result`
- `home_shots`, `away_shots`, `home_shots_on_target`, `away_shots_on_target`
- `home_corners`, `away_corners`, `home_fouls`, `away_fouls`
- `home_yellows`, `away_yellows`, `home_reds`, `away_reds`, `referee`
- Separate columns for each odds provider and market, preserving source column names and whether odds are opening/pre-closing or closing.

Every field is optional by source/season and must carry missingness metadata. This schema is a target design, not a claim that every field exists in every file.

## Current implementation status

This document records source assessment and a safe integration plan only. No Football-Data.co.uk dataset has been copied into the UFI repository, and no downloader/scraper has been added. Ingestion and model training are blocked pending confirmation of permitted use.
