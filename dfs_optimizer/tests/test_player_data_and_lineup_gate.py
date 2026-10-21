from datetime import datetime, timezone, timedelta
import io
from dfs_optimizer.src.player_data import read_player_stats_csv, build_player_projections
from dfs_optimizer.src.lineup_gate import validate_confirmed_lineup

def test_player_stats_parser_and_projection_features():
    text = "player_id,player_name,team,position,match_date,minutes,started,completed_passes,interceptions_won,yellow_cards,aerial_wins,aerial_duels,penalty_attempts,penalties_scored\n"
    text += "p1,Player One,A,DEF,2026-01-01,90,1,80,3,0,4,5,1,1\n"
    text += "p1,Player One,A,DEF,2026-01-08,90,1,100,4,1,3,5,0,0\n"
    result=read_player_stats_csv(io.StringIO(text))
    assert result["rows_valid"] == 2
    profile=build_player_projections(result["rows"])["profiles"][0]
    assert profile["interceptions_per90"] == 3.5
    assert profile["completed_passes_per90"] == 90
    assert 0 < profile["penalty_conversion_posterior"] <= 1
    assert profile["aerial_win_rate"] > 0.5

def test_lineup_gate_requires_fresh_official_xis():
    now=datetime(2026,10,21,12,0,tzinfo=timezone.utc)
    kickoff=(now+timedelta(minutes=60)).isoformat()
    confirmed=(now-timedelta(minutes=5)).isoformat()
    rows=[]
    for team in ("A","B"):
        for i in range(11):
            rows.append({"fixture_id":"fx1","kickoff_utc":kickoff,"confirmed_at_utc":confirmed,
                         "player_id":f"{team}{i}","player_name":f"{team} Player {i}","team":team,
                         "position":"DEF","salary":"10","status":"confirmed","starting":"true"})
    result=validate_confirmed_lineup(rows,now=now)
    assert result["ready"] is True
    stale=[dict(r,confirmed_at_utc=(now-timedelta(hours=3)).isoformat()) for r in rows]
    assert validate_confirmed_lineup(stale,now=now)["ready"] is False

def test_lineup_gate_rejects_missing_starters():
    now=datetime(2026,10,21,12,0,tzinfo=timezone.utc)
    rows=[{"fixture_id":"fx1","kickoff_utc":(now+timedelta(minutes=60)).isoformat(),
           "confirmed_at_utc":now.isoformat(),"player_id":"a","player_name":"A","team":"A",
           "position":"DEF","salary":"10","status":"confirmed","starting":"true"}]
    assert not validate_confirmed_lineup(rows,now=now)["ready"]
