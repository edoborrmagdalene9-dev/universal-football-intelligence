#!/usr/bin/env python3
"""Download permitted TheStatsAPI match data to a LOCAL, git-ignored folder.

No API key is stored in this file. Set THESTATSAPI_API_KEY in your shell.
Start with one competition/season to understand request usage before broad pulls.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://api.thestatsapi.com/api"
DEFAULT_OUT = Path("data/private/thestatsapi")


def request_json(path: str, params: dict | None = None) -> dict:
    key = os.environ.get("THESTATSAPI_API_KEY")
    if not key:
        raise RuntimeError(
            "Missing THESTATSAPI_API_KEY. Create a key in your TheStatsAPI account "
            "and set it as an environment variable; never commit it to GitHub."
        )
    query = "?" + urlencode(params) if params else ""
    req = Request(
        BASE_URL + path + query,
        headers={
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
            "User-Agent": "UFI-local-research-client/1.0",
        },
    )
    try:
        with urlopen(req, timeout=45) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"API HTTP {exc.code} for {path}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error for {path}: {exc}") from exc


def fetch_pages(path: str, params: dict | None = None, pause: float = 0.25) -> list:
    collected = []
    page = 1
    while True:
        query = dict(params or {})
        query.update({"page": page, "per_page": 100})
        body = request_json(path, query)
        rows = body.get("data", [])
        if not isinstance(rows, list):
            raise RuntimeError(f"Unexpected response shape for {path}: expected data list")
        collected.extend(rows)
        meta = body.get("meta") or {}
        total_pages = int(meta.get("total_pages", page))
        if page >= total_pages:
            break
        page += 1
        if pause:
            time.sleep(pause)
    return collected


def safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    return value[:100] or "unknown"


def save_json(out_dir: Path, name: str, payload: dict) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{safe_name(name)}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--competition-id", help="Fetch a single competition, e.g. comp_3039")
    parser.add_argument("--season-id", help="Optional season ID; requires --competition-id")
    parser.add_argument("--search", help="Search competition names, e.g. Premier League")
    parser.add_argument("--all-competitions", action="store_true",
                        help="Fetch multiple competitions; use --max-competitions to control scope")
    parser.add_argument("--max-competitions", type=int, default=5,
                        help="Maximum competitions for --all-competitions (default: 5; 0 means no client-side cap)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help=f"Local output directory (default: {DEFAULT_OUT})")
    parser.add_argument("--pause", type=float, default=0.25,
                        help="Seconds between paginated requests (default: 0.25)")
    args = parser.parse_args()

    if args.season_id and not args.competition_id:
        parser.error("--season-id requires --competition-id")
    if args.competition_id and args.all_competitions:
        parser.error("Choose --competition-id or --all-competitions, not both")

    try:
        if args.competition_id:
            competitions = [request_json(f"/football/competitions/{args.competition_id}").get("data", {})]
        else:
            competitions = fetch_pages(
                "/football/competitions",
                {"search": args.search} if args.search else {},
                pause=args.pause,
            )
            if not args.all_competitions:
                if args.search:
                    competitions = competitions[:1]
                else:
                    parser.error("Use --competition-id, --search, or explicitly pass --all-competitions")
            elif args.max_competitions > 0:
                competitions = competitions[:args.max_competitions]

        manifest = {
            "source": "TheStatsAPI",
            "source_url": "https://www.thestatsapi.com/",
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "scope": {
                "competition_id": args.competition_id,
                "season_id": args.season_id,
                "search": args.search,
                "all_competitions": args.all_competitions,
                "competition_count": len(competitions),
            },
            "records": [],
            "note": "Raw API snapshots; availability varies by competition and season. Keep local unless your data licence permits redistribution.",
        }

        for comp in competitions:
            comp_id = comp.get("id")
            if not comp_id:
                continue
            comp_name = comp.get("name", comp_id)
            if args.season_id:
                seasons = [{"id": args.season_id}]
            else:
                season_body = request_json(f"/football/competitions/{comp_id}/seasons")
                seasons = season_body.get("data", [])
            save_json(args.out, f"competition_{comp_id}", {
                "source": "TheStatsAPI",
                "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                "data": comp,
            })
            print(f"[{comp_name}] {len(seasons)} season(s)")
            for season in seasons:
                season_id = season.get("id")
                if not season_id:
                    continue
                matches = fetch_pages(
                    "/football/matches",
                    {"competition_id": comp_id, "season_id": season_id, "status": "finished"},
                    pause=args.pause,
                )
                filename = f"matches_{comp_id}_{season_id}"
                save_json(args.out, filename, {
                    "source": "TheStatsAPI",
                    "source_url": "https://www.thestatsapi.com/",
                    "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                    "competition": {"id": comp_id, "name": comp_name},
                    "season": season,
                    "data": matches,
                })
                manifest["records"].append({
                    "competition_id": comp_id,
                    "competition_name": comp_name,
                    "season_id": season_id,
                    "match_count": len(matches),
                    "file": f"{safe_name(filename)}.json",
                })
                print(f"  {season_id}: saved {len(matches)} finished matches")
                if args.pause:
                    time.sleep(args.pause)

        manifest_path = save_json(args.out, "manifest", manifest)
        print(f"Done. Manifest: {manifest_path}")
        print("Files are local and git-ignored; do not upload raw data unless your licence permits it.")
        return 0
    except (RuntimeError, KeyError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
