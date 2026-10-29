#!/usr/bin/env python3
"""Script to query the HAFAS TripSearch API and write response to a file."""

import json
import os
import requests

BASE_URL = "https://fahrplan.oebb.at/bin/mgate.exe"
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

payload = {
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
            "meth": "TripSearch",
            "req": {
                "depLocL": [{"type": "S", "lid": "A=1@O=Salzburg Volksgarten@L=591161@"}],
                "arrLocL": [{"type": "S", "lid": "A=1@O=Wien Hbf@L=8103000@"}],
                "outDate": "20261020",
                "outTime": "130000",
                "outFrwd": True,
                "numF": 5,
                "maxChg": 3,
                "minChgTime": 0,
                "jnyFltrL": [{"type": "PROD", "mode": "INC", "value": "65535"}],
                "getPasslist": True,
                "getPolyline": False,
                "getPT": True,
                "getIV": False,
                "getTariff": False,
            },
        }
    ],
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "response.json")

response = requests.post(BASE_URL, json=payload, headers=HEADERS)
response.raise_for_status()

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(response.json(), f, indent=2, ensure_ascii=False)

print(f"Response written to {OUTPUT_FILE}")
