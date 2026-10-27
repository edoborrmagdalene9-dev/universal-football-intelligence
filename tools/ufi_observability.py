"""Privacy-conscious optional Datadog/PostHog server telemetry for UFI."""
from __future__ import annotations
import json, os, time, urllib.error, urllib.request

def emit_request(route: str, outcome: str, duration_ms: float, error_type: str | None = None) -> None:
    # Route names only: never log query strings, tokens, source payloads, user data or odds.
    route = str(route or "unknown").split("?",1)[0][:120]
    event={"service":"universal-football-intelligence","route":route,"outcome":outcome,
           "duration_ms":round(max(0.0,float(duration_ms)),2),"error_type":error_type}
    print(json.dumps({"level":"error" if outcome=="error" else "info","event":"ufi_request","telemetry":event},separators=(",",":")),flush=True)
    dd_key=os.getenv("DD_API_KEY","").strip()
    if dd_key:
        site=os.getenv("DD_SITE","datadoghq.com").strip()
        _post("https://http-intake.logs."+site+"/api/v2/logs",
              [{"ddsource":"python","service":"universal-football-intelligence",
                "status":"error" if outcome=="error" else "info","message":"UFI backend request",
                "ufi":event}],{"DD-API-KEY":dd_key},timeout=0.7)
    ph_key=os.getenv("POSTHOG_API_KEY","").strip()
    if ph_key:
        host=os.getenv("POSTHOG_HOST","https://us.i.posthog.com").strip().rstrip("/")
        _post(host+"/capture/",{"api_key":ph_key,"event":"ufi_backend_request",
              "distinct_id":"ufi-backend-service","properties":event},{},timeout=0.7)

def _post(url: str, payload, headers: dict[str,str], timeout: float) -> None:
    try:
        body=json.dumps(payload,separators=(",",":")).encode()
        req=urllib.request.Request(url,data=body,method="POST",
            headers={"Content-Type":"application/json","User-Agent":"UFI-Observability/1.0",**headers})
        with urllib.request.urlopen(req,timeout=timeout) as response:
            response.read(128)
    except Exception:
        # Telemetry must never break prediction/data routes; provider health is visible via logs.
        return
