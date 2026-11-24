"""Additional UFI provider adapters. Secrets are read only from server environment variables.
No provider key is embedded in code, responses, logs, or browser-facing configuration.
"""
from __future__ import annotations
import json, os, time, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timezone
try:
    from .ufi_match_context import normalize_provider_payload
except ImportError:
    from ufi_match_context import normalize_provider_payload

class AdapterError(Exception):
    pass

_CACHE = {}
_TTLS = {"sgo": 600, "odds": 90, "sharp": 120, "weatherapi": 1800}
def _cached(key, ttl, fn):
    now=time.time()
    item=_CACHE.get(key)
    if item and now-item[0] < ttl:
        return item[1], True
    value=fn()
    _CACHE[key]=(now,value)
    return value, False

def _get_json(url, headers=None, timeout=12):
    req=urllib.request.Request(url, headers={"Accept":"application/json","User-Agent":"UFI-research/1.0", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body=response.read().decode("utf-8")
            payload=json.loads(body)
            return payload, dict(response.headers.items())
    except urllib.error.HTTPError as exc:
        # Never include the URL in the error; query strings may contain credentials.
        # Providers often return the actionable invalid-parameter reason in JSON.
        detail=""
        try:
            raw=exc.read(2048).decode("utf-8","replace")
            parsed=json.loads(raw)
            if isinstance(parsed,dict):
                detail=parsed.get("error") or parsed.get("message") or parsed.get("detail") or ""
            elif isinstance(parsed,str):
                detail=parsed
        except Exception:
            detail=""
        # Some providers return non-text error flags (for example {"error": true}).
        # Do not turn a boolean into a misleading human-readable diagnostic.
        if not isinstance(detail,str):
            detail=""
        if detail:
            for secret_name in ("SPORTSGAMEODDS_API_KEY","THE_ODDS_API_KEY","SHARPAPI_KEY","WEATHERAPI_KEY","SPORTMONKS_API_TOKEN"):
                secret=os.getenv(secret_name,"").strip()
                if secret: detail=str(detail).replace(secret,"[redacted]")
            detail=" ".join(str(detail).split())[:240]
            raise AdapterError("Provider returned HTTP %s: %s" % (exc.code,detail)) from exc
        raise AdapterError("Provider returned HTTP %s; verify credentials, endpoint, coverage and quota." % exc.code) from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise AdapterError("Provider unavailable: %s" % type(exc).__name__) from exc

def _query_url(base, params):
    return base.rstrip("/") + "?" + urllib.parse.urlencode({k:v for k,v in params.items() if v is not None and str(v)!=""})

def _odds_api(sport, query):
    key=os.getenv("THE_ODDS_API_KEY","").strip()
    if not key: raise AdapterError("THE_ODDS_API_KEY is not configured on the server.")
    # Use only documented V4 query parameters; one market per request minimizes quota use.
    markets=(query.get("markets") or ["h2h"])[0]
    regions=(query.get("regions") or ["uk"])[0]
    params={"apiKey":key,"regions":regions,"markets":markets,"oddsFormat":"decimal",
            "dateFormat":"iso","commenceTimeFrom":(query.get("from") or [None])[0],
            "commenceTimeTo":(query.get("to") or [None])[0]}
    base=os.getenv("THE_ODDS_API_BASE_URL","https://api.the-odds-api.com/v4/sports").strip().rstrip("/")
    url=base+"/"+urllib.parse.quote(sport,safe="_")+"/odds"
    cachekey="odds:"+sport+":"+urllib.parse.urlencode({k:v for k,v in params.items() if k!="apiKey"})
    response,hit=_cached(cachekey,_TTLS["odds"],lambda:_get_json(_query_url(url,params)))
    # _get_json returns (JSON payload, response headers). Unwrap it here so
    # normalizers receive the actual event list rather than a tuple.
    if isinstance(response,tuple) and len(response)==2:
        payload,headers=response
    else:
        payload,headers=response,{}
    header_map={str(k).lower():v for k,v in (headers or {}).items()}
    remaining=header_map.get("x-requests-remaining")
    used=header_map.get("x-requests-used")
    last=header_map.get("x-requests-last")
    return {"ok":True,"source":"The Odds API","sport":sport,"fetchedAt":time.time(),"cacheHit":hit,
            "quota":{"remaining":int(remaining) if str(remaining or "").isdigit() else None,
                     "used":int(used) if str(used or "").isdigit() else None,
                     "lastRequest":last,
                     "note":"Usage headers are provider-reported when present; otherwise inspect the account dashboard."},
            "data":payload}

def _sgo_events(query):
    key=os.getenv("SPORTSGAMEODDS_API_KEY","").strip()
    if not key: raise AdapterError("SPORTSGAMEODDS_API_KEY is not configured on the server.")
    # The API documents leagueID as taking precedence over sportID. Send only
    # one of these filters: some API gateway/schema versions reject both together.
    # The supplied plan page lists MLS among the entry-level leagues, while
    # the live API explicitly rejects EPL for this account's current tier.
    # Default to a verified accessible soccer league; honor explicit leagueID.
    league=(query.get("leagueID") or ["MLS"])[0].strip()
    sport=(query.get("sportID") or ["SOCCER"])[0].strip()
    # Match the provider's documented v2/events request shape: explicitly
    # disable alternate lines for the smallest, cheapest default response.
    params={"leagueID":league,
            "oddsAvailable":(query.get("oddsAvailable") or ["true"])[0],
            "includeAltLines":(query.get("includeAltLines") or ["false"])[0],
            "limit":min(100,max(1,int((query.get("limit") or ["1"])[0])))}
    if not league:
        params.pop("leagueID",None)
        params["sportID"]=sport or "SOCCER"
    if (query.get("live") or [""])[0]: params["live"]=(query.get("live") or [""])[0]
    if (query.get("started") or [""])[0]: params["started"]=(query.get("started") or [""])[0]
    if (query.get("eventID") or [""])[0]: params["eventID"]=(query.get("eventID") or [""])[0]
    url="https://api.sportsgameodds.com/v2/events"
    cachekey="sgo:"+urllib.parse.urlencode(params)
    payload,hit=_cached(cachekey,_TTLS["sgo"],lambda:_get_json(_query_url(url,params),{"X-Api-Key":key})[0])
    return {"ok":True,"source":"SportsGameOdds","fetchedAt":time.time(),"cacheHit":hit,
            "cacheTtlSeconds":_TTLS["sgo"],"data":payload}

def _sharp(query):
    key=os.getenv("SHARPAPI_KEY","").strip()
    base=os.getenv("SHARPAPI_BASE_URL","https://api.sharpapi.io/api/v1/odds").strip()
    if not key: raise AdapterError("SHARPAPI_KEY is not configured on the server.")
    # Forward only documented, non-secret filter parameters. The exact SharpAPI
    # schema must be confirmed against the account's current API docs before use.
    allowed=("sport","league","date","from","to","event_id","market","market_type","region","sportsbook","is_live","limit")
    params={k:(query.get(k) or [""])[0] for k in allowed if (query.get(k) or [""])[0]}
    # Keep health checks and empty-filter requests small on the free tier.
    params.setdefault("sportsbook","draftkings")
    params.setdefault("is_live","false")
    params["limit"]=str(min(5,max(1,int(params.get("limit","5")))))
    payload,hit=_cached("sharp:"+urllib.parse.urlencode(params),_TTLS["sharp"],
                         lambda:_get_json(_query_url(base,params),{"X-API-Key":key})[0])
    return {"ok":True,"source":"SharpAPI","fetchedAt":time.time(),"cacheHit":hit,
            "contractStatus":"provisional: confirm endpoint/query schema in the provider dashboard",
            "data":payload}

def _weatherapi(query):
    key=os.getenv("WEATHERAPI_KEY","").strip()
    if not key: raise AdapterError("WEATHERAPI_KEY is not configured on the server.")
    location=(query.get("q") or [""])[0]
    if not location: raise AdapterError("WeatherAPI requires q=latitude,longitude or a supported location.")
    day=(query.get("date") or [""])[0]
    today=datetime.now(timezone.utc).date().isoformat()
    endpoint=("history.json" if day < today else "forecast.json") if day else "current.json"
    params={"key":key,"q":location,"days":"3" if endpoint=="forecast.json" else None,"dt":day or None,"aqi":"no","alerts":"no"}
    base=os.getenv("WEATHERAPI_BASE_URL","https://api.weatherapi.com/v1").strip().rstrip("/")
    url=base+"/"+endpoint
    cachekey="weatherapi:"+endpoint+":"+location+":"+day
    payload,hit=_cached(cachekey,_TTLS["weatherapi"],lambda:_get_json(_query_url(url,params))[0])
    return {"ok":True,"source":"WeatherAPI.com","fetchedAt":time.time(),"cacheHit":hit,"data":payload}

def _odds_sports_catalog():
    """Return the provider's live sport catalogue; do not guess competition keys."""
    key=os.getenv("THE_ODDS_API_KEY","").strip()
    if not key: raise AdapterError("THE_ODDS_API_KEY is not configured on the server.")
    base=os.getenv("THE_ODDS_API_BASE_URL","https://api.the-odds-api.com/v4/sports").strip().rstrip("/")
    payload,headers=_cached("odds:sports-catalog",3600,lambda:_get_json(_query_url(base,{"apiKey":key})))
    rows=payload if isinstance(payload,list) else (payload.get("data") or [] if isinstance(payload,dict) else [])
    soccer=[{"key":x.get("key"),"title":x.get("title"),"group":x.get("group"),"active":x.get("active")}
            for x in rows if isinstance(x,dict) and (str(x.get("group","")).lower()=="soccer" or str(x.get("key","")).startswith("soccer_"))]
    h={str(k).lower():v for k,v in (headers or {}).items()}
    return {"ok":True,"source":"The Odds API sports catalogue","fetchedAt":time.time(),
            "sports":soccer,"sportCount":len(soccer),
            "quota":{"remaining":int(h["x-requests-remaining"]) if str(h.get("x-requests-remaining","")).isdigit() else None,
                     "used":int(h["x-requests-used"]) if str(h.get("x-requests-used","")).isdigit() else None},
            "note":"Live provider catalogue only. Active means listed by the provider, not that fixtures or markets are currently available."}

def _prob(value, name):
    try: x=float(value)
    except (TypeError,ValueError): raise AdapterError(name+" must be numeric.")
    if not 0 <= x <= 1: raise AdapterError(name+" must be between 0 and 1.")
    return x

def calculate_ev(query):
    """Transparent expected-return calculation from caller-supplied model probability and decimal odds."""
    p=_prob((query.get("probability") or [""])[0],"probability")
    try: odds=float((query.get("odds") or [""])[0])
    except (TypeError,ValueError): raise AdapterError("odds must be numeric.")
    if odds <= 1: raise AdapterError("decimal odds must be greater than 1.")
    return {"ok":True,"method":"EV = p * decimal_odds - 1","modelProbability":p,"decimalOdds":odds,
            "expectedReturnPerUnit":p*odds-1,"breakEvenProbability":1/odds,
            "warning":"Only as reliable as the supplied probability and price; this is not a profit guarantee."}

def calculate_arbitrage(query):
    """Check decimal odds for mutually exclusive exhaustive outcomes supplied by caller."""
    raw=(query.get("odds") or [""])[0]
    try: odds=[float(x.strip()) for x in raw.split(",") if x.strip()]
    except ValueError: raise AdapterError("odds must be comma-separated decimal prices.")
    if len(odds)<2 or any(x<=1 for x in odds): raise AdapterError("Supply at least two decimal odds, each greater than 1.")
    implied=sum(1/x for x in odds)
    return {"ok":True,"decimalOdds":odds,"impliedProbabilitySum":implied,
            "arbitrageDetected":implied<1,"theoreticalMargin":(1-implied) if implied<1 else 0,
            "equalPayoutStakeFractions":[(1/x)/implied for x in odds],
            "warning":"Valid only when odds cover every mutually exclusive outcome with identical settlement rules; fees, limits and price changes can erase the margin."}

def _normalized_matches(query):
    """Aggregate configured fixture/odds providers instead of returning the first partial feed."""
    errors=[]
    collected=[]
    sources=[]
    fetched=[]
    provider_counts={}
    requested_sports=[]
    if os.getenv("SPORTSGAMEODDS_API_KEY","").strip():
        try:
            match_query=dict(query)
            if not (match_query.get("limit") or [""])[0].strip():
                match_query["limit"]=["50"]
            raw=_sgo_events(match_query)
            records=normalize_provider_payload("SportsGameOdds",raw.get("data"),raw.get("fetchedAt"))
            provider_counts["SportsGameOdds"]=len(records)
            if records:
                collected.extend(records)
                sources.append("SportsGameOdds")
                fetched.append(raw.get("fetchedAt"))
            else:
                errors.append("SportsGameOdds returned no normalized records")
        except AdapterError as exc:
            errors.append("SportsGameOdds: "+str(exc))
    if os.getenv("THE_ODDS_API_KEY","").strip():
        raw_sports=(query.get("sports") or [(query.get("sport") or ["soccer_epl"])[0]])[0]
        sports=list(dict.fromkeys(x.strip() for x in raw_sports.split(",") if x.strip()))
        requested_sports=sports
        if len(sports)>16:
            raise AdapterError("At most 16 sports may be requested per normalized match search.")
        for sport in sports:
            try:
                odds_query=dict(query)
                odds_query.setdefault("regions",["uk"])
                odds_query.setdefault("markets",["h2h"])
                raw=_odds_api(sport,odds_query)
                records=normalize_provider_payload("The Odds API",raw.get("data"),raw.get("fetchedAt"))
                provider_counts["The Odds API:"+sport]=len(records)
                if records:
                    collected.extend(records)
                    if "The Odds API" not in sources:
                        sources.append("The Odds API")
                    fetched.append(raw.get("fetchedAt"))
                else:
                    errors.append("The Odds API ("+sport+") returned no normalized records")
            except AdapterError as exc:
                errors.append("The Odds API ("+sport+"): "+str(exc))
    # Deduplicate by normalized teams + kickoff; merge source/odds evidence rather than discarding a provider.
    merged={}
    for row in collected:
        if not isinstance(row,dict):
            continue
        home=" ".join(str(row.get("homeTeam") or "").casefold().split())
        away=" ".join(str(row.get("awayTeam") or "").casefold().split())
        kickoff=str(row.get("kickoff") or "")
        key=(home,away,kickoff[:16])
        if not home or not away or not kickoff:
            key=(home,away,str(row.get("fixtureId") or row.get("matchId") or len(merged)))
        current=merged.get(key)
        if current is None:
            merged[key]=dict(row)
            merged[key]["sources"]=dict(row.get("sources") or {})
            continue
        current_sources=current.setdefault("sources",{})
        for k,v in (row.get("sources") or {}).items():
            current_sources[k]=v
        if row.get("odds"):
            current["odds"]={**(current.get("odds") or {}),**row["odds"]}
        if row.get("lineups") and not current.get("lineups"):
            current["lineups"]=row["lineups"]
        if row.get("statistics") and not current.get("statistics"):
            current["statistics"]=row["statistics"]
        if row.get("events") and not current.get("events"):
            current["events"]=row["events"]
        current["providerSources"]=sorted(set(current.get("providerSources",[])+row.get("providerSources",[])))
    rows=list(merged.values())
    if not rows:
        detail="; ".join(errors) if errors else "Configure SPORTSGAMEODDS_API_KEY or THE_ODDS_API_KEY on the backend to load normalized match records."
        raise AdapterError("No match provider returned usable records. "+detail)
    return {"ok":True,"source":"multi-provider","sources":sources,
            "fetchedAt":max((x for x in fetched if x is not None),default=time.time()),
            "requestedSports":requested_sports,"providerRecordCounts":provider_counts,
            "data":rows,"recordCount":len(rows),"fallbackUsed":bool(errors),
            "providerWarnings":errors,
            "note":"Configured fixture and odds providers are aggregated. Missing scores, events, lineups and statistics remain unknown."}

def _provider_health(query):
    """Explicit, quota-aware connectivity checks; invoke only when the user clicks Test."""
    requested=(query.get("providers") or query.get("provider") or ["sportmonks,sportsgameodds,theoddsapi,weatherapi,sharpapi,openmeteo"])[0]
    names=[x.strip().lower() for x in requested.split(",") if x.strip()]
    if not names or names==["all"]:
        names=["sportmonks","sportsgameodds","theoddsapi","weatherapi","sharpapi","openmeteo"]
    aliases={"sgo":"sportsgameodds","odds":"theoddsapi","the-odds-api":"theoddsapi","weatherapi.com":"weatherapi","open-meteo":"openmeteo"}
    names=[aliases.get(x,x) for x in names]
    allowed={"sportsgameodds","theoddsapi","weatherapi","sharpapi","openmeteo","sportmonks"}
    unknown=[x for x in names if x not in allowed]
    if unknown: raise AdapterError("Unknown provider name: "+", ".join(unknown))
    results={}
    for name in dict.fromkeys(names):
        configured=True
        def probe():
            if name=="sportsgameodds":
                if not os.getenv("SPORTSGAMEODDS_API_KEY","").strip(): raise AdapterError("SPORTSGAMEODDS_API_KEY is not configured.")
                result=_sgo_events({"sportID":["SOCCER"],"leagueID":[(query.get("leagueID") or ["MLS"])[0]],"limit":["1"],"oddsAvailable":["true"],"includeAltLines":["false"]})
                return {"source":result.get("source"),"records":len(((result.get("data") or {}).get("data") or (result.get("data") or {}).get("events") or [])) if isinstance(result.get("data"),dict) else (len(result.get("data")) if isinstance(result.get("data"),list) else None)}
            if name=="theoddsapi":
                if not os.getenv("THE_ODDS_API_KEY","").strip(): raise AdapterError("THE_ODDS_API_KEY is not configured.")
                result=_odds_api((query.get("sport") or ["soccer_epl"])[0],{"regions":["uk"],"markets":["h2h"]})
                data=result.get("data")
                return {"source":"The Odds API","records":len(data) if isinstance(data,list) else None,"quota":result.get("quota")}
            if name=="weatherapi":
                if not os.getenv("WEATHERAPI_KEY","").strip(): raise AdapterError("WEATHERAPI_KEY is not configured.")
                result=_weatherapi({"q":[(query.get("q") or ["6.5244,3.3792"])[0]]})
                data=result.get("data") or {}
                return {"source":"WeatherAPI.com","location":(data.get("location") or {}).get("name"),"currentAvailable":isinstance(data.get("current"),dict)}
            if name=="sharpapi":
                if not os.getenv("SHARPAPI_KEY","").strip(): raise AdapterError("SHARPAPI_KEY is not configured.")
                result=_sharp({})
                return {"source":"SharpAPI","contractStatus":result.get("contractStatus"),"responseReceived":result.get("data") is not None}
            if name=="openmeteo":
                url="https://api.open-meteo.com/v1/forecast?"+urllib.parse.urlencode({"latitude":"6.5244","longitude":"3.3792","current":"temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"})
                data,_headers=_get_json(url)
                return {"source":"Open-Meteo","currentAvailable":isinstance(data.get("current"),dict)}
            if name=="sportmonks":
                token=os.getenv("SPORTMONKS_API_TOKEN","").strip()
                if not token: raise AdapterError("SPORTMONKS_API_TOKEN is not configured.")
                url="https://api.sportmonks.com/v3/football/leagues?"+urllib.parse.urlencode({"api_token":token,"per_page":"1"})
                data,_headers=_get_json(url)
                rows=data.get("data") if isinstance(data,dict) else None
                return {"source":"Sportmonks Football API v3","apiResponded":True,
                        "catalogRecords":len(rows) if isinstance(rows,list) else None,
                        "note":"Catalog connectivity only; fixture/lineup coverage is competition- and plan-specific."}
        try:
            value,cache_hit=_cached("health:"+name+":"+str((query.get("sport") or ["soccer_epl"])[0])+":"+str((query.get("q") or ["Lagos"])[0]),300,probe)
            results[name]={"reachable":True,"status":"ok","cacheHit":cache_hit,**value}
        except AdapterError as exc:
            message=str(exc)
            configured=not message.endswith("is not configured.")
            results[name]={"reachable":False,"status":"not-configured" if not configured else "error","message":message}
        except Exception as exc:
            results[name]={"reachable":False,"status":"error","message":"Probe failed safely: "+type(exc).__name__}
    return {"ok":all(v["reachable"] for v in results.values()),"checkedAt":datetime.now(timezone.utc).isoformat(),
            "checks":results,"note":"Connectivity test makes real provider requests and may consume quota. Results are cached for 5 minutes. SharpAPI remains provisional until its endpoint contract is confirmed."}

def handle_extra_route(route, query):
    if route == "/api/matches":
        return _normalized_matches(query),False
    if route == "/api/providers/health":
        return _provider_health(query),False
    if route == "/api/providers/status":
        names={"sportmonks":bool(os.getenv("SPORTMONKS_API_TOKEN","").strip()),
               "sharpapi":bool(os.getenv("SHARPAPI_KEY","").strip()),
               "weatherapi":bool(os.getenv("WEATHERAPI_KEY","").strip()),
               "theOddsApi":bool(os.getenv("THE_ODDS_API_KEY","").strip()),
               "sportsGameOdds":bool(os.getenv("SPORTSGAMEODDS_API_KEY","").strip()),
               "openMeteo":True}
        return {"ok":True,"providers":{k:{"configured":v,"status":"configured-not-connectivity-tested" if v else "not-configured"} for k,v in names.items()},
                "secretValuesReturned":False,"note":"Configured means a secret exists, not that the provider is reachable or that your free plan covers the requested league."},False
    if route == "/api/sports/catalog":
        return _odds_sports_catalog(),False
    if route == "/api/odds/the-odds-api":
        sport=(query.get("sport") or ["soccer_epl"])[0]
        return _odds_api(sport,query),False
    if route == "/api/odds/sportsgameodds":
        return _sgo_events(query),False
    if route == "/api/odds/sharpapi":
        return _sharp(query),False
    if route == "/api/weather/weatherapi":
        return _weatherapi(query),False
    if route == "/api/ev":
        return calculate_ev(query),False
    if route == "/api/arbitrage":
        return calculate_arbitrage(query),False
    if route == "/api/openrouter/status":
        return {"ok": True, "provider": "OpenRouter",
                "configured": bool(os.getenv("OPENROUTER_API_KEY", "").strip()),
                "model": os.getenv("OPENROUTER_MODEL", "openrouter/auto"),
                "secretValuesReturned": False,
                "note": "Configuration status only; this route does not test provider connectivity."}, False
    if route == "/api/openrouter/chat":
        key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if not key:
            raise AdapterError("OPENROUTER_API_KEY is not configured on the server.")
        raw_messages = (query.get("messages") or [""])[0]
        if not raw_messages:
            raise AdapterError("messages is required as URL-encoded JSON.")
        try:
            messages = json.loads(raw_messages)
        except (TypeError, ValueError):
            raise AdapterError("messages must be a URL-encoded JSON array.") from None
        if (not isinstance(messages, list) or not messages or
                any(not isinstance(m, dict) or m.get("role") not in ("system", "user", "assistant")
                    or not isinstance(m.get("content"), str) for m in messages)):
            raise AdapterError("messages must be a non-empty array of role/content objects.")
        # Bound payloads and reject unsupported roles to keep the public endpoint predictable.
        if len(messages) > 20 or sum(len(m["content"]) for m in messages) > 24000:
            raise AdapterError("messages exceed the request size limit.")
        model = (query.get("model") or [os.getenv("OPENROUTER_MODEL", "openrouter/auto")])[0].strip()
        if not model or len(model) > 160:
            raise AdapterError("model is invalid.")
        body = json.dumps({"model": model, "messages": messages, "temperature": 0.2,
                           "max_tokens": 1800}).encode("utf-8")
        request = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions", data=body, method="POST",
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                     "Accept": "application/json", "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", ""),
                     "X-Title": "Universal Football Intelligence"})
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            # Do not return upstream bodies that could contain request details or secrets.
            raise AdapterError("OpenRouter returned HTTP %s; check server-side key, model access and quota." % exc.code) from None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise AdapterError("OpenRouter request failed safely: " + type(exc).__name__) from None
        choices = payload.get("choices") if isinstance(payload, dict) else None
        if not choices or not isinstance(choices[0].get("message"), dict):
            raise AdapterError("OpenRouter response did not contain a usable assistant message.")
        usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
        return {"ok": True, "provider": "OpenRouter", "model": payload.get("model", model),
                "message": choices[0]["message"], "usage": {
                    "prompt_tokens": usage.get("prompt_tokens"),
                    "completion_tokens": usage.get("completion_tokens"),
                    "total_tokens": usage.get("total_tokens")},
                "note": "Text generation only. This response is not independently verified and is not itself a football prediction."}, False
    if route == "/api/models/score":
        home = (query.get("home") or [""])[0].strip()
        away = (query.get("away") or [""])[0].strip()
        league = (query.get("league") or [""])[0].strip().upper()
        cutoff = (query.get("date") or [""])[0].strip()
        seasons = (query.get("seasons") or ["5"])[0]
        if not home or not away or not league:
            raise AdapterError("home, away and a supported league code are required.")
        try:
            try:
                from .ufi_historical_results import load_football_data_results
                from .ufi_score_models import predict_fixture
            except ImportError:
                from ufi_historical_results import load_football_data_results
                from ufi_score_models import predict_fixture
            historical = load_football_data_results(league, seasons)
            result = predict_fixture(historical.get("data", []), home, away, cutoff or None)
            return {"ok": True, "source": historical.get("source"), "league_code": league,
                    "source_urls": historical.get("source_urls", []), "fetched_at": historical.get("fetched_at"),
                    "source_record_count": historical.get("record_count", 0), **result}, False
        except ValueError as exc:
            raise AdapterError(str(exc)) from None
        except Exception as exc:
            raise AdapterError("Score model failed safely ("+type(exc).__name__+").") from None
    if route == "/api/history/results":
        league = (query.get("league") or [""])[0].strip().upper()
        seasons = (query.get("seasons") or ["5"])[0]
        try:
            try:
                from .ufi_historical_results import load_football_data_results
            except ImportError:
                from ufi_historical_results import load_football_data_results
            return load_football_data_results(league, seasons), False
        except ValueError as exc:
            raise AdapterError(str(exc)) from None
    if route == "/api/analytics/config":
        token = os.getenv("POSTHOG_API_KEY", "").strip()
        host = os.getenv("POSTHOG_HOST", "https://us.i.posthog.com").strip().rstrip("/")
        if not host.startswith("https://"):
            host = "https://us.i.posthog.com"
        return {"ok": True, "configured": bool(token), "projectToken": token if token else None,
                "apiHost": host, "autocapture": False, "sessionRecording": False,
                "note": "Public PostHog project token is exposed only for browser event ingestion; no private credentials are returned."}, False
    if route == "/api/ai/status":
        return {"ok": True,
                "providers": {
                    "gemini": {"configured": bool(os.getenv("GEMINI_API_KEY", "").strip()), "role": "primary"},
                    "openrouter": {"configured": bool(os.getenv("OPENROUTER_API_KEY", "").strip()), "role": "fallback"}},
                "secretValuesReturned": False,
                "note": "Configuration only; actual provider connectivity is checked during a research request."}, False
    if route == "/api/ai/research-fixture":
        home = (query.get("home") or [""])[0].strip()
        away = (query.get("away") or [""])[0].strip()
        competition = (query.get("competition") or [""])[0].strip()
        match_date = (query.get("date") or [""])[0].strip()
        if not home or not away:
            raise AdapterError("home and away are required.")
        try:
            try:
                from .ufi_ai_orchestrator import research_fixture_with_failover
            except ImportError:
                from ufi_ai_orchestrator import research_fixture_with_failover
            return {"ok": True, **research_fixture_with_failover(home, away, competition, match_date)}, False
        except ValueError as exc:
            raise AdapterError(str(exc)) from None
        except RuntimeError as exc:
            raise AdapterError(str(exc)) from None
    if route == "/api/ai/council":
        raw_prompt = (query.get("prompt") or [""])[0]
        if not raw_prompt.strip():
            raise AdapterError("prompt is required.")
        try:
            try:
                from .ufi_ai_orchestrator import review_with_failover
            except ImportError:
                from ufi_ai_orchestrator import review_with_failover
            return review_with_failover(raw_prompt), False
        except ValueError as exc:
            raise AdapterError(str(exc)) from None
    if route == "/api/ai/research":
        raw_question = (query.get("question") or [""])[0].strip()
        raw_sources = (query.get("source_material") or [""])[0]
        if not raw_question:
            raise AdapterError("question is required.")
        if not raw_sources:
            return {"status": "NEEDS_DATA", "claims": [], "verified": False,
                    "reason": "source_material is required; no live facts will be invented."}, False
        try:
            source_material = json.loads(raw_sources)
        except (TypeError, ValueError):
            raise AdapterError("source_material must be URL-encoded JSON array.") from None
        try:
            try:
                from .ufi_ai_orchestrator import research_with_failover
            except ImportError:
                from ufi_ai_orchestrator import research_with_failover
            return {"ok": True, **research_with_failover(raw_question, source_material)}, False
        except ValueError as exc:
            raise AdapterError(str(exc)) from None
    return None
