import json
from pathlib import Path
from dfs_optimizer.src import data_acquisition

def test_statsbomb_event_download_wrapper_is_opt_in_and_manifested(tmp_path, monkeypatch):
    out=tmp_path/"competition_9_season_281"
    out.mkdir()
    match={"match_id":123,"match_date":"2024-01-01","home_team":{"home_team_name":"A"},
           "away_team":{"away_team_name":"B"},"home_score":1,"away_score":0}
    (out/"matches.json").write_text(json.dumps([match]),encoding="utf-8")
    (out/"source_manifest.json").write_text(json.dumps({"source":"StatsBomb Open Data"}),encoding="utf-8")
    monkeypatch.setattr(data_acquisition,"download_season",lambda *a,**k:{"directory":str(out),"manifest":{"source":"StatsBomb Open Data"}})
    monkeypatch.setattr(data_acquisition,"fetch_json",lambda url: [{"type":{"name":"test"}}] if "/events/" in url else [])
    result=data_acquisition.download_season_with_events("9","281",str(tmp_path),max_matches=1,delay=0)
    assert result["manifest"]["event_files_downloaded"]==1
    assert result["manifest"]["lineup_files_downloaded"]==1
    assert (out/"events"/"123.json").exists()
    assert (out/"lineups"/"123.json").exists()
    saved=json.loads((out/"source_manifest.json").read_text(encoding="utf-8"))
    assert saved["event_files_downloaded"]==1
