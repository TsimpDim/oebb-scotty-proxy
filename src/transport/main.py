from fastapi import FastAPI
import requests as r
from transport.scotty import STATIONS, BASE_URL, HEADERS
from transport.utils import get_station_by_extid, get_payload, simplify_response
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