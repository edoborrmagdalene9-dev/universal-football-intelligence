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
            rec = {"models": {}}
            for name, (lh, la) in models.items():
                exact, probs = result_probs(lh, la)
                rec["models"][name] = {"exact_score_logloss": -math.log(max(1e-12, exact.get(actual, 0))),
                    "one_x_two_logloss": -math.log(max(1e-12, probs[cls])),
                    "one_x_two_brier": sum((probs[i]-(i==cls))**2 for i in range(3))}
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
    return summary, predictions
