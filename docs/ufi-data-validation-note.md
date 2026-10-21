# UFI dataset reconnaissance and validation note

## Source inspected

- Provider repository: https://github.com/hudl/open-data
- File: data/matches/9/281.json
- Competition: 1. Bundesliga, season 2023/2024
- Git blob SHA observed during inspection: 7f89072f44a97b537df4d31d181319901f482ed0

## Validation result

A read-only validation pass checked the 34 match records returned by that file:
- 34 records received
- 34 had date, home team, away team and non-negative integer final scores
- 0 malformed/missing-field records
- 0 exact duplicate rows under date + teams + final score
- Date range: 2023-08-19 through 2024-05-18

Example rows included Bayer Leverkusen 3-2 RB Leipzig (2023-08-19) and Borussia Mönchengladbach 0-3 Bayer Leverkusen (2023-08-26).

## Interpretation

This is a valid small sample for validating parsing and pipeline behaviour, **not a complete league-season dataset** and not enough to support a strong season-level training/validation/test claim. StatsBomb Open Data covers selected matches/competitions. Do not infer missing fixtures or treat coverage as complete.

The data was not copied into this repository. The app's opt-in downloader lets the user retrieve selected source data locally, records a manifest, and reminds the user to follow current provider terms and attribution requirements.

## Next dataset step

Use a broader results source only after checking its current terms permit the intended AI/model-training use. Some freely downloadable football results sites explicitly limit use to private individuals and exclude commercial data-training products or automated AI/scraping use. A public CSV is not automatically licensed for every research or commercial purpose.

For real contest ownership, source historical entries from the relevant contest platform or a properly licensed provider. Match results cannot substitute for actual DFS lineup ownership.
