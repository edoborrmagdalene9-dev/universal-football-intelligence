# OpenFootball: free historical fixtures and results

Source: https://github.com/openfootball/football.json  
License: the upstream project dedicates its data and schema to the public domain; verify the current upstream `LICENSE.md` before redistributing a derived dataset.

## Why UFI uses it

OpenFootball provides season JSON files with match dates, home/away teams, fixtures and full-time scores where available. It needs no API key and is a useful base for historical form, scoreline frequencies, Elo/form features and chronological backtests.

It does **not** provide bookmaker odds, reliable player weak-foot labels, full player tracking or comprehensive event-level data. UFI combines it with separately licensed event data such as StatsBomb Open Data where appropriate.

## Download locally

From the repository root, with Python 3 installed and internet access:

```bash
python tools/openfootball_download.py
```

By default, this checks seasons from 2010/11 through 2026/27 across the league codes listed in the script. It saves raw JSON, a normalized `matches.csv`, and a provenance manifest under `data/private/openfootball/`. The output is git-ignored and is not uploaded to the public repository.

To start with only Premier League seasons:

```bash
python tools/openfootball_download.py --leagues en.1 --start-year 2010 --end-year 2025
```

To download a smaller test first:

```bash
python tools/openfootball_download.py --leagues en.1,de.1 --start-year 2022 --end-year 2023
```

The script skips missing season files (HTTP 404), logs other source/network errors, and records which source URL each row came from. Always inspect the manifest and missing values before modelling. It is a downloader for public-domain results—not a source for odds or tracking data.
