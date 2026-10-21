from dfs_optimizer.src.statsbomb_player_stats import events_to_player_rows

def test_event_adapter_counts_passes_interceptions_and_shots():
    lineups=[
      {"team_name":"Home","lineup":[{"player_id":1,"player_name":"H1","positions":[{"position":{"name":"Center Back"}}]}]},
      {"team_name":"Away","lineup":[{"player_id":2,"player_name":"A1","positions":[{"position":{"name":"Goalkeeper"}}]}]},
    ]
    events=[
      {"id":"s1","type":{"name":"Starting XI"},"team":{"name":"Home"},"tactics":{"lineup":[{"player":{"id":1,"name":"H1"},"position":{"name":"Center Back"}}]}},
      {"id":"s2","type":{"name":"Starting XI"},"team":{"name":"Away"},"tactics":{"lineup":[{"player":{"id":2,"name":"A1"},"position":{"name":"Goalkeeper"}}]}},
      {"id":"p1","type":{"name":"Pass"},"player":{"id":1,"name":"H1"},"team":{"name":"Home"},"pass":{"shot_assist":True}},
      {"id":"i1","type":{"name":"Interception"},"player":{"id":1,"name":"H1"},"team":{"name":"Home"}},
      {"id":"sh1","type":{"name":"Shot"},"player":{"id":1,"name":"H1"},"team":{"name":"Home"},"shot":{"outcome":{"name":"Goal"},"type":{"name":"Open Play"}}},
      {"id":"du1","type":{"name":"Duel"},"player":{"id":1,"name":"H1"},"team":{"name":"Home"},"duel":{"type":{"name":"Aerial"},"outcome":{"name":"Won"}}},
      {"id":"psh1","type":{"name":"Shot"},"player":{"id":1,"name":"H1"},"team":{"name":"Home"},"shot":{"outcome":{"name":"Saved"},"type":{"name":"Penalty"}}},
      {"id":"gk1","type":{"name":"Goal Keeper"},"player":{"id":2,"name":"A1"},"team":{"name":"Away"},"goalkeeper":{"type":{"name":"Shot Saved"}},"related_events":["psh1"]},
      {"id":"sub1","type":{"name":"Half End"},"minute":90,"second":0},
    ]
    match={"match_id":10,"match_date":"2026-01-01","home_score":1,"away_score":0,
           "home_team":{"home_team_name":"Home"},"away_team":{"away_team_name":"Away"}}
    rows=events_to_player_rows(events,lineups,match)
    h=next(r for r in rows if r["player_id"]=="1")
    assert h["completed_passes"]==1
    assert h["interceptions_won"]==1
    assert h["goals"]==1
    assert h["shots_on_target"]==2
    assert h["chances_created"]==1

    assert h["aerial_wins"] == 1
    assert h["aerial_duels"] == 1
    gk=next(r for r in rows if r["player_id"]=="2")
    assert gk["penalties_faced"] == 1
    assert gk["penalties_saved"] == 1
