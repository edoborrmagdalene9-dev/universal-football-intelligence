"""Chronological scoreline baseline evaluation; predictions use past matches only."""
import math

def pmf(k, rate):
    if rate == 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-rate + k * math.log(rate) - math.lgamma(k + 1))

def result_probs(home_rate, away_rate, cap=10):
    home = draw = away = 0.0
    exact = {}
    for h in range(cap + 1):
        for a in range(cap + 1):
            p = pmf(h, home_rate) * pmf(a, away_rate)
            exact[(h, a)] = p
            if h > a: home += p
            elif h == a: draw += p
            else: away += p
    total = home + draw + away
    return exact, (home / total, draw / total, away / total)

def evaluate(rows, min_history=100, team_window=10):
    past, team, predictions = [], {}, []
    for row in rows:
        if len(past) >= min_history:
            mean_h = sum(x["home_goals"] for x in past) / len(past)
            mean_a = sum(x["away_goals"] for x in past) / len(past)
            def rates(name):
                t = team.get(name, {"gf": [], "ga": []})
                n = len(t["gf"])
                base = max(.05, (mean_h + mean_a) / 2)
                return ((sum(t["gf"]) + 5*base)/(n+5)/base,
                        (sum(t["ga"]) + 5*base)/(n+5)/base)
            ha, hd = rates(row["home_team"]); aa, ad = rates(row["away_team"])
            models = {"league_poisson": (max(.05, mean_h), max(.05, mean_a)),
                      "rolling_team_rates": (max(.05, mean_h*ha*ad), max(.05, mean_a*aa*hd))}
            actual = (row["home_goals"], row["away_goals"])
            cls = 0 if actual[0] > actual[1] else (1 if actual[0] == actual[1] else 2)
            rec = {"date": row.get("date"), "home_team": row["home_team"], "away_team": row["away_team"],
                   "home_goals": actual[0], "away_goals": actual[1], "models": {}}
            for name, (lh, la) in models.items():
                exact, probs = result_probs(lh, la)
                rec["models"][name] = {"lambda_home": lh, "lambda_away": la,
                    "exact_score_logloss": -math.log(max(1e-12, exact.get(actual, 0))),
                    "one_x_two_logloss": -math.log(max(1e-12, probs[cls])),
                    "one_x_two_brier": sum((probs[i]-(i==cls))**2 for i in range(3)),
                    "p_home": probs[0], "p_draw": probs[1], "p_away": probs[2]}
            predictions.append(rec)
        past.append(row)
        for name, gf, ga in ((row["home_team"], row["home_goals"], row["away_goals"]),
                             (row["away_team"], row["away_goals"], row["home_goals"])):
            t = team.setdefault(name, {"gf": [], "ga": []})
            t["gf"] = (t["gf"] + [gf])[-team_window:]
            t["ga"] = (t["ga"] + [ga])[-team_window:]
    summary = {"models": {}}
    for name in ("league_poisson", "rolling_team_rates"):
        vals = [p["models"][name] for p in predictions]
        summary["models"][name] = {"n": len(vals)}
        for metric in ("exact_score_logloss", "one_x_two_logloss", "one_x_two_brier"):
            summary["models"][name][metric] = sum(v[metric] for v in vals)/len(vals) if vals else None
    summary["historical_matches"] = len(rows)
    summary["evaluated_unseen_matches"] = len(predictions)
    summary["note"] = "Lower scores are better. Chronological benchmark only; not proof of calibration or profit."
    return summary, predictions


def read_results_csv(path):
    import csv
    from datetime import datetime
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"date", "home_team", "away_team", "home_goals", "away_goals"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("CSV columns required: date,home_team,away_team,home_goals,away_goals")
        rows = []
        for line, row in enumerate(reader, 2):
            try:
                stamp = datetime.fromisoformat(row["date"].strip().replace("Z", "+00:00")).timestamp()
                match = {"date": row["date"], "home_team": row["home_team"].strip(),
                         "away_team": row["away_team"].strip(), "home_goals": int(row["home_goals"]),
                         "away_goals": int(row["away_goals"]), "_timestamp": stamp}
                if not match["home_team"] or not match["away_team"] or min(match["home_goals"], match["away_goals"]) < 0:
                    raise ValueError()
                rows.append(match)
            except (ValueError, TypeError) as exc:
                raise ValueError("Invalid CSV row " + str(line)) from exc
    rows.sort(key=lambda item: item["_timestamp"])
    for row in rows:
        row.pop("_timestamp", None)
    return rows


def main():
    import argparse
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser(description="Chronological scoreline baseline evaluation")
    parser.add_argument("csv", help="historical results CSV")
    parser.add_argument("--min-history", type=int, default=100)
    parser.add_argument("--window", type=int, default=10)
    parser.add_argument("--out", default="exact-score-walkforward-report.json")
    args = parser.parse_args()
    summary, predictions = evaluate(read_results_csv(args.csv), max(1, args.min_history), max(1, args.window))
    summary["predictions"] = predictions
    Path(args.out).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key != "predictions"}, indent=2))
    print("Full report written to " + args.out)


if __name__ == "__main__":
    main()
