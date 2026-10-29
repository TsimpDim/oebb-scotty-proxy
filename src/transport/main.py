from fastapi import FastAPI
from datetime import datetime
from zoneinfo import ZoneInfo
from transport.scotty import STATIONS, BASE_URL, HEADERS
from transport.utils import get_payload, simplify_response, filter_journeys_by_window, make_retrying_session
from fastapi import Depends
from transport.auth import handle_api_key
from transport.db import get_journeys

AUSTRIA_TZ = ZoneInfo("Europe/Vienna")


def _utc_time_to_austria_minutes(utc_time_str: str) -> int:
    hours, minutes = utc_time_str.split(":")
    now_utc = datetime.now(tz=ZoneInfo("UTC"))
    austria_now = now_utc.astimezone(AUSTRIA_TZ)
    return (int(hours) * 60 + int(minutes) + austria_now.utcoffset().total_seconds() // 60) % (24 * 60)


def _now_austria_minutes() -> int:
    now = datetime.now(tz=AUSTRIA_TZ)
    return now.hour * 60 + now.minute

app = FastAPI(dependencies=[
    Depends(handle_api_key),
])

# Reuse a single session for connection pooling and retries across requests.
_session = make_retrying_session()

_REQUEST_TIMEOUT = 10

def dev() -> None:
    import uvicorn

    uvicorn.run("transport.main:app", host="127.0.0.1", port=8000, reload=True)

@app.get("/stations")
def read_stations():
    return STATIONS

@app.get("/stations/{station_id}")
def read_station(station_id: str):
    station = STATIONS.get(station_id)
    if not station:
        return {"error": "Station not found."}

    payload = get_payload(station['extId'], station["name"])
    data = _session.post(BASE_URL, json=payload, timeout=_REQUEST_TIMEOUT)

    if data.status_code != 200:
        return {"error": "Failed to fetch data from the API."}
    return simplify_response(data.json())

@app.get("/journeys/vienna")
def read_journeys_vienna(fromTime: str | None = None):
    stored = get_journeys()
    if stored is None:
        return {"error": "No journeys available yet."}
    ref_minutes = _utc_time_to_austria_minutes(fromTime) if fromTime else _now_austria_minutes()
    return filter_journeys_by_window(stored["data"], ref_minutes)