"""Public historical results loader for source-backed UFI goal-rate estimation."""
from __future__ import annotations
import csv, io, json, os, urllib.error, urllib.request
from datetime import date, datetime, timezone

LEAGUE_CODES={"E0","E1","E2","E3","SC0","SC1","SC2","SC3","D1","D2","I1","I2","SP1","SP2","F1","F2","N1","B1","P1","T1","G1"}

def _season_code(start_year: int) -> str:
    if start_year >= 2000:
        return f"{start_year % 100:02d}{(start_year+1) % 100:02d}"
    return f"{start_year % 100:02d}{(start_year+1) % 100:02d}"

def _parse_date(value: str) -> str | None:
    value=(value or "").strip()
    for fmt in ("%d/%m/%y","%d/%m/%Y","%Y-%m-%d"):
        try:return datetime.strptime(value,fmt).date().isoformat()
        except ValueError:pass
    return None

def load_football_data_results(league_code: str, seasons: int=5, timeout: float=8.0) -> dict:
    league=str(league_code or "").strip().upper()
    if league not in LEAGUE_CODES:
        raise ValueError("Unsupported football-data league code. Choose a code from the supported list.")
    try: seasons=max(1,min(8,int(seasons)))
    except (TypeError,ValueError): seasons=5
    today=date.today()
    current_start=today.year if today.month>=7 else today.year-1
    records=[]; urls=[]; issues=[]
    for offset in range(seasons):
        code=_season_code(current_start-offset)
        url=f"https://www.football-data.co.uk/mmz4281/{code}/{league}.csv"
        req=urllib.request.Request(url,headers={"Accept":"text/csv,*/*","User-Agent":"UFI-Historical-Results/1.0"})
        try:
            with urllib.request.urlopen(req,timeout=timeout) as response:
                raw=response.read().decode("utf-8-sig","replace")
            reader=csv.DictReader(io.StringIO(raw))
            if not reader.fieldnames or not {"Date","HomeTeam","AwayTeam","FTHG","FTAG"}.issubset(set(reader.fieldnames)):
                issues.append({"season":code,"reason":"CSV schema unavailable"});continue
            count=0
            for row in reader:
                match_date=_parse_date(row.get("Date",""))
                try:
                    hg=int(float(row.get("FTHG","")));ag=int(float(row.get("FTAG","")))
                except (TypeError,ValueError,OverflowError):continue
                home=(row.get("HomeTeam") or "").strip();away=(row.get("AwayTeam") or "").strip()
                if not match_date or not home or not away or hg<0 or ag<0:continue
                records.append({"date":match_date,"home_team":home,"away_team":away,"home_goals":hg,"away_goals":ag,"season":code,"source_url":url})
                count+=1
            if count:urls.append(url)
            else:issues.append({"season":code,"reason":"No usable match rows"})
        except (urllib.error.URLError,urllib.error.HTTPError,TimeoutError,UnicodeError) as exc:
            issues.append({"season":code,"reason":type(exc).__name__})
    records.sort(key=lambda x:x["date"])
    return {"ok":bool(records),"source":"Football-Data.co.uk public historical results",
            "league_code":league,"requested_seasons":seasons,"seasons_loaded":sorted({r["season"] for r in records}),
            "fetched_at":datetime.now(timezone.utc).isoformat(),"record_count":len(records),
            "source_urls":urls,"issues":issues,"data":records,
            "note":"Full-time results only; no xG, lineups, injuries, tracking or calibration. These rows support a baseline rate estimate, not a proven betting edge."}
