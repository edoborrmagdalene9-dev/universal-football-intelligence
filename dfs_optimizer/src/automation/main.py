"""Local CLI for validating player projections and generating a lineup CSV.

This is an offline-first entry point. Live/confirmed lineups require a permitted,
configured data provider; no credentials or scraping are silently assumed.
"""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path
from ..scoring_engine import expected_points
from ..optimizer.pulp_optimizer import optimize_lineup

def main(argv=None):
    parser = argparse.ArgumentParser(description="FantasyFi DFS optimizer")
    parser.add_argument("--players", required=True, help="CSV with id,team,position,salary and projection or expected-stat columns")
    parser.add_argument("--output", default="fantasyfi_entries.csv")
    parser.add_argument("--roster-size", type=int, required=True)
    parser.add_argument("--salary-cap", type=float, required=True)
    parser.add_argument("--positions-json", required=True, help='JSON object e.g. {"GK":1,"DEF":3,"MID":3,"FWD":2}')
    parser.add_argument("--team-cap", type=int)
    args = parser.parse_args(argv)
    rows = []
    with open(args.players, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            row["salary"] = float(row["salary"])
            row["ownership"] = float(row.get("ownership") or 0)
            row["projection"] = float(row["projection"]) if row.get("projection") else expected_points(
                {k: float(v) for k,v in row.items() if k.startswith(("x","expected_","clean_sheet_","appearance_","start_","probability_")) and v not in ("",None)},
                row["position"])
            rows.append(row)
    slots = json.loads(args.positions_json)
    result = optimize_lineup(rows, args.roster_size, args.salary_cap, slots, args.team_cap)
    lookup = {str(r["id"]):r for r in rows}
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["entry_id","player_id","team","position","salary","projection"])
        writer.writeheader()
        for player_id in result["players"]:
            r=lookup[player_id]
            writer.writerow({"entry_id":"lineup_1","player_id":player_id,"team":r["team"],"position":r["position"],"salary":r["salary"],"projection":r["projection"]})
    print(json.dumps({**result,"output":str(Path(args.output).resolve())}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
