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
def _integrated_get_payload(route, query):
    try:
        extra=adapters.handle_extra_route(route,query)
        if extra is not None:
            return extra
        return _original_get_payload(route,query)
    except adapters.AdapterError as exc:
        raise legacy.ProviderError(str(exc)) from exc
legacy.get_payload = _integrated_get_payload

if __name__ == "__main__":
    if not legacy.TOKEN:
        print("INFO: SPORTMONKS_API_TOKEN is unset; Sportmonks routes will report unavailable.")
    print(f"UFI multi-provider proxy listening on 0.0.0.0:{legacy.PORT}")
    ThreadingHTTPServer(("0.0.0.0",legacy.PORT),legacy.Handler).serve_forever()
