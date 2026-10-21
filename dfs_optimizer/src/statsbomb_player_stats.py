"""Convert local StatsBomb Open Data match/event/lineup JSON into canonical player-match CSV.

The open dataset is selected historical coverage, not a live feed. Aggregations are
explicit proxies; on-field goals-conceded and some keeper/card edge cases need
provider-specific verification before production use.
"""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path
from collections import defaultdict

ON_TARGET = {"Goal", "Saved", "Saved to Post", "Saved Off T"}
def _name(obj):
    return obj.get("name") if isinstance(obj, dict) else None
def _id(obj):
    return str(obj.get("id")) if isinstance(obj, dict) and obj.get("id") is not None else None
def _minute(event):
    try: return max(0.0,float(event.get("minute",0) or 0)+float(event.get("second",0) or 0)/60)
    except (TypeError,ValueError): return 0.0
def _players_from_lineups(data):
    players={}
    for team in data if isinstance(data,list) else []:
        team_name=team.get("team_name") or _name(team.get("team"))
        for p in team.get("lineup",[]) or []:
            pid=str(p.get("player_id") or p.get("id") or "")
            if not pid: continue
            positions=p.get("positions") or []
            pos=_name(positions[0].get("position")) if positions and isinstance(positions[0],dict) else ""
            players[pid]={"player_id":pid,"player_name":p.get("player_name") or p.get("name") or pid,
                          "team":team_name or "UNKNOWN","position":pos or "UNK"}
    return players
def events_to_player_rows(events, lineups, match):
    players=_players_from_lineups(lineups)
    by_event_id={str(e.get("id")):e for e in events if e.get("id")}
    starts=set()
    substitutions={}
    max_minute=max((_minute(e) for e in events),default=90.0)
    match_minutes=max(90.0,max_minute)
    for e in events:
        typ=_name(e.get("type"))
        if typ=="Starting XI":
            team=_name(e.get("team"))
            for p in (e.get("tactics") or {}).get("lineup",[]) or []:
                pobj=p.get("player") or {}
                pid=_id(pobj)
                if not pid: continue
                starts.add(pid)
                players.setdefault(pid,{"player_id":pid,"player_name":_name(pobj) or pid,
                                       "team":team or "UNKNOWN","position":_name(p.get("position")) or "UNK"})
        elif typ=="Substitution":
            off=_id(e.get("player")); replacement=_id((e.get("substitution") or {}).get("replacement"))
            minute=_minute(e)
            if off: substitutions[off]=minute
            if replacement:
                substitutions.setdefault(replacement,0.0)
                obj=e.get("substitution",{}).get("replacement",{})
                players.setdefault(replacement,{"player_id":replacement,"player_name":_name(obj) or replacement,
                                                "team":_name(e.get("team")) or "UNKNOWN","position":_name(e.get("position")) or "UNK"})
    stats=defaultdict(lambda:defaultdict(float))
    def stat(pid,key,n=1): 
        if pid: stats[pid][key]+=n
    for pid in players:
        stats[pid]["started"]=1 if pid in starts else 0
    for e in events:
        typ=_name(e.get("type")); pid=_id(e.get("player")); team=_name(e.get("team"))
        if pid and pid not in players:
            players[pid]={"player_id":pid,"player_name":_name(e.get("player")) or pid,
                          "team":team or "UNKNOWN","position":_name(e.get("position")) or "UNK"}
        if typ=="Pass" and pid:
            if not (e.get("pass") or {}).get("outcome"): stat(pid,"completed_passes")
            if (e.get("pass") or {}).get("shot_assist"): stat(pid,"chances_created")
        elif typ=="Interception" and pid: stat(pid,"interceptions_won")
        elif typ=="Duel" and pid:
            duel = e.get("duel") or {}
            duel_type = _name(duel.get("type")) or ""
            duel_outcome = _name(duel.get("outcome")) or ""
            if "Aerial" in duel_type:
                stat(pid,"aerial_duels")
                if "Won" in duel_type or duel_outcome == "Won":
                    stat(pid,"aerial_wins")
            if duel_type == "Tackle" and duel_outcome == "Won":
                stat(pid,"tackles_won")
        elif typ=="Shot" and pid:
            shot=e.get("shot") or {}; outcome=_name(shot.get("outcome")); shot_type=_name(shot.get("type"))
            is_goal=outcome=="Goal" and shot_type!="Own Goal"
            if outcome in ON_TARGET: stat(pid,"shots_on_target")
            pattern = _name(e.get("play_pattern")) or ""
            if pattern in {"From Corner", "From Free Kick"}: stat(pid,"set_piece_shots")
            if is_goal: stat(pid,"goals")
            if shot_type=="Penalty":
                stat(pid,"penalty_attempts")
                if is_goal: stat(pid,"penalties_scored")
                else: stat(pid,"penalties_missed")
                home_name = match.get("home_team",{}).get("home_team_name") or match.get("home_team",{}).get("name")
                away_name = match.get("away_team",{}).get("away_team_name") or match.get("away_team",{}).get("name")
                opponent_team = away_name if team == home_name else home_name
                keeper_id = next((k for k,v in players.items()
                                  if v.get("team") == opponent_team and "goalkeeper" in str(v.get("position","")).lower()), None)
                if keeper_id: stat(keeper_id,"penalties_faced")
            key_id=shot.get("key_pass_id")
            if key_id and str(key_id) in by_event_id:
                assist_event=by_event_id[str(key_id)]
                stat(_id(assist_event.get("player")),"assists")
        elif typ=="Goal Keeper" and pid:
            keeper=e.get("goalkeeper") or {}
            outcome=_name(keeper.get("type")) or _name(keeper.get("outcome"))
            if outcome and ("Saved" in outcome or "Collected" in outcome): stat(pid,"saves")
            related=e.get("related_events") or []
            if any(_name((by_event_id.get(str(r),{}).get("shot") or {}).get("type"))=="Penalty" for r in related):
                stat(pid,"penalties_saved")
        elif typ in {"Foul Committed","Bad Behaviour"} and pid:
            card=_name((e.get("foul_committed") or {}).get("card")) or _name((e.get("bad_behaviour") or {}).get("card"))
            if card and "Yellow" in card: stat(pid,"yellow_cards")
            if card and "Red" in card: stat(pid,"red_cards")
        elif typ=="Own Goal Against":
            # The player responsible is not consistently named on this event.
            if pid: stat(pid,"own_goals")
    # Approximate minutes from starting/substitution events; never imply tracking precision.
    for pid,p in players.items():
        if pid in starts:
            mins=substitutions.get(pid,match_minutes)
        elif pid in substitutions and substitutions[pid]==0:
            mins=max(0.0,match_minutes-next((_minute(e) for e in events if _name(e.get("type"))=="Substitution" and _id((e.get("substitution") or {}).get("replacement"))==pid),0.0))
        else: mins=0.0
        stats[pid]["minutes"]=mins
        if mins<=0: stats[pid]["started"]=0
    # Team score-based goals conceded is a match-level proxy, not exact on-field concession.
    hs=match.get("home_score"); aws=match.get("away_score")
    home=match.get("home_team",{}).get("home_team_name") or match.get("home_team",{}).get("name")
    away=match.get("away_team",{}).get("away_team_name") or match.get("away_team",{}).get("name")
    for pid,p in players.items():
        if p["team"]==home: conceded=aws or 0
        elif p["team"]==away: conceded=hs or 0
        else: conceded=0
        stats[pid]["goals_conceded"]=float(conceded) if stats[pid]["minutes"]>0 else 0.0
    date=match.get("match_date","")
    rows=[]
    for pid,p in players.items():
        row={"player_id":pid,"player_name":p["player_name"],"team":p["team"],"position":p["position"],
             "match_date":date,"fixture_id":str(match.get("match_id","")),
             "minutes":round(stats[pid]["minutes"],2),"started":int(stats[pid]["started"])}
        for k in ("goals","assists","shots_on_target","chances_created","completed_passes","interceptions_won",
                  "tackles_won","goals_conceded","saves","penalties_saved","yellow_cards","red_cards",
                  "own_goals","penalties_missed","penalty_attempts","penalties_scored"):
            row[k]=int(stats[pid][k])
        row.update({"aerial_wins":int(stats[pid]["aerial_wins"]),\n                    "aerial_duels":int(stats[pid]["aerial_duels"]),\n                    "set_piece_shots":int(stats[pid]["set_piece_shots"]),\n                    "penalties_faced":int(stats[pid]["penalties_faced"])})
        rows.append(row)
    return rows

def convert_directory(root, output):
    root=Path(root); output=Path(output)
    matches=[]
    for match_file in root.rglob("matches.json"):
        try: data=json.loads(match_file.read_text(encoding="utf-8"))
        except (OSError,json.JSONDecodeError): continue
        if isinstance(data,list): matches.extend(data)
    # Also accept season-local files named competition_<id>_season_<id>/matches.json.
    match_by_id={str(m.get("match_id")):m for m in matches if m.get("match_id") is not None}
    event_files=list(root.rglob("events/*.json"))
    rows=[]; skipped=[]
    for event_file in event_files:
        mid=event_file.stem
        lineup_file=event_file.parent.parent/"lineups"/f"{mid}.json"
        match=match_by_id.get(mid)
        if not match or not lineup_file.exists():
            skipped.append({"match_id":mid,"reason":"missing match metadata or lineup file"}); continue
        try:
            events=json.loads(event_file.read_text(encoding="utf-8"))
            lineups=json.loads(lineup_file.read_text(encoding="utf-8"))
            rows.extend(events_to_player_rows(events,lineups,match))
        except (OSError,json.JSONDecodeError,TypeError,ValueError) as exc:
            skipped.append({"match_id":mid,"reason":str(exc)})
    if rows:
        output.parent.mkdir(parents=True,exist_ok=True)
        fields=["player_id","player_name","team","position","match_date","fixture_id","minutes","started",
                "goals","assists","shots_on_target","chances_created","completed_passes","interceptions_won",
                "tackles_won","goals_conceded","saves","penalties_saved","yellow_cards","red_cards","own_goals",
                "penalties_missed","aerial_wins","aerial_duels","set_piece_shots","penalty_attempts","penalties_scored","penalties_faced"]
        with output.open("w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    return {"output":str(output),"matches_found":len(event_files),"player_match_rows":len(rows),"skipped":skipped,
            "warning":"StatsBomb event aggregation is historical and partial. Aerial metrics are left blank/zero where unavailable; goals conceded are team-score proxies, not exact on-field values. Review provider definitions and sample coverage."}

def main(argv=None):
    p=argparse.ArgumentParser(description="Convert local StatsBomb events and lineups to player-match stats CSV")
    p.add_argument("--data-root",default="data/external/statsbomb")
    p.add_argument("--output",default="data/external/statsbomb/player_match_stats.csv")
    a=p.parse_args(argv)
    print(json.dumps(convert_directory(a.data_root,a.output),indent=2))
if __name__=="__main__": main()
