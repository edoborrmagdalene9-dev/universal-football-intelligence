"""Opt-in StatsBomb Open Data downloader with local cache and CSV export.

Usage:
  python -m dfs_optimizer.src.data_acquisition --list
  python -m dfs_optimizer.src.data_acquisition --competition-id 2 --season-id 44

IDs must be chosen from the live competitions.json listing. Downloads stay local;
this script does not bundle or redistribute provider data.
"""
import argparse
import csv
import json
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

BASE = "https://raw.githubusercontent.com/hudl/open-data/master/data"
USER_AGENT = "UFI-Research-Data-Client/1.0 (user-initiated download)"


def fetch_json(url, timeout=30, retries=3):
    last = None
    for attempt in range(retries):
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(request, timeout=timeout) as response:
                if response.status != 200:
                    raise RuntimeError(f"HTTP {response.status} from {url}")
                return json.loads(response.read().decode("utf-8"))
        except (URLError, HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
            if attempt + 1 < retries:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Could not retrieve valid JSON from {url}: {last}")


def list_competitions(cache_dir="data/remote_cache"):
    cache = Path(cache_dir); cache.mkdir(parents=True, exist_ok=True)
    path = cache / "competitions.json"
    if path.exists():
        try: return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError: path.unlink()
    data = fetch_json(f"{BASE}/competitions.json")
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def download_season(competition_id, season_id, output_dir="data/external/statsbomb", delay=0.15):
    competitions = list_competitions()
    found = [c for c in competitions if str(c.get("competition_id")) == str(competition_id)
             and str(c.get("season_id")) == str(season_id)]
    if not found:
        raise ValueError("Competition/season ID pair was not found in current StatsBomb competitions.json")
    comp = found[0]
    url = f"{BASE}/matches/{competition_id}/{season_id}.json"
    matches = fetch_json(url)
    if not isinstance(matches, list) or not matches:
        raise ValueError("Selected competition-season returned no match records")
    out = Path(output_dir) / f"competition_{competition_id}_season_{season_id}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "matches.json").write_text(json.dumps(matches, indent=2), encoding="utf-8")
    rows, issues = [], []
    for item in matches:
        try:
            home = item.get("home_team", {}).get("home_team_name") or item.get("home_team", {}).get("name")
            away = item.get("away_team", {}).get("away_team_name") or item.get("away_team", {}).get("name")
            date = item.get("match_date")
            hs, aws = item.get("home_score"), item.get("away_score")
            if not all([home, away, date]) or hs is None or aws is None:
                issues.append({"match_id": item.get("match_id"), "reason": "missing team/date/final score"})
                continue
            rows.append({"date": date, "home_team": home, "away_team": away,
                         "home_goals": int(hs), "away_goals": int(aws),
                         "match_id": item.get("match_id")})
        except (TypeError, ValueError, AttributeError) as exc:
            issues.append({"match_id": item.get("match_id"), "reason": str(exc)})
    if rows:
        with (out / "matches.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["date", "home_team", "away_team", "home_goals", "away_goals", "match_id"])
            writer.writeheader(); writer.writerows(rows)
    manifest = {"source": "StatsBomb Open Data", "source_url": url, "competition": comp.get("competition_name"),
                "competition_id": competition_id, "season_id": season_id, "retrieved_at_unix": int(time.time()),
                "records_received": len(matches), "csv_rows_validated_for_required_fields": len(rows),
                "records_skipped": issues, "terms_reminder": "Check current StatsBomb user agreement; attribution and publication conditions apply."}
    (out / "source_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {"directory": str(out), "manifest": manifest}



def download_season_with_events(competition_id, season_id, output_dir="data/external/statsbomb",
                                delay=0.15, max_matches=None):
    """Add historical event/lineup downloads without changing the original results-only API."""
    if max_matches is not None and max_matches < 1:
        raise ValueError("max_matches must be >= 1 when supplied")
    result = download_season(competition_id, season_id, output_dir)
    out = Path(result["directory"])
    matches = json.loads((out / "matches.json").read_text(encoding="utf-8"))
    selected = matches[:max_matches] if max_matches else matches
    event_dir, lineup_dir = out / "events", out / "lineups"
    event_dir.mkdir(parents=True, exist_ok=True)
    lineup_dir.mkdir(parents=True, exist_ok=True)
    event_downloads, lineup_downloads, errors = 0, 0, []
    for match in selected:
        match_id = match.get("match_id")
        if match_id is None:
            errors.append({"match_id": None, "reason": "match record missing match_id"})
            continue
        for kind, target_dir in (("events", event_dir), ("lineups", lineup_dir)):
            target = target_dir / f"{match_id}.json"
            if target.exists():
                if kind == "events": event_downloads += 1
                else: lineup_downloads += 1
                continue
            try:
                data = fetch_json(f"{BASE}/{kind}/{match_id}.json")
                target.write_text(json.dumps(data, indent=2), encoding="utf-8")
                if kind == "events": event_downloads += 1
                else: lineup_downloads += 1
            except Exception as exc:
                errors.append({"match_id": match_id, "kind": kind, "reason": str(exc)})
            time.sleep(max(0.0, delay))
    manifest_path = out / "source_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({"event_files_downloaded": event_downloads,
                     "lineup_files_downloaded": lineup_downloads,
                     "event_download_errors": errors})
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    result["manifest"] = manifest
    return result

def main():
    parser = argparse.ArgumentParser(description="Opt-in downloader for selected StatsBomb Open Data")
    parser.add_argument("--list", action="store_true", help="List available competition-season IDs")
    parser.add_argument("--competition-id")
    parser.add_argument("--season-id")
    parser.add_argument("--output-dir", default="data/external/statsbomb")
    parser.add_argument("--include-events", action="store_true", help="Also download historical event and lineup JSON files")
    parser.add_argument("--max-matches", type=int, help="Limit event/lineup download count for bandwidth control")
    args = parser.parse_args()
    if args.list:
        for item in list_competitions():
            print(f'{item.get("competition_id")}\t{item.get("season_id")}\t{item.get("competition_name")}\t{item.get("season_name")}')
        return
    if not args.competition_id or not args.season_id:
        parser.error("supply --list or both --competition-id and --season-id")
    if args.include_events:
        print(json.dumps(download_season_with_events(args.competition_id, args.season_id, args.output_dir, max_matches=args.max_matches), indent=2))
        return
    print(json.dumps(download_season(args.competition_id, args.season_id, args.output_dir), indent=2))


if __name__ == "__main__":
    main()
