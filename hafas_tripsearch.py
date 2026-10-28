#!/usr/bin/env python3
"""Script to query the HAFAS TripSearch API."""

import requests
from src.transport.scotty import BASE_URL, HEADERS

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
                "jnyFltrL": [{"type": "PROD", "mode": "INC", "value": "1023"}],
                "getPasslist": True,
                "getPolyline": False,
                "getPT": True,
                "getIV": False,
                "getTariff": False,
            },
        }
    ],
}

response = requests.post(BASE_URL, json=payload, headers=HEADERS)
response.raise_for_status()

import json
print(json.dumps(response.json(), indent=2, ensure_ascii=False))
