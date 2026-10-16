#!/usr/bin/env python3
"""Chronological UFI research model: Elo probabilities plus a Poisson score model.

All predictions for a calendar date are made before any results from that date
are added. This is research infrastructure, not a betting recommendation.
"""
import argparse, csv, json, math
from datetime import datetime, timezone
from collections import defaultdict, deque
from pathlib import Path

LABELS = ("H", "D", "A")
def probs_from_ratings(home_rating, away_rating, draw_base=0.26):
    # Bradley-Terry-style home/away strength, with an explicit draw component.
    diff = max(-800.0, min(800.0, (home_rating + 55.0 - away_rating) * math.log(10) / 400))
    decisive = 1.0 / (1.0 + math.exp(-diff))
    home = (1.0 - draw_base) * decisive
    away = (1.0 - draw_base) * (1.0 - decisive)
    return (home, draw_base, away)

def poisson_probs(lam, cap=10):
    lam = max(0.05, min(6.0, float(lam)))
    out = [math.exp(-lam)]
    for k in range(1, cap + 1):
        out.append(out[-1] * lam / k)
    total = sum(out)
    return [x / total for x in out]

def poisson_1x2(home_lam, away_lam):
    hp, ap = poisson_probs(home_lam), poisson_probs(away_lam)
    h = d = a = 0.0
    for i, pi in enumerate(hp):
        for j, pj in enumerate(ap):
            if i > j: h += pi * pj
            elif i == j: d += pi * pj
            else: a += pi * pj
    total = h + d + a
    return (h/total, d/total, a/total)

def score(p, actual):
    brier = sum((p[i] - (1 if LABELS[i] == actual else 0)) ** 2 for i in range(3))
    logloss = -math.log(max(1e-12, p[LABELS.index(actual)]))
    return brier, logloss

def metrics(rows, prefix):
    if not rows: return {"matches": 0, "accuracy": None, "brier": None, "log_loss": None}
    n = len(rows)
    return {
        "matches": n,
        "accuracy": round(sum(r[prefix+"_correct"] for r in rows)/n, 6),
        "brier": round(sum(r[prefix+"_brier"] for r in rows)/n, 6),
        "log_loss": round(sum(r[prefix+"_logloss"] for r in rows)/n, 6)
    }

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", default="output/openfootball/matches.csv")
    ap.add_argument("--out", default="output/openfootball/advanced")
    ap.add_argument("--min-history", type=int, default=5)
    ap.add_argument("--window", type=int, default=12)
    ap.add_argument("--elo-k", type=float, default=20.0)
    ap.add_argument("--odds-csv", default="", help="Optional permitted, timestamped odds CSV; never scraped by this script")
    args = ap.parse_args()
    if args.min_history < 1 or args.window < 1 or args.elo_k <= 0: ap.error("history/window must be positive and Elo K must be > 0")
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    with open(args.input, encoding="utf-8-sig", newline="") as f: source = list(csv.DictReader(f))
    source.sort(key=lambda r: (r.get("date",""), r.get("league_code",""), r.get("home_team",""), r.get("away_team","")))
    by_date = defaultdict(list)
    skipped = 0
    for r in source:
        try:
            date = (r.get("date") or "").strip()
            league = (r.get("league_code") or "").strip()
            home = (r.get("home_team") or "").strip()
            away = (r.get("away_team") or "").strip()
            hg, ag = float(r.get("home_goals","")), float(r.get("away_goals",""))
            if not date or not league or not home or not away or not math.isfinite(hg) or not math.isfinite(ag) or hg < 0 or ag < 0 or not hg.is_integer() or not ag.is_integer():
                raise ValueError()
            r["_date"], r["_league"], r["_home"], r["_away"], r["_hg"], r["_ag"] = date, league, home, away, int(hg), int(ag)
            by_date[date].append(r)
        except (ValueError, TypeError):
            skipped += 1
    ratings = defaultdict(lambda: 1500.0)
    played = defaultdict(int)
    hgf, hga, agf, aga = defaultdict(lambda: deque(maxlen=args.window)), defaultdict(lambda: deque(maxlen=args.window)), defaultdict(lambda: deque(maxlen=args.window)), defaultdict(lambda: deque(maxlen=args.window))
    league_h, league_a = defaultdict(lambda: deque(maxlen=100)), defaultdict(lambda: deque(maxlen=100))
    outcome_counts = defaultdict(lambda: [0,0,0])
    predictions, ledger = [], []
    # optional user-supplied odds must be dated and have decimal odds available pre-match.
    odds = {}
    odds_status = "not supplied; ROI and bookmaker comparison intentionally not computed"
    if args.odds_csv:
        with open(args.odds_csv, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                key = (row.get("date","").strip(), row.get("league_code","").strip(), row.get("home_team","").strip(), row.get("away_team","").strip())
                try:
                    vals = [float(row[k]) for k in ("home_odds","draw_odds","away_odds")]
                    captured = datetime.fromisoformat(row["captured_at_utc"].replace("Z", "+00:00"))
                    kickoff = datetime.fromisoformat(row["kickoff_at_utc"].replace("Z", "+00:00"))
                    if captured.tzinfo is None or kickoff.tzinfo is None or captured >= kickoff:
                        continue
                    if all(math.isfinite(v) and v > 1 for v in vals) and all(key):
                        odds[key] = {"values": vals, "captured_at_utc": captured.astimezone(timezone.utc).isoformat(), "kickoff_at_utc": kickoff.astimezone(timezone.utc).isoformat()}
                except (KeyError, ValueError, TypeError): continue
        odds_status = f"loaded {len(odds)} valid odds rows with timezone-aware capture timestamps earlier than kickoff"
    per_league = defaultdict(list)
    for date in sorted(by_date):
        updates = []
        for r in by_date[date]:
            league, home, away, hg, ag = r["_league"], r["_home"], r["_away"], r["_hg"], r["_ag"]
            hk, ak = (league, home), (league, away)
            actual = "H" if hg > ag else ("D" if hg == ag else "A")
            ready = played[hk] >= args.min_history and played[ak] >= args.min_history and len(league_h[league]) >= args.min_history
            if ready:
                # Elo forecast.
                elo_p = probs_from_ratings(ratings[hk], ratings[ak])
                # Shrunk rolling venue-specific goals forecast; league means anchor small samples.
                bh = sum(league_h[league])/len(league_h[league])
                ba = sum(league_a[league])/len(league_a[league])
                h_attack = (sum(hgf[hk])/len(hgf[hk]) if hgf[hk] else bh) / max(.1,bh)
                h_def = (sum(hga[hk])/len(hga[hk]) if hga[hk] else ba) / max(.1,ba)
                a_attack = (sum(agf[ak])/len(agf[ak]) if agf[ak] else ba) / max(.1,ba)
                a_def = (sum(aga[ak])/len(aga[ak]) if aga[ak] else bh) / max(.1,bh)
                hl = max(.15,min(4.5,bh*h_attack*a_def))
                al = max(.15,min(4.5,ba*a_attack*h_def))
                goal_p = poisson_1x2(hl, al)
                # Equal-weight ensemble is fixed before testing; no test-set tuning.
                ensemble = tuple((elo_p[i]+goal_p[i])/2 for i in range(3))
                counts = outcome_counts[league]; denom = sum(counts)+3
                baseline = tuple((counts[i]+1)/denom for i in range(3))
                pred = {"date":date,"season":r.get("season",""),"league_code":league,"home_team":home,"away_team":away,
                    "home_goals":hg,"away_goals":ag,"actual_1x2":actual,
                    "elo_p_home":round(elo_p[0],6),"elo_p_draw":round(elo_p[1],6),"elo_p_away":round(elo_p[2],6),
                    "poisson_p_home":round(goal_p[0],6),"poisson_p_draw":round(goal_p[1],6),"poisson_p_away":round(goal_p[2],6),
                    "ensemble_p_home":round(ensemble[0],6),"ensemble_p_draw":round(ensemble[1],6),"ensemble_p_away":round(ensemble[2],6),
                    "baseline_p_home":round(baseline[0],6),"baseline_p_draw":round(baseline[1],6),"baseline_p_away":round(baseline[2],6),
                    "predicted_1x2":LABELS[max(range(3),key=lambda i:ensemble[i])],"method":"fixed 50/50 Elo + rolling-goals Poisson; prior dates only"}
                for name, p in (("ensemble",ensemble),("baseline",baseline),("elo",elo_p),("poisson",goal_p)):
                    b,ll=score(p,actual); pred[name+"_brier"]=round(b,6); pred[name+"_logloss"]=round(ll,6); pred[name+"_correct"]=int(LABELS[max(range(3),key=lambda i:p[i])]==actual)
                predictions.append(pred); per_league[league].append(pred)
                # Paper ledger only where matching, valid decimal odds were explicitly supplied.
                key=(date,league,home,away)
                if key in odds:
                    odds_row=odds[key]; o=odds_row["values"]; implied=[1/x for x in o]; total=sum(implied); fair=[x/total for x in implied]
                    pick=max(range(3),key=lambda i:ensemble[i])
                    ledger.append({"date":date,"league_code":league,"home_team":home,"away_team":away,"actual_1x2":actual,
                        "home_odds":o[0],"draw_odds":o[1],"away_odds":o[2],"odds_captured_at_utc":odds_row["captured_at_utc"],"kickoff_at_utc":odds_row["kickoff_at_utc"],"model_probability":round(ensemble[pick],6),
                        "market_implied_probability_raw":round(implied[pick],6),"market_probability_no_vig":round(fair[pick],6),
                        "selection":LABELS[pick],"flat_stake_units":1,"paper_profit_units":round(o[pick]-1 if LABELS[pick]==actual else -1,4),
                        "warning":"retrospective paper test only; verify odds timestamp predates kickoff and account for limits/voids"})
            updates.append((league,hk,ak,hg,ag,actual))
        for league,hk,ak,hg,ag,actual in updates:
            # Elo updates occur only after the entire date has been predicted.
            expected=1/(1+10**((ratings[ak]-(ratings[hk]+55))/400))
            actual_home=1.0 if actual=="H" else (0.5 if actual=="D" else 0.0)
            change=args.elo_k*(actual_home-expected)
            ratings[hk]+=change; ratings[ak]-=change
            hgf[hk].append(hg); hga[hk].append(ag); agf[ak].append(ag); aga[ak].append(hg)
            league_h[league].append(hg); league_a[league].append(ag); outcome_counts[league][LABELS.index(actual)]+=1
            played[hk]+=1; played[ak]+=1
    fields=list(predictions[0]) if predictions else ["date","league_code","home_team","away_team","actual_1x2"]
    with open(out/"advanced_predictions.csv","w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(predictions)
    summary={"data_source":"OpenFootball fixtures/results","source_rows":len(source),"valid_scored_rows":sum(len(v) for v in by_date.values()),"backtested_matches":len(predictions),"skipped_invalid_rows":skipped,
        "same_date_leakage_control":"All fixtures on a calendar date predicted before any result that date updates Elo or form.",
        "models":{"fixed_elo_plus_poisson_ensemble":metrics(predictions,"ensemble"),"elo_only":metrics(predictions,"elo"),"poisson_only":metrics(predictions,"poisson"),"league_frequency_baseline":metrics(predictions,"baseline")},
        "per_league":{k:{"ensemble":metrics(v,"ensemble"),"elo":metrics(v,"elo"),"poisson":metrics(v,"poisson"),"baseline":metrics(v,"baseline")} for k,v in sorted(per_league.items())},
        "odds_status":odds_status,"paper_bet_count":len(ledger),"paper_profit_units":round(sum(x["paper_profit_units"] for x in ledger),4) if ledger else None,
        "paper_roi":round(sum(x["paper_profit_units"] for x in ledger)/len(ledger),6) if ledger else None,
        "limitations":["No player features are inferred from results-only data.","Odds ROI is omitted unless an odds CSV is explicitly supplied.","A retrospective paper ledger is not proof of live profitability; odds must be timestamped before kickoff.","Same-date fixtures are withheld together because kickoff times are absent.","Ensemble weights are fixed, not tuned on test outcomes."],
        "predictions_csv":str(out/"advanced_predictions.csv"),"paper_ledger_csv":str(out/"paper_betting_ledger.csv")}
    with open(out/"metrics.json","w",encoding="utf-8") as f: json.dump(summary,f,indent=2)
    with open(out/"paper_betting_ledger.csv","w",encoding="utf-8-sig",newline="") as f:
        cols=list(ledger[0]) if ledger else ["date","league_code","home_team","away_team","selection","home_odds","draw_odds","away_odds","paper_profit_units","warning"]
        w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(ledger)
    print(json.dumps(summary,indent=2))
    if not predictions: raise SystemExit("No eligible matches; no advanced model metrics produced.")

if __name__ == "__main__": main()
