#!/usr/bin/env python3
"""Chronological, same-date leakage-aware OpenFootball baseline backtest.

Uses only earlier calendar dates for all predictions on a date. Compares a
rolling venue-specific team-goal Poisson model with a smoothed league-outcome
frequency baseline. Python standard library only.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict, deque
from pathlib import Path


def poisson_probs(lam: float, max_goals: int = 8) -> list[float]:
    lam = max(0.05, min(6.0, lam))
    p = math.exp(-lam)
    probs = [p]
    for k in range(1, max_goals + 1):
        p = probs[-1] * lam / k
        probs.append(p)
    total = sum(probs)
    return [value / total for value in probs]


def outcome_probs(home_lam: float, away_lam: float) -> tuple[float, float, float]:
    hp, ap = poisson_probs(home_lam), poisson_probs(away_lam)
    home = draw = away = 0.0
    for i, p in enumerate(hp):
        for j, q in enumerate(ap):
            if i > j:
                home += p * q
            elif i == j:
                draw += p * q
            else:
                away += p * q
    total = home + draw + away
    return home / total, draw / total, away / total


def safe_float(value: object) -> float | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        number = float(value)
        if not math.isfinite(number) or number < 0:
            return None
        return number
    except (TypeError, ValueError):
        return None


def scores_for(probs: tuple[float, float, float], actual: str) -> tuple[float, float]:
    labels = ("H", "D", "A")
    brier = sum((probs[i] - (1.0 if labels[i] == actual else 0.0)) ** 2 for i in range(3))
    logloss = -math.log(max(1e-12, probs[labels.index(actual)]))
    return brier, logloss


def summarize(records: list[dict], prefix: str) -> dict:
    if not records:
        return {"matches": 0, "accuracy_1x2": None, "mean_brier_1x2": None, "mean_logloss_1x2": None}
    return {
        "matches": len(records),
        "accuracy_1x2": round(sum(r[f"{prefix}_correct"] for r in records) / len(records), 6),
        "mean_brier_1x2": round(sum(r[f"{prefix}_brier"] for r in records) / len(records), 6),
        "mean_logloss_1x2": round(sum(r[f"{prefix}_logloss"] for r in records) / len(records), 6),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="output/openfootball/matches.csv")
    parser.add_argument("--out", default="output/openfootball/model")
    parser.add_argument("--min-history", type=int, default=5)
    parser.add_argument("--window", type=int, default=10)
    args = parser.parse_args()
    if args.min_history < 1 or args.window < 1:
        parser.error("--min-history and --window must be positive integers")

    source, out = Path(args.input), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        raise SystemExit(f"Missing input CSV: {source}")
    with source.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows.sort(key=lambda r: (r.get("date", ""), r.get("league_code", ""), r.get("home_team", ""), r.get("away_team", "")))

    home_scored = defaultdict(lambda: deque(maxlen=args.window))
    home_conceded = defaultdict(lambda: deque(maxlen=args.window))
    away_scored = defaultdict(lambda: deque(maxlen=args.window))
    away_conceded = defaultdict(lambda: deque(maxlen=args.window))
    league_home_goals = defaultdict(lambda: deque(maxlen=100))
    league_away_goals = defaultdict(lambda: deque(maxlen=100))
    league_outcomes = defaultdict(Counter)
    predictions: list[dict] = []
    scored_records: list[dict] = []
    per_league: dict[str, list[dict]] = defaultdict(list)
    skipped_invalid = 0
    eligible_count = 0

    # Group all fixtures by date: every prediction for a date is made before
    # any result from that same date is added to the training history.
    by_date: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_date[row.get("date", "")].append(row)

    for date in sorted(by_date):
        todays_updates = []
        for row in by_date[date]:
            hg = safe_float(row.get("home_goals"))
            ag = safe_float(row.get("away_goals"))
            league = (row.get("league_code") or "").strip()
            home_team = (row.get("home_team") or "").strip()
            away_team = (row.get("away_team") or "").strip()
            if hg is None or ag is None or not league or not home_team or not away_team:
                skipped_invalid += 1
                continue
            hk, ak = (league, home_team), (league, away_team)
            actual = "H" if hg > ag else ("D" if hg == ag else "A")
            team_ready = (
                len(home_scored[hk]) >= args.min_history
                and len(away_scored[ak]) >= args.min_history
                and len(league_home_goals[league]) >= args.min_history
            )
            league_history_count = sum(league_outcomes[league].values())
            if team_ready and league_history_count >= args.min_history:
                base_h = sum(league_home_goals[league]) / len(league_home_goals[league])
                base_a = sum(league_away_goals[league]) / len(league_away_goals[league])
                h_attack = (sum(home_scored[hk]) / len(home_scored[hk])) / max(0.1, base_h)
                h_defence = (sum(home_conceded[hk]) / len(home_conceded[hk])) / max(0.1, base_a)
                a_attack = (sum(away_scored[ak]) / len(away_scored[ak])) / max(0.1, base_a)
                a_defence = (sum(away_conceded[ak]) / len(away_conceded[ak])) / max(0.1, base_h)
                home_lam = max(0.15, min(4.5, base_h * h_attack * a_defence))
                away_lam = max(0.15, min(4.5, base_a * a_attack * h_defence))
                model_probs = outcome_probs(home_lam, away_lam)

                # Laplace-smoothed league outcome baseline from prior dates only.
                counts = league_outcomes[league]
                denom = sum(counts.values()) + 3
                league_probs = tuple((counts[label] + 1) / denom for label in ("H", "D", "A"))
                model_brier, model_logloss = scores_for(model_probs, actual)
                base_brier, base_logloss = scores_for(league_probs, actual)
                model_pred = ("H", "D", "A")[max(range(3), key=lambda i: model_probs[i])]
                base_pred = ("H", "D", "A")[max(range(3), key=lambda i: league_probs[i])]
                rec = {
                    "date": date, "season": row.get("season", ""), "league_code": league,
                    "home_team": home_team, "away_team": away_team,
                    "actual_home_goals": int(hg), "actual_away_goals": int(ag),
                    "pred_home_goals": round(home_lam, 3), "pred_away_goals": round(away_lam, 3),
                    "p_home": round(model_probs[0], 6), "p_draw": round(model_probs[1], 6),
                    "p_away": round(model_probs[2], 6), "predicted_1x2": model_pred,
                    "actual_1x2": actual, "brier_1x2": round(model_brier, 6),
                    "logloss_1x2": round(model_logloss, 6),
                    "baseline_p_home": round(league_probs[0], 6),
                    "baseline_p_draw": round(league_probs[1], 6),
                    "baseline_p_away": round(league_probs[2], 6),
                    "baseline_predicted_1x2": base_pred,
                    "baseline_brier_1x2": round(base_brier, 6),
                    "baseline_logloss_1x2": round(base_logloss, 6),
                    "method": "rolling venue-specific goals; prior calendar dates only",
                }
                predictions.append(rec)
                score_record = {
                    "model_correct": int(model_pred == actual), "model_brier": model_brier,
                    "model_logloss": model_logloss, "baseline_correct": int(base_pred == actual),
                    "baseline_brier": base_brier, "baseline_logloss": base_logloss,
                }
                scored_records.append(score_record)
                per_league[league].append(score_record)
                eligible_count += 1

            todays_updates.append((league, hk, ak, hg, ag, actual))

        # Update training state only after all fixtures for this date were forecast.
        for league, hk, ak, hg, ag, actual in todays_updates:
            home_scored[hk].append(hg)
            home_conceded[hk].append(ag)
            away_scored[ak].append(ag)
            away_conceded[ak].append(hg)
            league_home_goals[league].append(hg)
            league_away_goals[league].append(ag)
            league_outcomes[league][actual] += 1

    pred_path = out / "chronological_predictions.csv"
    fields = list(predictions[0]) if predictions else [
        "date", "season", "league_code", "home_team", "away_team",
        "actual_home_goals", "actual_away_goals", "pred_home_goals", "pred_away_goals",
        "p_home", "p_draw", "p_away", "predicted_1x2", "actual_1x2",
        "brier_1x2", "logloss_1x2", "baseline_p_home", "baseline_p_draw",
        "baseline_p_away", "baseline_predicted_1x2", "baseline_brier_1x2",
        "baseline_logloss_1x2", "method"
    ]
    with pred_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(predictions)

    per_league_metrics = {
        league: {
            "team_model": summarize(items, "model"),
            "league_frequency_baseline": summarize(items, "baseline"),
        }
        for league, items in sorted(per_league.items())
    }
    metrics = {
        "method": "chronological rolling venue-specific goals Poisson baseline",
        "data_source": "OpenFootball football.json",
        "matches_in_source_csv": len(rows),
        "backtested_matches": eligible_count,
        "rows_skipped_for_missing_or_invalid_fields": skipped_invalid,
        "min_history_per_team_venue": args.min_history,
        "rolling_window": args.window,
        "same_date_leakage_control": "All matches on a calendar date are forecast before any results from that date enter history; kickoff times are not available.",
        "team_model": summarize(scored_records, "model"),
        "league_frequency_baseline": summarize(scored_records, "baseline"),
        "per_league": per_league_metrics,
        "limitations": [
            "Baseline only; no odds, lineups, injuries, player traits or tracking.",
            "League outcome baseline is a smoothed prior-results benchmark, not bookmaker odds.",
            "Calendar dates are available but kickoff times are not; same-date results are withheld together.",
            "Metrics are not proof of betting profitability. Evaluate by season and against odds-based benchmarks where licensed data is available.",
            "Predictions are estimates, not guaranteed outcomes."
        ],
        "predictions_csv": str(pred_path),
    }
    metrics_path = out / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    if eligible_count == 0:
        raise SystemExit("No eligible matches for backtesting. Check score parsing and data coverage.")


if __name__ == "__main__":
    main()
