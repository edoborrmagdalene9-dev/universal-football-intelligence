"""Public historical results loader for source-backed UFI goal-rate estimation.

Season downloads run concurrently with bounded per-request timeouts so a single
slow season does not serially delay the whole prediction request.
"""
from __future__ import annotations
import csv, io, os, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone

LEAGUE_CODES={"E0","E1","E2","E3","SC0","SC1","SC2","SC3","D1","D2","I1","I2","SP1","SP2","F1","F2","N1","B1","P1","T1","G1"}

def _season_code(start_year: int) -> str:
    return f"{start_year % 100:02d}{(start_year+1) % 100:02d}"

def _parse_date(value: str) -> str | None:
    value=(value or "").strip()
    for fmt in ("%d/%m/%y","%d/%m/%Y","%Y-%m-%d"):
        try:return datetime.strptime(value,fmt).date().isoformat()
        except ValueError:pass
    return None

def _load_one_season(league: str, code: str, timeout: float) -> dict:
    url=f"https://www.football-data.co.uk/mmz4281/{code}/{league}.csv"
    req=urllib.request.Request(url,headers={"Accept":"text/csv,*/*","User-Agent":"UFI-Historical-Results/1.0"})
    try:
        with urllib.request.urlopen(req,timeout=timeout) as response:
            raw=response.read().decode("utf-8-sig","replace")
        reader=csv.DictReader(io.StringIO(raw))
        if not reader.fieldnames or not {"Date","HomeTeam","AwayTeam","FTHG","FTAG"}.issubset(set(reader.fieldnames)):
            return {"season":code,"records":[],"url":None,"issue":{"season":code,"reason":"CSV schema unavailable"}}
        records=[]
        for row in reader:
            match_date=_parse_date(row.get("Date",""))
            try:
                hg=int(float(row.get("FTHG","")));ag=int(float(row.get("FTAG","")))
            except (TypeError,ValueError,OverflowError):continue
            home=(row.get("HomeTeam") or "").strip();away=(row.get("AwayTeam") or "").strip()
            if not match_date or not home or not away or hg<0 or ag<0:continue
            records.append({"date":match_date,"home_team":home,"away_team":away,"home_goals":hg,"away_goals":ag,"season":code,"source_url":url})
        if records:
            return {"season":code,"records":records,"url":url,"issue":None}
        return {"season":code,"records":[],"url":None,"issue":{"season":code,"reason":"No usable match rows"}}
    except (urllib.error.URLError,urllib.error.HTTPError,TimeoutError,UnicodeError) as exc:
        return {"season":code,"records":[],"url":None,"issue":{"season":code,"reason":type(exc).__name__}}

def load_football_data_results(league_code: str, seasons: int=5, timeout: float=8.0) -> dict:
    league=str(league_code or "").strip().upper()
    if league not in LEAGUE_CODES:
        raise ValueError("Unsupported football-data league code. Choose a code from the supported list.")
    try: seasons=max(1,min(8,int(seasons)))
    except (TypeError,ValueError): seasons=5
    try: timeout=max(1.0,min(12.0,float(timeout)))
    except (TypeError,ValueError): timeout=8.0
    today=date.today()
    current_start=today.year if today.month>=7 else today.year-1
    codes=[_season_code(current_start-offset) for offset in range(seasons)]
    # Bounded parallel requests turn N sequential timeouts into approximately
    # one timeout window while keeping outbound concurrency low and predictable.
    results=[]
    with ThreadPoolExecutor(max_workers=min(4,len(codes))) as pool:
        futures=[pool.submit(_load_one_season,league,code,timeout) for code in codes]
        for future in as_completed(futures):
            try: results.append(future.result())
            except Exception as exc:
                # Fail one season independently; preserve usable results from others.
                results.append({"season":"unknown","records":[],"url":None,
                                "issue":{"season":"unknown","reason":type(exc).__name__}})
    records=[row for result in results for row in result["records"]]
    records.sort(key=lambda x:(x["date"],x["home_team"],x["away_team"]))
    urls=sorted({result["url"] for result in results if result.get("url")})
    issues=[result["issue"] for result in results if result.get("issue")]
    return {"ok":bool(records),"source":"Football-Data.co.uk public historical results",
            "league_code":league,"requested_seasons":seasons,"seasons_loaded":sorted({r["season"] for r in records}),
            "fetched_at":datetime.now(timezone.utc).isoformat(),"record_count":len(records),
            "source_urls":urls,"issues":issues,"data":records,
            "note":"Full-time results only; no xG, lineups, injuries, tracking or calibration. These rows support a baseline rate estimate, not a proven betting edge. Season downloads are concurrent and each request has a bounded timeout."}
