#!/usr/bin/env python3
"""Production entrypoint that extends the existing UFI proxy without removing routes."""
from __future__ import annotations
import json, os, time, urllib.parse, urllib.request, urllib.error
from datetime import date
from http.server import ThreadingHTTPServer
import ufi_live_data_proxy as legacy
import ufi_provider_adapters as adapters

# The Odds API returns usage metadata in response headers. Keep the JSON body
# as the data field and expose quota headers without exposing any credentials.
_original_odds_api = adapters._odds_api
def _odds_api_with_usage(sport, query):
    result = _original_odds_api(sport, query)
    data = result.get("data")
    if isinstance(data, tuple) and len(data) == 2:
        payload, headers = data
        result["data"] = payload
        result["quota"] = {
            "requestsUsed": headers.get("x-requests-used"),
            "requestsRemaining": headers.get("x-requests-remaining"),
            "requestsLast": headers.get("x-requests-last"),
            "note": "Values are provider response headers; null means the provider did not send that header."
        }
    return result
adapters._odds_api = _odds_api_with_usage

def _open_meteo_enhanced(lat: float, lon: float, day: str, hour: int):
    today=date.today().isoformat()
    archive=day<today
    base="https://archive-api.open-meteo.com/v1/archive" if archive else "https://api.open-meteo.com/v1/forecast"
    params={"latitude":str(lat),"longitude":str(lon),
            "hourly":"temperature_2m,relative_humidity_2m,precipitation,precipitation_probability,wind_speed_10m",
            "timezone":"UTC"}
    if archive:
        params.update({"start_date":day,"end_date":day})
    else:
        params["forecast_days"]="7"
    url=base+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":"UFI-research/1.0"})
    try:
        with urllib.request.urlopen(req,timeout=12) as response:
            payload=json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError,urllib.error.HTTPError,TimeoutError,json.JSONDecodeError) as exc:
        raise legacy.ProviderError("Open-Meteo weather source unavailable: "+type(exc).__name__) from exc
    hourly=payload.get("hourly") or {}
    times=hourly.get("time") or []
    matches=[i for i,t in enumerate(times) if t.startswith(day+"T")]
    if not matches:
        raise legacy.ProviderError("Weather source returned no hourly observations for requested date/location.")
    index=min(matches,key=lambda i:abs(int(times[i][11:13])-hour))
    def value(key):
        vals=hourly.get(key) or []
        return vals[index] if index<len(vals) else None
    return {"source":"Open-Meteo","sourceUrl":base,"fetchedAt":time.time(),
            "requested":{"latitude":lat,"longitude":lon,"date":day,"hourUtc":hour},
            "matchedHourUtc":times[index],"archive":archive,
            "weather":{"temperatureC":value("temperature_2m"),
                       "relativeHumidityPct":value("relative_humidity_2m"),
                       "precipitationMm":value("precipitation"),
                       "precipitationProbabilityPct":value("precipitation_probability"),
                       "windSpeedKmh":value("wind_speed_10m")},
            "note":"Grid-cell weather estimate, not stadium sensor data."}

legacy.open_meteo_weather = _open_meteo_enhanced
_original_get_payload = legacy.get_payload

def _has_provider_rows(payload):
    """Detect genuinely empty legacy provider envelopes without guessing data."""
    if not isinstance(payload,dict):
        return bool(payload)
    data=payload.get("data")
    if isinstance(data,list):
        return len(data)>0
    if isinstance(data,dict):
        rows=data.get("data")
        if isinstance(rows,list):
            return len(rows)>0
        # A non-empty provider envelope without a recognizable row list is
        # not proof of usable fixtures; treat explicit no-results as empty.
        if data.get("message") and not rows:
            return False
    return data is not None

def _fallback_live_feed(query):
    """Use only an explicitly live/started SGO feed; never label upcoming odds as live."""
    raw=adapters._sgo_events({"live":["true"],"started":["true"],
                              "limit":["50"],"oddsAvailable":["false"],
                              "includeAltLines":["false"]})
    rows=adapters.normalize_provider_payload("SportsGameOdds",raw.get("data"),raw.get("fetchedAt"))
    return {"ok":True,"source":"SportsGameOdds","fetchedAt":raw.get("fetchedAt"),
            "cacheHit":raw.get("cacheHit"),"data":rows,"recordCount":len(rows),
            "fallbackUsed":True,"fallbackReason":"Sportmonks returned no accessible live records",
            "note":"Only provider-marked live/started fixtures are included. Missing scores/events remain unknown."},False

def _fallback_date_fixtures(query):
    """Use odds-provider fixtures as a labelled fallback when Sportmonks has no date rows."""
    raw_day=(query.get("date") or [date.today().isoformat()])[0]
    try:
        requested=date.fromisoformat(raw_day)
    except ValueError as exc:
        raise legacy.ProviderError("date must use YYYY-MM-DD") from exc
    start=requested.isoformat()+"T00:00:00Z"
    end=(requested.fromordinal(requested.toordinal()+1)).isoformat()+"T00:00:00Z"
    sport=(query.get("sport") or ["soccer_epl"])[0]
    raw=adapters._odds_api(sport,{"from":[start],"to":[end],
                                  "regions":["uk"],"markets":["h2h"]})
    rows=adapters.normalize_provider_payload("The Odds API",raw.get("data"),raw.get("fetchedAt"))
    # Guard against provider timezone/range quirks; never return another date.
    rows=[row for row in rows if isinstance(row.get("kickoff"),str)
          and row["kickoff"][:10]==raw_day]
    return {"ok":True,"source":"The Odds API","fetchedAt":raw.get("fetchedAt"),
            "cacheHit":raw.get("cacheHit"),"data":rows,"recordCount":len(rows),
            "fallbackUsed":True,"fallbackReason":"Sportmonks returned no accessible fixtures for the requested date",
            "note":"Odds-only fixture fallback. Scores, events, lineups and statistics are intentionally unknown."},False

def _integrated_get_payload(route, query):
    # Additive end-to-end route: source fixture -> historical model, with evidence gates.
    if route == "/api/pipeline/predict":
        try:
            try:
                from .ufi_end_to_end_pipeline import generate_fixture_pipeline
                from .ufi_prediction_api import generate_score_prediction
            except ImportError:
                from ufi_end_to_end_pipeline import generate_fixture_pipeline
                from ufi_prediction_api import generate_score_prediction
            return generate_fixture_pipeline(query, _original_get_payload, generate_score_prediction), False
        except ValueError as exc:
            raise legacy.ProviderError(str(exc)) from exc

    # Expose the existing historical Poisson/Dixon-Coles model through an additive API route.
    # This route deliberately keeps the market gate at WAIT until odds are independently validated.
    if route == "/api/models/score":
        try:
            try:
                from .ufi_prediction_api import generate_score_prediction
            except ImportError:
                from ufi_prediction_api import generate_score_prediction
            return generate_score_prediction(query), False
        except ValueError as exc:
            raise legacy.ProviderError(str(exc)) from exc
    try:
        extra=adapters.handle_extra_route(route,query)
        if extra is not None:
            return extra
        payload,cache_hit=_original_get_payload(route,query)
        if route=="/api/live" and not _has_provider_rows(payload):
            try:
                return _fallback_live_feed(query)
            except adapters.AdapterError as fallback_error:
                if isinstance(payload,dict):
                    payload=dict(payload)
                    payload["fallbackAttempt"]={"source":"SportsGameOdds","error":str(fallback_error)}
                    payload["note"]="Sportmonks returned no accessible live records and the live-only fallback was unavailable."
                return payload,cache_hit
        if route=="/api/fixtures" and not _has_provider_rows(payload):
            try:
                return _fallback_date_fixtures(query)
            except adapters.AdapterError as fallback_error:
                if isinstance(payload,dict):
                    payload=dict(payload)
                    payload["fallbackAttempt"]={"source":"The Odds API","error":str(fallback_error)}
                    payload["note"]="Sportmonks returned no accessible fixtures and the odds-only fallback was unavailable."
                return payload,cache_hit
        return payload,cache_hit
    except adapters.AdapterError as exc:
        raise legacy.ProviderError(str(exc)) from exc
    except legacy.ProviderError as exc:
        # If Open-Meteo is temporarily rate-limited/unavailable, return a clearly
        # labelled WeatherAPI current observation as a fallback. Do not pretend
        # it is an hourly kickoff forecast or historical observation.
        if route == "/api/weather" and os.getenv("WEATHERAPI_KEY","").strip():
            try:
                lat=(query.get("lat") or [""])[0]
                lon=(query.get("lon") or [""])[0]
                requested_day=(query.get("date") or [date.today().isoformat()])[0]
                requested_hour=int((query.get("hour") or ["12"])[0])
                fallback,_=adapters.handle_extra_route(
                    "/api/weather/weatherapi",{"q":[lat+","+lon],"date":[requested_day]})
                payload=fallback.get("data") or {}
                # Prefer a true hourly forecast/history point for the requested
                # kickoff. Never silently substitute current weather for a future
                # or historical match.
                location=payload.get("location") or {}
                timezone_name=location.get("tz_id") or "UTC"
                from datetime import datetime, timezone
                from zoneinfo import ZoneInfo
                requested_utc=datetime.fromisoformat(
                    requested_day+"T"+f"{requested_hour:02d}:00").replace(tzinfo=timezone.utc)
                requested_local=requested_utc.astimezone(ZoneInfo(timezone_name))
                days=((payload.get("forecast") or {}).get("forecastday") or [])
                target_day=requested_local.date().isoformat()
                day_record=next((item for item in days if item.get("date")==target_day),None)
                hours=(day_record or {}).get("hour") or []
                if hours:
                    def hour_distance(item):
                        try:
                            parsed=datetime.fromisoformat(item.get("time","").replace(" ","T"))
                            return abs((parsed-requested_local.replace(tzinfo=None)).total_seconds())
                        except (TypeError,ValueError):
                            return float("inf")
                    point=min(hours,key=hour_distance)
                    current=point
                    return {"source":"WeatherAPI.com","fallbackUsed":True,
                            "fallbackReason":"Open-Meteo unavailable; using WeatherAPI hourly data",
                            "fetchedAt":fallback.get("fetchedAt"),
                            "requested":{"latitude":lat,"longitude":lon,
                                         "date":requested_day,"hourUtc":requested_hour},
                            "matchedLocalTime":point.get("time"),
                            "location":{"name":location.get("name"),"timezone":timezone_name},
                            "weather":{"temperatureC":current.get("temp_c"),
                                       "relativeHumidityPct":current.get("humidity"),
                                       "precipitationMm":current.get("precip_mm"),
                                       "precipitationProbabilityPct":current.get("chance_of_rain"),
                                       "windSpeedKmh":current.get("wind_kph")},
                            "note":"Hourly WeatherAPI forecast/history for the nearest provider location; grid-cell/stadium conditions may differ."},False
            except (adapters.AdapterError,TypeError,ValueError,KeyError,OverflowError):
                pass
        raise exc
legacy.get_payload = _integrated_get_payload

# Optional telemetry; missing monitoring keys never block application requests.
try:
    from .ufi_observability import emit_request as _emit_telemetry
except ImportError:
    try:
        from ufi_observability import emit_request as _emit_telemetry
    except ImportError:
        _emit_telemetry = None

_unobserved_get_payload = legacy.get_payload
def _observed_get_payload(route, query):
    started = time.monotonic()
    try:
        result = _unobserved_get_payload(route, query)
    except Exception as exc:
        if _emit_telemetry:
            _emit_telemetry(route, "error", (time.monotonic()-started)*1000, type(exc).__name__)
        raise
    if _emit_telemetry:
        _emit_telemetry(route, "ok", (time.monotonic()-started)*1000)
    return result
legacy.get_payload = _observed_get_payload

if __name__ == "__main__":
    if not legacy.TOKEN:
        print("INFO: SPORTMONKS_API_TOKEN is unset; Sportmonks routes will report unavailable.")
    print(f"UFI multi-provider proxy listening on 0.0.0.0:{legacy.PORT}")
    ThreadingHTTPServer(("0.0.0.0",legacy.PORT),legacy.Handler).serve_forever()
