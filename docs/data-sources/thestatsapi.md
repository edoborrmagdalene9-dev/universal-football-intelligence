# TheStatsAPI integration for UFI

Official site: https://www.thestatsapi.com/  
API docs: https://www.thestatsapi.com/docs  
Quickstart: https://www.thestatsapi.com/docs/quickstart  
Authentication: https://www.thestatsapi.com/docs/authentication  
Pagination: https://www.thestatsapi.com/docs/concepts/pagination

## Why this provider

The provider advertises fixtures/results, team and player data, match stats/events, xG, lineups, heatmaps, and odds across 150 competitions by default, with more available on request. Coverage varies by competition and season. Its website currently advertises a 7-day free trial and a Starter plan at $50/month; check current terms/pricing before starting. Sources: official pages linked above.

## Local downloader

`tools/thestatsapi_download.py` uses Python's standard library only. It downloads finished matches for a selected competition/season or a limited number of competitions, following the API's documented pagination format.

1. Create an account and API key via the provider's dashboard.
2. Set the key as an environment variable. Never paste it into source code or commit it:
   - Windows PowerShell (current terminal): `$env:THESTATSAPI_API_KEY="YOUR_KEY"`
   - macOS/Linux: `export THESTATSAPI_API_KEY="YOUR_KEY"`
3. Start with a single competition:
   `python tools/thestatsapi_download.py --search "Premier League"`
4. For a known competition ID and season ID:
   `python tools/thestatsapi_download.py --competition-id comp_3039 --season-id sn_8406098`
5. Only after checking your plan/quota, expand scope:
   `python tools/thestatsapi_download.py --all-competitions --max-competitions 5`

The output defaults to `data/private/thestatsapi/`, which is git-ignored. This avoids accidentally committing an API key or bulk provider data to the public UFI repo. Don't use `--all-competitions` without a scope/usage plan: every paginated request counts against API quotas, and "all seasons, all leagues" may require many requests.

## Important limitations

- The API key is not included in the repo; a user must create it.
- No API data has been downloaded or validated in this commit. The provider requires an authenticated key.
- This client fetches competition metadata and finished match records. It does not yet fetch odds, lineups, xG/event detail, player stats, or tracking data; those need dedicated endpoint adapters and validation.
- Match records are not tracking feeds. Do not infer exact sprint speeds, hip orientation, jump heights, or full ball trajectories unless a supported data source provides them.
- Keep data provenance, retrieval timestamps, missing values and original IDs. Verify licensing/retention/redistribution rights before publishing downloaded records.
