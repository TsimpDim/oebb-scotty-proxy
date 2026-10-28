from fastapi import FastAPI
import requests as r
from datetime import datetime
from transport.scotty import STATIONS, BASE_URL, HEADERS
from transport.utils import get_payload, simplify_response, fetch_vienna_journeys, filter_journeys_by_window
from fastapi import Depends
from transport.auth import handle_api_key
from transport.db import get_journeys

app = FastAPI(dependencies=[
    Depends(handle_api_key),
])

# Reuse a single session for connection pooling across requests.
_session = r.Session()
_session.headers.update(HEADERS)

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
def read_journeys_vienna(date: str | None = None, time: str | None = None):
    if date is None and time is None:
        stored = get_journeys()
        if stored is None:
            return {"error": "No journeys available yet."}
        now = datetime.now()
        return filter_journeys_by_window(stored["data"], now.hour * 60 + now.minute)

    now = datetime.now()
    search_date = date or now.strftime("%Y%m%d")
    search_time = time or now.strftime("%H%M%S")
    result = fetch_vienna_journeys(_session, BASE_URL, HEADERS, search_date, search_time)
    return result or {"error": "Failed to fetch data from the API."}