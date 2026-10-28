from fastapi import FastAPI
import requests as r
from datetime import datetime
from transport.scotty import STATIONS, BASE_URL, HEADERS
from transport.utils import get_payload, simplify_response, get_journey_payload, simplify_trip_response, refine_connections
from fastapi import Depends
from transport.auth import handle_api_key

app = FastAPI(dependencies=[
    Depends(handle_api_key),
])

def dev() -> None:
    import uvicorn

    uvicorn.run("transport.main:app", host="127.0.0.1", port=8000, reload=True)

@app.get("/stations")
def read_stations():
    return STATIONS

@app.get("/stations/{station_id}")
def read_station(station_id: str):
    station = STATIONS.get(station_id)
    payload = get_payload(station['extId'], station["name"]) if station else None
    if payload:
        data = r.post(
            BASE_URL,
            json=payload,
            headers=HEADERS,
        )

        if data.status_code == 200:
            return simplify_response(data.json())
        else:
            return {"error": "Failed to fetch data from the API."}
    else:
        return {"error": "Station not found."}

@app.get("/journeys/vienna")
def read_journeys_vienna(date: str | None = None, time: str | None = None):
    origin = STATIONS.get("591161")
    if not origin:
        return {"error": "Origin station not found."}

    now = datetime.now()
    search_date = date or now.strftime("%Y%m%d")
    search_time = time or now.strftime("%H%M%S")
    reference_minutes = int(search_time[:2]) * 60 + int(search_time[2:4])

    destinations = [
        STATIONS.get("8103000")   # Wien Hbf
    ]
    destinations = [d for d in destinations if d]
    if not destinations:
        return {"error": "Destination stations not found."}

    connections = []
    for destination in destinations:
        payload = get_journey_payload(
            origin["extId"], origin["name"],
            destination["extId"], destination["name"],
            search_date, search_time,
        )
        data = r.post(BASE_URL, json=payload, headers=HEADERS)

        if data.status_code != 200:
            continue
        for connection in simplify_trip_response(data.json()):
            connection["destination"] = destination["name"]
            connections.append(connection)

    if not connections:
        return {"error": "Failed to fetch data from the API."}

    return refine_connections(connections, reference_minutes)