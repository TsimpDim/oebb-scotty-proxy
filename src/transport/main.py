from fastapi import FastAPI
import requests as r
from datetime import datetime
from transport.scotty import STATIONS, BASE_URL, HEADERS
from transport.utils import get_payload, simplify_response, get_journey_payload, simplify_trip_response, refine_connections, fetch_trips_with_scroll
from fastapi import Depends
from transport.auth import handle_api_key
from transport.cache import TTLCache

app = FastAPI(dependencies=[
    Depends(handle_api_key),
])

# Reuse a single session for connection pooling across requests.
_session = r.Session()
_session.headers.update(HEADERS)

_REQUEST_TIMEOUT = 10

_station_cache = TTLCache(ttl=30.0)
_journeys_cache = TTLCache(ttl=60.0)

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

    cached = _station_cache.get(station_id)
    if cached is not None:
        return cached

    payload = get_payload(station['extId'], station["name"])
    data = _session.post(BASE_URL, json=payload, timeout=_REQUEST_TIMEOUT)

    if data.status_code != 200:
        return {"error": "Failed to fetch data from the API."}

    result = simplify_response(data.json())
    _station_cache.set(station_id, result)
    return result

@app.get("/journeys/vienna")
def read_journeys_vienna(date: str | None = None, time: str | None = None):
    origin = STATIONS.get("591161")
    if not origin:
        return {"error": "Origin station not found."}

    now = datetime.now()
    search_date = date or now.strftime("%Y%m%d")
    search_time = time or now.strftime("%H%M%S")

    cache_key = f"{search_date}:{search_time}"
    cached = _journeys_cache.get(cache_key)
    if cached is not None:
        return cached

    result = _fetch_journeys(origin, search_date, search_time)
    if result:
        _journeys_cache.set(cache_key, result)
    return result or {"error": "Failed to fetch data from the API."}

def _fetch_journeys(origin: dict, search_date: str, search_time: str) -> list:
    reference_minutes = int(search_time[:2]) * 60 + int(search_time[2:4])

    destinations = [
        STATIONS.get("8103000")   # Wien Hbf
    ]
    destinations = [d for d in destinations if d]
    if not destinations:
        return []

    connections = []
    for destination in destinations:
        payload = get_journey_payload(
            origin["extId"], origin["name"],
            destination["extId"], destination["name"],
            search_date, search_time,
        )
        payload["_origin_extid"] = origin["extId"]
        payload["_origin_name"] = origin["name"]
        payload["_dest_extid"] = destination["extId"]
        payload["_dest_name"] = destination["name"]
        payload["_date"] = search_date
        payload["_time"] = search_time

        response = fetch_trips_with_scroll(_session, BASE_URL, HEADERS, payload, min_connections=30)

        if not response or response.get("err") != "OK":
            continue
        svc_res = response.get("svcResL", [{}])[0]
        if svc_res.get("err") != "OK":
            continue
        for connection in simplify_trip_response(response):
            connection["destination"] = destination["name"]
            connections.append(connection)

    if not connections:
        return []

    return refine_connections(connections, reference_minutes)