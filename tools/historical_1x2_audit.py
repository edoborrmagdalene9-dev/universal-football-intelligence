#!/usr/bin/env python3
"""Historical 1X2 slip audit using the CC0/ODC-BY football results archive.

Downloads the public results archive on first run and keeps it in a local cache.
It does NOT contain bookmaker odds, and it cannot guarantee that a pick is a
"spoiler". It ranks selections by a transparent historical-frequency baseline.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

DATA_URL = (
    "https://raw.githubusercontent.com/schochastics/football-data/"
    "master/data/results/games.parquet"
)
DATASET_PAGE = "https://github.com/schochastics/football-data"
ATTRIBUTION = (
    "Dataset: schochastics/football-data, Open Data Commons Attribution "
    "License (ODC-BY 1.0); source: https://github.com/schochastics/football-data"
)
OUTCOMES = ("H", "D", "A")
LABELS = {"H": "HOME", "D": "DRAW", "A": "AWAY"}


def normalize(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def selection_code(value: str) -> str:
    value = normalize(value)
    aliases = {
        "h": "H", "home": "H", "home win": "H", "1": "H",
        "d": "D", "draw": "D", "x": "D",
        "a": "A", "away": "A", "away win": "A", "2": "A",
    }
    if value not in aliases:
        raise ValueError(f"Unsupported selection {value!r}; use Home/Draw/Away or 1/X/2.")
    return aliases[value]


def download_dataset(cache_dir: Path, refresh: bool = False) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    destination = cache_dir / "games.parquet"
    if destination.exists() and destination.stat().st_size > 1_000_000 and not refresh:
        return destination
    temp = destination.with_suffix(".parquet.part")
    request = urllib.request.Request(
        DATA_URL,
        headers={"User-Agent": "UniversalFootballIntelligence/1.0 (historical audit)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response, temp.open("wb") as out:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
        if temp.stat().st_size < 1_000_000:
            raise RuntimeError("Downloaded archive is unexpectedly small; refusing to cache it.")
        temp.replace(destination)
    except Exception:
        temp.unlink(missing_ok=True)
        raise
    return destination


def load_matches(path: Path):
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError(
            "Missing optional dependencies. Install with: pip install pandas pyarrow"
        ) from exc
    frame = pd.read_parquet(path)
    required = {"date", "home", "away", "gh", "ga"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError("Dataset schema changed; missing columns: " + ", ".join(sorted(missing)))
    if "full_time" in frame.columns:
        frame = frame[frame["full_time"].fillna("F").astype(str).str.upper().eq("F")]
    frame = frame.dropna(subset=["date", "home", "away", "gh", "ga"]).copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce", utc=True)
    frame = frame.dropna(subset=["date"])
    frame["home"] = frame["home"].astype(str).str.strip()
    frame["away"] = frame["away"].astype(str).str.strip()
    frame["competition"] = frame["competition"].fillna("UNKNOWN").astype(str) if "competition" in frame else "UNKNOWN"
    frame["gh"] = pd.to_numeric(frame["gh"], errors="coerce")
    frame["ga"] = pd.to_numeric(frame["ga"], errors="coerce")
    frame = frame.dropna(subset=["gh", "ga"])
    frame = frame[(frame["gh"] >= 0) & (frame["ga"] >= 0)]
    frame = frame.sort_values("date")
    records = []
    for row in frame.itertuples(index=False):
        h, a = int(row.gh), int(row.ga)
        result = "H" if h > a else ("D" if h == a else "A")
        records.append({
            "date": row.date.date(),
            "home": str(row.home).strip(),
            "away": str(row.away).strip(),
            "home_key": normalize(row.home),
            "away_key": normalize(row.away),
            "competition": str(row.competition),
            "competition_key": normalize(row.competition),
            "result": result,
        })
    if not records:
        raise ValueError("No usable historical results were found.")
    return records


def probabilities(counter: Counter, prior: Counter, strength: float = 12.0):
    """Dirichlet-smoothed empirical 1X2 distribution."""
    total_prior = sum(prior.get(k, 0) for k in OUTCOMES)
    prior_p = {k: (prior.get(k, 0) / total_prior if total_prior else 1 / 3) for k in OUTCOMES}
    total = sum(counter.get(k, 0) for k in OUTCOMES)
    denom = total + strength
    return {k: (counter.get(k, 0) + strength * prior_p[k]) / denom for k in OUTCOMES}


def audit(rows, picks, min_team_sample=5):
    # Build only historical team/competition result counts. No odds or live context
    # are claimed. For each fixture, the model uses league prior + home team's
    # home record + away team's away record, with explicit smoothing.
    league = defaultdict(Counter)
    home_team = defaultdict(Counter)
    away_team = defaultdict(Counter)
    latest_date = max(r["date"] for r in rows)
    for r in rows:
        league[r["competition_key"]][r["result"]] += 1
        home_team[r["home_key"]][r["result"]] += 1
        away_team[r["away_key"]][r["result"]] += 1

    overall = Counter()
    for c in league.values():
        overall.update(c)
    results = []
    for pick in picks:
        comp_key = normalize(pick.get("competition", ""))
        home_name = str(pick.get("home_team", "")).strip()
        away_name = str(pick.get("away_team", "")).strip()
        home_key, away_key = normalize(home_name), normalize(away_name)
        selection = selection_code(str(pick.get("selection", "")))
        if not home_key or not away_key:
            raise ValueError("Every pick needs home_team and away_team.")
        try:
            kickoff = date.fromisoformat(str(pick.get("date", "")).strip()[:10])
        except ValueError as exc:
            raise ValueError("Every pick needs a valid date in YYYY-MM-DD format.") from exc

        # Do not leak matches played on/after the target date. For future fixtures,
        # this naturally uses all available archive records up to its data cutoff.
        # Strict chronological cutoff: never backfill a historical fixture with
        # matches played after kickoff. If the archive has no earlier records,
        # return neutral/insufficient-history output rather than leaking the future.
        past = [r for r in rows if r["date"] < kickoff]
        model_data_cutoff = str(max((r["date"] for r in past), default="NO_PRIOR_RESULTS"))
        past_league = Counter(r["result"] for r in past if not comp_key or r["competition_key"] == comp_key)
        if sum(past_league.values()) < 30:
            past_league = Counter(r["result"] for r in past)
        hp = Counter(r["result"] for r in past if r["home_key"] == home_key)
        ap = Counter(r["result"] for r in past if r["away_key"] == away_key)
        prior = past_league or Counter(r["result"] for r in past)
        # Combine venue-relevant empirical evidence. Smoothed estimates are blended
        # with the competition baseline; this is a transparent screening baseline,
        # not a fitted or calibrated production forecast.
        base = probabilities(Counter(), prior, 1.0)
        hdist = probabilities(hp, prior, 12.0)
        adist = probabilities(ap, prior, 12.0)
        probs = {k: 0.45 * base[k] + 0.30 * hdist[k] + 0.25 * adist[k] for k in OUTCOMES}
        norm = sum(probs.values())
        probs = {k: v / norm for k, v in probs.items()}
        selected_p = probs[selection]
        sample = len(hp) + len(ap)
        if not hp or not ap:
            status = "INSUFFICIENT_TEAM_HISTORY"
        elif sample < min_team_sample * 2:
            status = "LOW_TEAM_SAMPLE"
        elif selected_p < 0.25:
            status = "HIGH_RISK_SCREEN"
        elif selected_p < 0.38:
            status = "REVIEW"
        else:
            status = "LOWER_HISTORICAL_RISK"
        results.append({
            "date": str(pick.get("date", "")),
            "competition": str(pick.get("competition", "")),
            "home_team": home_name,
            "away_team": away_name,
            "selection": LABELS[selection],
            "p_home_baseline": round(probs["H"], 4),
            "p_draw_baseline": round(probs["D"], 4),
            "p_away_baseline": round(probs["A"], 4),
            "selected_probability_baseline": round(selected_p, 4),
            "home_team_historical_matches": sum(hp.values()),
            "away_team_historical_away_matches": sum(ap.values()),
            "historical_data_cutoff": str(latest_date),
            "model_data_cutoff": model_data_cutoff,
            "screen": status,
            "reason": (
                "Selected outcome has low baseline probability; investigate with current team news, "
                "lineups, odds and a separately validated model."
                if status == "HIGH_RISK_SCREEN" else
                "Historical sample is limited or unavailable; do not treat this as a confirmed spoiler."
                if status in ("LOW_TEAM_SAMPLE", "INSUFFICIENT_TEAM_HISTORY") else
                "Screening flag only; not a guarantee and not a standalone betting decision."
            ),
        })
    results.sort(key=lambda r: (r["selected_probability_baseline"], r["home_team"], r["away_team"]))
    return {
        "source": DATASET_PAGE,
        "attribution": ATTRIBUTION,
        "dataset_matches_loaded": len(rows),
        "historical_data_cutoff": str(latest_date),
        "dataset_latest_date": str(latest_date),
        "picks_audited": len(results),
        "method": "Smoothed historical 1X2 outcome frequencies, competition prior + home-team record + away-team away record.",
        "limitations": [
            "This archive contains results, not historical bookmaker odds or pre-match market prices.",
            "Dataset coverage is broad but incomplete and its published results stop at 2023; verify the actual cutoff in the report.",
            "Team names can change; unmatched names produce weak/unknown evidence rather than fuzzy guesses.",
            "This is a screening baseline, not a calibrated model, guaranteed spoiler detector, or proof of value.",
            "Current injuries, lineups, tactical changes, schedule congestion and market prices are not represented.",
        ],
        "picks": results,
    }


def read_picks(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"home_team", "away_team", "selection"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("Slip CSV needs columns: home_team,away_team,selection; date and competition are optional.")
        return list(reader)


def main():
    parser = argparse.ArgumentParser(description="Audit a home/draw/away slip against historical results.")
    parser.add_argument("slip_csv", help="CSV with home_team,away_team,selection; optional date,competition")
    parser.add_argument("--cache-dir", default=".cache/ufi-historical", help="local dataset cache directory")
    parser.add_argument("--out", default="historical-1x2-audit.json", help="JSON report path")
    parser.add_argument("--refresh", action="store_true", help="redownload the historical archive")
    args = parser.parse_args()
    try:
        parquet = download_dataset(Path(args.cache_dir), args.refresh)
        rows = load_matches(parquet)
        report = audit(rows, read_picks(Path(args.slip_csv)))
        Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps({k: v for k, v in report.items() if k != "picks"}, indent=2))
        for pick in report["picks"]:
            print(
                f'{pick["screen"]:25} {pick["selection"]:4} {pick["home_team"]} vs {pick["away_team"]} '
                f'| selected baseline={pick["selected_probability_baseline"]:.1%}'
            )
        print(f"Full report: {args.out}")
        print("Attribution: " + ATTRIBUTION)
    except Exception as exc:
        print(f"Historical 1X2 audit failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
