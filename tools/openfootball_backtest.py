#!/usr/bin/env python3
"""Build a chronological, leakage-aware baseline backtest from OpenFootball matches.

Uses only prior completed matches from the same league to estimate each team's
home/away scoring rates. Outputs per-match predictions and summary metrics.
Python standard library only.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict, deque
from pathlib import Path

def poisson_probs(lam: float, max_goals: int = 8) -> list[float]:
    lam = max(0.05, min(6.0, lam))
    p = math.exp(-lam)
    probs = [p]
    for k in range(1, max_goals + 1):
        p = probs[-1] * lam / k
        probs.append(p)
    total = sum(probs)
    return [p / total for p in probs]

def outcome_probs(home_lam: float, away_lam: float) -> tuple[float, float, float]:
    hp, ap = poisson_probs(home_lam), poisson_probs(away_lam)
    home = draw = away = 0.0
    for i, p in enumerate(hp):
        for j, q in enumerate(ap):
            if i > j: home += p*q
            elif i == j: draw += p*q
            else: away += p*q
    total = home + draw + away
    return home/total, draw/total, away/total

def safe_float(value: str) -> float | None:
    try:
        if value is None or str(value).strip() == "": return None
        return float(value)
    except (TypeError, ValueError):
        return None

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="output/openfootball/matches.csv")
    parser.add_argument("--out", default="output/openfootball/model")
    parser.add_argument("--min-history", type=int, default=5)
    parser.add_argument("--window", type=int, default=10)
    args = parser.parse_args()

    source = Path(args.input)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        raise SystemExit(f"Missing input CSV: {source}")

    with source.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows.sort(key=lambda r: (r.get("date", ""), r.get("league_code", "")))

    # Maintain separate home/away goal history per team and league.
    home_scored = defaultdict(lambda: deque(maxlen=args.window))
    home_conceded = defaultdict(lambda: deque(maxlen=args.window))
    away_scored = defaultdict(lambda: deque(maxlen=args.window))
    away_conceded = defaultdict(lambda: deque(maxlen=args.window))
    league_home = defaultdict(lambda: deque(maxlen=100))
    league_away = defaultdict(lambda: deque(maxlen=100))
    predictions = []
    brier_total = logloss_total = correct = evaluated = 0

    for row in rows:
        hg, ag = safe_float(row.get("home_goals")), safe_float(row.get("away_goals"))
        league = row.get("league_code", "")
        home_team, away_team = row.get("home_team", ""), row.get("away_team", "")
        if hg is None or ag is None or not league or not home_team or not away_team:
            continue
        hk, ak = (league, home_team), (league, away_team)

        # Predict only when each team has enough prior venue-specific history.
        if (len(home_scored[hk]) >= args.min_history and
            len(away_scored[ak]) >= args.min_history and
            len(league_home[league]) >= args.min_history):
            base_h = sum(league_home[league]) / len(league_home[league])
            base_a = sum(league_away[league]) / len(league_away[league])
            h_attack = (sum(home_scored[hk]) / len(home_scored[hk])) / max(0.1, base_h)
            h_defence = (sum(home_conceded[hk]) / len(home_conceded[hk])) / max(0.1, base_a)
            a_attack = (sum(away_scored[ak]) / len(away_scored[ak])) / max(0.1, base_a)
            a_defence = (sum(away_conceded[ak]) / len(away_conceded[ak])) / max(0.1, base_h)
            home_lam = max(0.15, min(4.5, base_h * h_attack * a_defence))
            away_lam = max(0.15, min(4.5, base_a * a_attack * h_defence))
            ph, pd, pa = outcome_probs(home_lam, away_lam)
            actual = "H" if hg > ag else ("D" if hg == ag else "A")
            probs = {"H": ph, "D": pd, "A": pa}
            brier = sum((probs[k] - (1.0 if k == actual else 0.0))**2 for k in ("H","D","A"))
            logloss = -math.log(max(1e-12, probs[actual]))
            predicted = max(probs, key=probs.get)
            brier_total += brier
            logloss_total += logloss
            correct += int(predicted == actual)
            evaluated += 1
            predictions.append({
                "date": row.get("date", ""), "season": row.get("season", ""),
                "league_code": league, "home_team": home_team, "away_team": away_team,
                "actual_home_goals": int(hg), "actual_away_goals": int(ag),
                "pred_home_goals": round(home_lam, 3), "pred_away_goals": round(away_lam, 3),
                "p_home": round(ph, 6), "p_draw": round(pd, 6), "p_away": round(pa, 6),
                "predicted_1x2": predicted, "actual_1x2": actual,
                "brier_1x2": round(brier, 6), "logloss_1x2": round(logloss, 6),
                "method": "rolling venue-specific goals baseline; prior matches only"
            })

        # Add the observed result only after forecasting it: prevents future leakage.
        home_scored[hk].append(hg)
        home_conceded[hk].append(ag)
        away_scored[ak].append(ag)
        away_conceded[ak].append(hg)
        league_home[league].append(hg)
        league_away[league].append(ag)

    pred_path = out / "chronological_predictions.csv"
    fields = list(predictions[0]) if predictions else [
        "date","season","league_code","home_team","away_team","actual_home_goals",
        "actual_away_goals","pred_home_goals","pred_away_goals","p_home","p_draw",
        "p_away","predicted_1x2","actual_1x2","brier_1x2","logloss_1x2","method"
    ]
    with pred_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(predictions)

    metrics = {
        "method": "chronological rolling venue-specific goals baseline",
        "data_source": "OpenFootball football.json",
        "matches_in_source_csv": len(rows),
        "backtested_matches": evaluated,
        "min_history_per_team_venue": args.min_history,
        "rolling_window": args.window,
        "accuracy_1x2": round(correct/evaluated, 6) if evaluated else None,
        "mean_brier_1x2": round(brier_total/evaluated, 6) if evaluated else None,
        "mean_logloss_1x2": round(logloss_total/evaluated, 6) if evaluated else None,
        "limitations": [
            "Baseline only; no odds, lineups, injuries, player traits or tracking.",
            "League-average and team rates are simple descriptive features, not a calibrated production model.",
            "Metrics must be compared with naive baselines and interpreted by league/season.",
            "Predictions are estimates, not guaranteed outcomes."
        ],
        "predictions_csv": str(pred_path)
    }
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    if evaluated == 0:
        raise SystemExit("No eligible matches for backtesting. Check score parsing and data coverage.")

if __name__ == "__main__":
    main()
