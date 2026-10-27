#!/usr/bin/env python3
"""UFI live monitor. Review alerts only; never places bets or invents missing data."""
from __future__ import annotations
import json, os, re, sqlite3, smtplib, ssl, time, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage
from pathlib import Path

BACKEND=os.getenv("UFI_BACKEND_URL","https://universal-football-intelligence.onrender.com").rstrip("/")
STATE_DB=os.getenv("UFI_STATE_DB","ufi_brain_state.sqlite3")
KICKOFF_LEAD=int(os.getenv("UFI_KICKOFF_ALERT_MINUTES","10"))
LIVE_MIN=int(os.getenv("UFI_LIVE_MINUTE_MIN","10")); LIVE_MAX=int(os.getenv("UFI_LIVE_MINUTE_MAX","25"))
MIN_SOT=int(os.getenv("UFI_MIN_TOTAL_SHOTS_ON_TARGET","3"))
MIN_SHOTS=int(os.getenv("UFI_MIN_TOTAL_SHOTS","8"))
MIN_DANGER=int(os.getenv("UFI_MIN_TOTAL_DANGEROUS_ATTACKS","20"))
ODDS_MIN=float(os.getenv("UFI_TARGET_ODDS_MIN","1.18")); ODDS_MAX=float(os.getenv("UFI_TARGET_ODDS_MAX","1.25"))
BOOKMAKER=os.getenv("UFI_BOOKMAKER_ID","").strip(); MARKET=os.getenv("UFI_OVER05_HT_MARKET_ID","").strip()

def json_get(url, timeout=15):
    req=urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":"UFI-Autonomous-Brain/1.0"})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        if r.status!=200: raise RuntimeError("HTTP status %s"%r.status)
        return json.loads(r.read().decode()),time.time()

def get_backend(path): return json_get(BACKEND+path)

def unwrap_rows(payload):
    value=payload
    for _ in range(6):
        if isinstance(value,list): return [x for x in value if isinstance(x,dict)]
        if not isinstance(value,dict): return []
        if isinstance(value.get("data"),list): return [x for x in value["data"] if isinstance(x,dict)]
        value=next((value[k] for k in ("data","fixtures","events","results","response") if isinstance(value.get(k),(dict,list))),None)
        if value is None: return []
    return []

def first(*xs): return next((x for x in xs if x not in (None,"")),None)

def team_names(row):
    home=first(row.get("homeTeam"),row.get("home_team")); away=first(row.get("awayTeam"),row.get("away_team"))
    participants=row.get("participants") or row.get("teams") or []
    if isinstance(participants,list):
        for t in participants:
            if not isinstance(t,dict): continue
            name=first(t.get("name"),t.get("short_code"),t.get("shortName"))
            meta=t.get("meta") if isinstance(t.get("meta"),dict) else {}
            loc=str(meta.get("location","")).lower()
            if loc=="home" and not home: home=name
            if loc=="away" and not away: away=name
    elif isinstance(participants,dict):
        for side in ("home","away"):
            val=participants.get(side); name=val.get("name") if isinstance(val,dict) else val
            if side=="home" and not home: home=name
            if side=="away" and not away: away=name
    return str(home or "Unknown home"),str(away or "Unknown away")

def kickoff_datetime(row):
    raw=first(row.get("kickoff"),row.get("starting_at"),row.get("commence_time"),row.get("startTime"),row.get("startsAt"))
    if not isinstance(raw,str): return None
    try:
        dt=datetime.fromisoformat(raw.replace("Z","+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except ValueError: return None

def minute_score(row):
    status=row.get("status") if isinstance(row.get("status"),dict) else {}
    state=row.get("state") if isinstance(row.get("state"),dict) else {}
    clock=first(status.get("clock"),status.get("elapsed"),state.get("clock"),row.get("minute"),row.get("elapsed"))
    if isinstance(clock,dict): clock=first(clock.get("minute"),clock.get("elapsed"),clock.get("value"))
    if isinstance(clock,str):
        m=re.search(r"\d+",clock); clock=int(m.group()) if m else None
    try: minute=int(clock) if clock is not None else None
    except (TypeError,ValueError): minute=None
    home=away=None
    score=row.get("score")
    if isinstance(score,dict):
        home=first(score.get("home"),score.get("localteam_score")); away=first(score.get("away"),score.get("visitorteam_score"))
    scores=row.get("scores")
    if isinstance(scores,list) and (home is None or away is None):
        for item in scores:
            if not isinstance(item,dict): continue
            desc=str(first(item.get("description"),item.get("type"),"")).lower()
            if desc not in ("current","ft","full_time","full time","2nd_half","2nd half"): continue
            score_obj=item.get("score") if isinstance(item.get("score"),dict) else {}
            side=str(first(score_obj.get("participant"),item.get("participant"),"")).lower()
            val=first(score_obj.get("goals"),item.get("goals"))
            if side in ("home","localteam"): home=val
            if side in ("away","visitorteam","visitor"): away=val
    try: pair=(int(home),int(away)) if home is not None and away is not None else None
    except (TypeError,ValueError): pair=None
    return minute,pair

def flatten_stats(value,out=None):
    if out is None: out=[]
    if isinstance(value,dict):
        typ=str(first(value.get("type"),value.get("name"),value.get("developer_name"),"")).lower()
        val=first(value.get("value"),value.get("data"),value.get("total"))
        if typ and val is not None: out.append((re.sub(r"[^a-z]","",typ),val))
        for child in value.values():
            if isinstance(child,(dict,list)): flatten_stats(child,out)
    elif isinstance(value,list):
        for child in value: flatten_stats(child,out)
    return out

def extract_live_stats(row):
    pairs=flatten_stats(row.get("statistics")); result={}
    aliases={"sot":("shotsontarget","shotsongoal","shots_on_target","shots_on_goal"),
             "shots":("totalshots","shotstotal","total_shots","shots"),
             "danger":("dangerousattacks","dangerous_attacks")}
    for key,names in aliases.items():
        norms={re.sub(r"[^a-z]","",n) for n in names}; vals=[]
        for typ,val in pairs:
            if typ in norms:
                try:
                    if not (isinstance(val,str) and "%" in val): vals.append(float(val))
                except (ValueError,TypeError): pass
        result[key]=sum(vals) if vals else None
    return result

def odds_values(payload):
    found=[]
    def visit(v,ctx=""):
        if isinstance(v,dict):
            label=" ".join(str(v.get(k,"")) for k in ("name","label","market_name","marketName","description","outcome","selection","market"))
            price=first(v.get("decimal"),v.get("decimal_odds"),v.get("odds"),v.get("price"),v.get("value"))
            combined=(ctx+" "+label).lower()
            if price is not None and ("over 0.5" in combined or "over 0,5" in combined) and any(w in combined for w in ("half","1st","ht","first")):
                try:
                    p=float(price)
                    if p>1: found.append(p)
                except (ValueError,TypeError): pass
            for k,x in v.items():
                if isinstance(x,(dict,list)): visit(x,combined+" "+str(k))
        elif isinstance(v,list):
            for x in v: visit(x,ctx)
    visit(payload); return found

class StateStore:
    """Local SQLite state for testing; production needs a durable mounted DB."""
    def __init__(self,path):
        self.db=sqlite3.connect(path,timeout=10)
        self.db.execute("CREATE TABLE IF NOT EXISTS sent_alerts (alert_key TEXT PRIMARY KEY,sent_at TEXT NOT NULL)")
        self.db.execute("CREATE TABLE IF NOT EXISTS live_snapshots (fixture_id TEXT,captured_at TEXT,minute INTEGER,home_goals INTEGER,away_goals INTEGER,stats_json TEXT,odds_json TEXT,source TEXT)")
        self.db.commit()
    def seen(self,key): return self.db.execute("SELECT 1 FROM sent_alerts WHERE alert_key=?",(key,)).fetchone() is not None
    def mark(self,key):
        self.db.execute("INSERT OR IGNORE INTO sent_alerts VALUES (?,?)",(key,datetime.now(timezone.utc).isoformat())); self.db.commit()
    def snapshot(self,fid,minute,score,stats,odds,source):
        self.db.execute("INSERT INTO live_snapshots VALUES (?,?,?,?,?,?,?,?)",(str(fid),datetime.now(timezone.utc).isoformat(),minute,score[0] if score else None,score[1] if score else None,json.dumps(stats,sort_keys=True),json.dumps(odds) if odds is not None else None,source)); self.db.commit()
    def close(self): self.db.close()

def send_telegram(message):
    token=os.getenv("TELEGRAM_BOT_TOKEN","").strip(); chat=os.getenv("TELEGRAM_CHAT_ID","").strip()
    if not token or not chat: return False
    url="https://api.telegram.org/bot%s/sendMessage"%token
    req=urllib.request.Request(url,data=json.dumps({"chat_id":chat,"text":message,"disable_web_page_preview":True}).encode(),headers={"Content-Type":"application/json"},method="POST")
    try:
        with urllib.request.urlopen(req,timeout=12) as r: return bool(json.loads(r.read().decode()).get("ok"))
    except Exception as e: print("Telegram delivery failed:",type(e).__name__); return False

def send_email(subject,body):
    host=os.getenv("SMTP_HOST","").strip(); sender=os.getenv("SMTP_FROM","").strip(); recipient=os.getenv("ALERT_EMAIL_TO","").strip()
    if not host or not sender or not recipient: return False
    msg=EmailMessage(); msg["Subject"]=subject; msg["From"]=sender; msg["To"]=recipient; msg.set_content(body)
    try:
        with smtplib.SMTP(host,int(os.getenv("SMTP_PORT","587")),timeout=15) as s:
            s.starttls(context=ssl.create_default_context())
            user=os.getenv("SMTP_USERNAME","").strip()
            if user: s.login(user,os.getenv("SMTP_PASSWORD",""))
            s.send_message(msg)
        return True
    except Exception as e: print("Email delivery failed:",type(e).__name__); return False

def alert_once(store,key,subject,message):
    if store.seen(key): return False
    sent=send_telegram(message) or send_email(subject,message)
    if sent: store.mark(key)
    print(json.dumps({"alertKey":key,"delivered":sent}))
    return sent

def main():
    if not BACKEND.startswith("https://"): raise SystemExit("UFI_BACKEND_URL must use HTTPS")
    now=datetime.now(timezone.utc); store=StateStore(STATE_DB)
    counts={"fixtures":0,"live":0,"kickoffAlerts":0,"liveReviewAlerts":0,"snapshots":0,"errors":[]}
    try:
        dates=[now.date().isoformat(),(now.date()+timedelta(days=1)).isoformat()]
        tasks=[("/api/fixtures?date="+d,"fixtures") for d in dates]+[("/api/live","live")]
        for path,kind in tasks:
            try: payload,_=get_backend(path); rows=unwrap_rows(payload)
            except Exception as e: counts["errors"].append(path+": "+type(e).__name__); continue
            counts[kind]+=len(rows); source=str(payload.get("source","UFI backend")) if isinstance(payload,dict) else "UFI backend"
            for row in rows:
                home,away=team_names(row); fid=first(row.get("fixtureId"),row.get("id"),row.get("fixture_id"))
                kickoff=kickoff_datetime(row)
                if kind=="fixtures" and kickoff and fid is not None:
                    mins=(kickoff-now).total_seconds()/60
                    if 0<=mins<=KICKOFF_LEAD:
                        key="kickoff:%s:%s"%(fid,kickoff.isoformat())
                        msg="UFI KICKOFF WATCH (review only)\n%s vs %s\nKickoff in %.1f minutes (UTC %s).\nReview lineups, feed freshness and market terms in UFI. No automatic stake."%(home,away,mins,kickoff.strftime("%H:%M"))
                        if alert_once(store,key,"UFI kickoff watch: %s vs %s"%(home,away),msg): counts["kickoffAlerts"]+=1
                if kind!="live": continue
                minute,score=minute_score(row); stats=extract_live_stats(row); odds_payload=None
                if fid is not None and BOOKMAKER.isdigit() and MARKET.isdigit():
                    try: odds_payload,_=get_backend("/api/inplay-odds?id=%s&bookmaker=%s&market=%s"%(urllib.parse.quote(str(fid)),BOOKMAKER,MARKET))
                    except Exception as e: counts["errors"].append("odds %s: %s"%(fid,type(e).__name__))
                store.snapshot(fid if fid is not None else "unknown",minute,score,stats,odds_payload,source); counts["snapshots"]+=1
                if fid is None or minute is None or score!=(0,0) or not LIVE_MIN<=minute<=LIVE_MAX: continue
                pressure=(stats["sot"] is not None and stats["sot"]>=MIN_SOT) or (stats["shots"] is not None and stats["shots"]>=MIN_SHOTS and stats["danger"] is not None and stats["danger"]>=MIN_DANGER)
                prices=odds_values(odds_payload) if odds_payload is not None else []
                eligible=[p for p in prices if ODDS_MIN<=p<=ODDS_MAX]
                if not pressure or not eligible: continue
                key="live-over05ht:%s:%s"%(fid,minute)
                msg=("UFI LIVE MARKET REVIEW — NOT A BET INSTRUCTION\n%s vs %s | %s'\nScore: %s-%s\nStats: total SOT=%s; total shots=%s; dangerous attacks=%s\nObserved Over 0.5 first-half price(s): %s\nReview source timestamps, cards/VAR, and settlement terms. This experimental trigger is not validated as profitable; no automatic staking."%(home,away,minute,score[0],score[1],stats["sot"],stats["shots"],stats["danger"],", ".join("%.2f"%p for p in eligible)))
                if alert_once(store,key,"UFI live market review: %s vs %s"%(home,away),msg): counts["liveReviewAlerts"]+=1
        print(json.dumps({"ok":True,"runAtUtc":now.isoformat(),"counts":counts,"stateDb":STATE_DB,"note":"SQLite must be on persistent storage for scheduled deduplication and durable historical snapshots."},sort_keys=True))
    finally: store.close()

if __name__=="__main__": main()
