from fastapi import FastAPI
import requests as r
from datetime import datetime
from transport.scotty import STATIONS, BASE_URL, HEADERS
from transport.utils import get_station_by_extid, get_payload, simplify_response, get_journey_payload, simplify_trip_response, refine_connections
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
    station = get_station_by_extid(station_id)
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
    origin = get_station_by_extid("591161")
    if not origin:
        return {"error": "Origin station not found."}

    destinations = [
        get_station_by_extid("8103000"),   # Wien Hbf
        get_station_by_extid("8101003"),   # Wien Westbahnhof
    ]
    destinations = [d for d in destinations if d]
    if not destinations:
        return {"error": "Destination stations not found."}

    connections = []
    for destination in destinations:
        payload = get_journey_payload(
            origin["extId"], origin["name"],
            destination["extId"], destination["name"],
            date, time,
        )
        data = r.post(BASE_URL, json=payload, headers=HEADERS)

        if data.status_code != 200:
            continue
        for connection in simplify_trip_response(data.json()):
            connection["destination"] = destination["name"]
            connections.append(connection)

    if not connections:
        return {"error": "Failed to fetch data from the API."}

    if time and len(time) >= 4 and time[:4].isdigit():
        reference_minutes = int(time[:2]) * 60 + int(time[2:4])
    else:
        now = datetime.now()
        reference_minutes = now.hour * 60 + now.minute

    return refine_connections(connections, reference_minutes)