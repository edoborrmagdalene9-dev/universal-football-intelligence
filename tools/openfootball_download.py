#!/usr/bin/env python3
"""Fetch public-domain OpenFootball JSON results and normalize them to CSV.

No API key or third-party Python packages required.
Source data: https://github.com/openfootball/football.json
The script downloads only public-domain fixture/result files and saves them locally;
it does not upload datasets to GitHub.
"""
from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://raw.githubusercontent.com/openfootball/football.json/master"
LEAGUES = {
    "en.1": "England Premier League",
    "en.2": "England Championship",
    "en.3": "England League One",
    "en.4": "England League Two",
    "de.1": "Germany Bundesliga",
    "de.2": "Germany 2. Bundesliga",
    "es.1": "Spain La Liga",
    "es.2": "Spain Segunda Division",
    "it.1": "Italy Serie A",
    "it.2": "Italy Serie B",
    "fr.1": "France Ligue 1",
    "fr.2": "France Ligue 2",
    "nl.1": "Netherlands Eredivisie",
    "pt.1": "Portugal Primeira Liga",
    "sco.1": "Scotland Premiership",
}
FIELDS = [
    "season", "league_code", "league_name", "date", "round",
    "home_team", "away_team", "home_goals", "away_goals", "status",
    "source_url",
]


def season_names(start_year: int, end_year: int):
    for year in range(start_year, end_year + 1):
        yield f"{year}-{str(year + 1)[-2:]}"


def get_json(url: str):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "UFI-openfootball-importer/1.0 (public-domain data research)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def goals(match, key):
    score = match.get("score") or {}
    value = score.get(key)
    if isinstance(value, list) and value:
        return value[0]
    if isinstance(value, (int, float, str)):
        return value
    return ""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-year", type=int, default=2010,
                        help="first season start year (default: 2010)")
    parser.add_argument("--end-year", type=int, default=2026,
                        help="last season start year (default: 2026)")
    parser.add_argument("--leagues", default=",".join(LEAGUES),
                        help="comma-separated league codes; default: all listed leagues")
    parser.add_argument("--out", default="data/private/openfootball",
                        help="local output directory (gitignored by this repository)")
    parser.add_argument("--delay", type=float, default=0.15,
                        help="polite pause between requests in seconds")
    args = parser.parse_args()

    selected = [code.strip() for code in args.leagues.split(",") if code.strip()]
    unknown = sorted(set(selected) - set(LEAGUES))
    if unknown:
        parser.error(f"unknown league code(s): {', '.join(unknown)}")
    if args.end_year < args.start_year:
        parser.error("--end-year must be >= --start-year")

    output = Path(args.out)
    raw_dir = output / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    files_found = 0
    requests_made = 0

    for season in season_names(args.start_year, args.end_year):
        for code in selected:
            url = f"{BASE}/{season}/{code}.json"
            requests_made += 1
            try:
                payload = get_json(url)
            except Exception as exc:
                print(f"[WARN] {url}: {exc}")
                continue
            if not payload:
                continue
            files_found += 1
            (raw_dir / f"{season}_{code}.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            for match in payload.get("matches", []):
                score = match.get("score") or {}
                has_ft = "ft" in score and isinstance(score.get("ft"), list) and len(score["ft"]) >= 2
                rows.append({
                    "season": season,
                    "league_code": code,
                    "league_name": LEAGUES[code],
                    "date": match.get("date", ""),
                    "round": match.get("round", ""),
                    "home_team": match.get("team1", ""),
                    "away_team": match.get("team2", ""),
                    "home_goals": goals(match, "ft")[0] if has_ft else "",
                    "away_goals": goals(match, "ft")[1] if has_ft else "",
                    "status": "finished" if has_ft else "scheduled_or_unscored",
                    "source_url": url,
                })
            print(f"[OK] {season} {code}: {len(payload.get('matches', []))} matches")
            time.sleep(max(0.0, args.delay))

    csv_path = output / "matches.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    manifest = {
        "source": "OpenFootball football.json",
        "source_url": "https://github.com/openfootball/football.json",
        "source_license": "Public domain (verify upstream LICENSE.md before redistribution)",
        "leagues_requested": selected,
        "start_year": args.start_year,
        "end_year": args.end_year,
        "files_found": files_found,
        "requests_made": requests_made,
        "match_rows": len(rows),
        "csv": str(csv_path),
        "note": "Results/fixtures only; odds, player traits and tracking are not included.",
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(f"\nDone: {files_found} season/league files, {len(rows)} match rows")
    print(f"CSV: {csv_path}")
    print("Raw JSON and CSV remain local; nothing was uploaded to GitHub.")


if __name__ == "__main__":
    main()
