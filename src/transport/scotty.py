BASE_URL = "https://fahrplan.oebb.at/bin/mgate.exe"

BASE_PAYLOAD = {
    "id": "1",
    "ver": "1.67",
    "lang": "deu",
    "auth": {"type": "AID", "aid": "OWDL4fE4ixNiPBBm"},
    "client": {
        "id": "OEBB",
        "type": "WEB",
        "name": "webapp",
        "l": "vs_webapp",
    },
    "formatted": False,
    "svcReqL": [
        {
            "meth": "StationBoard",
            "req": {
                "type": "DEP",
                "stbLoc": {
                    "type": "S",
                    "name": "$station_name$",
                    "extId": "$station_id$",
                },
                "maxJny": 15,
            },
        }
    ],
}

HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

STATIONS =  [
    {"name": "Salzburg Volksgarten", "extId": "591161", "city": "Salzburg"},
    {"name": "Wien Hbf", "extId": "8103000", "city": "Wien"},
]
