# ÖBB HAFAS (`mgate.exe`) API Field Reference

This document describes the HaCon HAFAS RPC gateway (`mgate.exe`) used by ÖBB SCOTTY and regional transport web applications — the request envelope, the available methods, the native filtering options, and a breakdown of the JSON response structures.

---

## 1. Journey Object (`jnyL[]` Element)

The primary object representing a vehicle run or station departure leg.

| Field | Data Type | Example Value | Description |
| :--- | :--- | :--- | :--- |
| `jid` | String | `2\|#VN#1#ST#17...` | **Journey Context Key (`ctxRecon`):** Serialized token containing complete trip metadata. |
| `date` | String | `"20260904"` | Operational date of the journey in `YYYYMMDD` format. |
| `trainStartDate` | String | `"20260904"` | The date when the vehicle commenced its initial run from its origin terminus. |
| `prodX` | Integer | `8` | Index pointing to the product definition in the root `common.prodL` array. |
| `dirTxt` | String | `"Parsch"` | Destination name displayed on the front of the vehicle. |
| `dirFlg` | String | `"R"` | **Direction Flag:** Shorthand for route orientation (`H` = Outbound, `R` = Inbound). |
| `status` | String | `"P"` | **Operational Status:** (`P` = Planned, `R` = Real-time, `C` = Canceled, `A` = Additional). |
| `isRchbl` | Boolean | `true` | **Reachability Flag:** `true` if the connection is achievable based on live telemetry. |
| `subscr` | String | `"F"` | Subscription flag for push notifications (`T` = True, `F` = False). |
| `sumLDrawStyleX` | Integer | `0` | Reference index for summary map line rendering styles. |
| `resLDrawStyleX` | Integer | `1` | Reference index for detailed map line rendering styles. |

---

## 2. HAFAS Context Key (`jid` / `ctxRecon`) Token Specification

The `jid` string uses `#` delimiters to encode trip state information without maintaining server sessions:

| Tag | Name | Example | Decoded Meaning |
| :--- | :--- | :--- | :--- |
| `2\|` | Version | `2` | Serialization schema version. |
| `#ST#` | Server State | `1788424467` | Timetable state epoch timestamp. |
| `#ZI#` | Zug-ID | `74916` | Internal HAFAS vehicle dispatch run number. |
| `#DA#` | Date Code | `40926` | Date representation (`DMMYY`). |
| `#1S#` / `#LS#` | First/Last Station | `591064` / `591121` | Station EVA IDs for vehicle origin and terminus. |
| `#1T#` / `#LT#` | First/Last Time | `1331` / `1402` | Origin departure (13:31) and terminus arrival (14:02). |
| `#PU#` | Provider Unit | `81` | Country/Transit Authority code (`81` = Austria / ÖBB / SVV). |
| `#RT#` | Real-Time | `1` | Real-time GPS tracking status (`1` = Active). |
| `#CA#` | Category | `"obu"` | Vehicle class shorthand (`obu` = Oberleitungsbus / Trolleybus). |
| `#ZE#` / `#ZB#` | Line Identifier | `6` / `"O-Bus 6 "` | Line number and display label. |
| `#PC#` | Product Class | `6` | HAFAS mode index (`6` = Bus / Trolleybus). |
| `#FR#` / `#TO#` | Leg From/To | `591064` / `591121` | Station IDs for the requested journey segment. |
| `#FT#` / `#TT#` | Leg Times | `1331` / `1402` | Boarding and alighting times for the segment. |

---

## 3. Station Board Stop Details (`stbStop`)

Contains real-time arrival/departure timings and platform info for the queried station.

| Field | Data Type | Example Value | Description |
| :--- | :--- | :--- | :--- |
| `locX` | Integer | `2` | Index pointing to the station location object in `common.locL[]`. |
| `idx` | Integer | `15` | Sequential stop number along the vehicle's full route sequence. |
| `dProdX` | Integer | `8` | Product index for departure mode resolution. |
| `dTimeS` | String | `"135500"` | **Scheduled Time:** Format `HHMMSS` (13:55:00). |
| `dTimeR` | String | `"135600"` | **Real-Time Predicted Time:** Format `HHMMSS` (13:56:00). |
| `dTimeFS` | Object | `{"styleX": 0}` | UI style index for scheduled time display. |
| `dTimeFR` | Object | `{"txtA": "1 Minuten später"}` | Formatted real-time text label (e.g., delay notices). |
| `dProgType` | String | `"PROGNOSED"` | Delay source (`PROGNOSED` = GPS calculation, `MANUAL` = Dispatcher entry). |
| `dTZOffset` | Integer | `120` | UTC offset in minutes (`120` = CEST / UTC+2). |
| `type` | String | `"N"` | Node stop classification (`N` = Normal stop, `S` = Primary Station). |

---

## 4. Spatial Position (`pos`)

Encodes geographic location in WGS84 coordinates.

| Field | Data Type | Example Value | Decoded Formula / Meaning |
| :--- | :--- | :--- | :--- |
| `x` | Integer | `13043555` | Longitude $\div 1,000,000$ $\rightarrow$ **13.043555° E** |
| `y` | Integer | `47804293` | Latitude $\div 1,000,000$ $\rightarrow$ **47.804293° N** |

---

## 5. Messages and Remarks (`msgL[]`)

Contains pointers to service warnings, accessibility notices, or detour alerts.

| Field | Data Type | Example Value | Description |
| :--- | :--- | :--- | :--- |
| `type` | String | `"REM"` | Message source type (`REM` = Remark, `HIM` = Hazard Information Module). |
| `remX` | Integer | `0` | Index pointing to the full text remark in `common.remL[]`. |
| `sty` | String | `"I"` | Notice severity level (`I` = Info, `W` = Warning, `E` = Error). |
| `fLocX` | Integer | `2` | Start station index in `common.locL[]` where message applies. |
| `tLocX` | Integer | `8` | End station index in `common.locL[]` where message applies. |
| `tagL` | Array[String]| `["RES_JNY_DTL"]` | HAFAS UI context tags specifying where to display the message. |
| `sort` | Integer | `268435456` | Display priority bitmask for sorting notices in clients. |

---

## 6. Product Segment List (`prodL[]`)

Maps route segments to vehicle categories.

| Field | Data Type | Example Value | Description |
| :--- | :--- | :--- | :--- |
| `prodX` | Integer | `8` | Reference index in `common.prodL[]`. |
| `fLocX` | Integer | `2` | Starting location index for this product configuration. |
| `tLocX` | Integer | `8` | Ending location index for this product configuration. |
| `fIdx` | Integer | `15` | Starting stop index sequence number. |
| `tIdx` | Integer | `20` | Ending stop index sequence number. |

---

## 7. Request Envelope

Every request is an HTTP `POST` to `https://fahrplan.oebb.at/bin/mgate.exe` with a JSON body:

```json
{
  "id": "1",
  "ver": "1.67",
  "lang": "deu",
  "auth": {"type": "AID", "aid": "OWDL4fE4ixNiPBBm"},
  "client": {"id": "OEBB", "type": "WEB", "name": "webapp", "l": "vs_webapp"},
  "formatted": false,
  "svcReqL": [
    {"meth": "StationBoard", "req": { }}
  ]
}
```

`svcReqL` is an array of service requests; each entry is `{"meth": "...", "req": {...}}`. `meth` selects the RPC. Known methods:

| Method | Purpose |
| :--- | :--- |
| `LocMatch` | Search stations/stops/POIs by name. |
| `StationBoard` | Departure/arrival board at a station. |
| `TripSearch` | Journey planning between two locations. |
| `JourneyDetails` | Full details of a journey via its `jid`/`ctxRecon`. |
| `HimSearch` | Service alerts / disruptions. |

---

## 8. Location Identifiers

Locations appear in two forms:

- `extId` — the numeric station ID: either a local ID (e.g. `591161`) or an EVA number (e.g. `8103000`).
- `lid` — a fully-qualified location string: `A=1@O=<name>@L=<extId>@` (optionally extended with `@X=..@Y=..@U=..@p=..` coordinates).

For `TripSearch` the endpoint accepts the short `lid` form; the resolved `common.locL[]` entry then contains the full form with coordinates. A location object is either `{"type": "S", "lid": "..."}` or `{"type": "S", "name": "...", "extId": "..."}`.

Verified station IDs (`fahrplan.oebb.at`):

| Station | extId |
| :--- | :--- |
| Salzburg Volksgarten | `591161` |
| Salzburg Hbf | `8100002` |
| Wien Hbf | `8103000` |
| Wien Meidling | `8100514` |
| Linz/Donau Hbf | `8100013` |
| St.Pölten Hbf | `8100008` |
| Graz Hbf | `8100173` |
| Innsbruck Hbf | `8100108` |
| Klagenfurt Hbf | `8100085` |
| Wels Hbf | `8100014` |
| Wr.Neustadt Hbf | `8100516` |

---

## 9. Filtering — StationBoard

`StationBoard` supports several native filters; there is no need to fetch all departures and filter client-side.

| Field | Type | Description |
| :--- | :--- | :--- |
| `type` | `"DEP"` / `"ARR"` | Departures or arrivals. |
| `stbLoc` | Location | The station to query. |
| `dirLoc` | Location (optional) | **Destination filter** — only journeys whose destination matches this location. |
| `maxJny` | Integer | Maximum journeys to return. |
| `date` / `time` | `YYYYMMDD` / `HHMMSS` | Start of the board window. |
| `dur` | Integer | Window length in minutes. |
| `jnyFltrL` | Array | Product filter (see §10). |
| `stbFltrEquiv` | Boolean | Exclude equivalent stops (older profiles). |

Example — departures from Salzburg Hbf toward Wien Hbf:

```json
{
  "meth": "StationBoard",
  "req": {
    "type": "DEP",
    "stbLoc": {"type": "S", "name": "Salzburg Hbf", "extId": "8100002"},
    "dirLoc": {"type": "S", "name": "Wien Hbf", "extId": "8103000"},
    "maxJny": 40
  }
}
```

`dirLoc` matches the vehicle's final destination (its `dirTxt`/`dirFlg`), not intermediate stops — a train continuing past the filter station will not match.

---

## 10. Product Filtering (`jnyFltrL`)

`jnyFltrL` accepts entries of the form `{"type": "PROD", "mode": "INC", "value": "<bitmask>"}`. The bitmask is the sum of product-class bits; `mode` is `INC` (include) or `BIT` (exact bitmask match).

Product-class bits (verified from `common.prodL[].cls` / `icoL[]`):

| Bit | Value | Product |
| :--- | :--- | :--- |
| 0 | 1 | Railjet / high-speed |
| 1 | 2 | Night train |
| 2 | 4 | Intercity / Eurocity |
| 3 | 8 | Regional |
| 4 | 16 | Commuter rail |
| 5 | 32 | S-Bahn |
| 6 | 64 | Bus / trolleybus |
| 7 | 128 | U-Bahn (metro) |
| 8 | 256 | Tram |
| 9 | 512 | Rail replacement (SEV) |
| 10 | 1024 | Generic |
| 11 | 2048 | Taxi / cable car |

- `1023` = all regular products (bits 0–9).
- `63` = rail only (bits 0–5: high-speed through S-Bahn); `191` adds metro.

Other filter types can be appended, e.g. `{"type": "META", "mode": "INC", "meta": "..."}` for accessibility, or `{"type": "BC", "mode": "INC"}` for bicycle carriage.

Note: the `#PC#` tag inside a `jid` uses a separate legacy numbering and must not be confused with `common.prodL[].cls`.

---

## 11. TripSearch — Journey Planning

### Request

```json
{
  "meth": "TripSearch",
  "req": {
    "depLocL": [{"type": "S", "lid": "A=1@O=Salzburg Volksgarten@L=591161@"}],
    "arrLocL": [{"type": "S", "lid": "A=1@O=Wien Hbf@L=8103000@"}],
    "outDate": "20261020",
    "outTime": "130000",
    "outFrwd": true,
    "numF": 5,
    "maxChg": 3,
    "minChgTime": 0,
    "jnyFltrL": [{"type": "PROD", "mode": "INC", "value": "1023"}],
    "getPasslist": true,
    "getPolyline": false,
    "getPT": true,
    "getIV": false,
    "getTariff": false
  }
}
```

| Field | Type | Description |
| :--- | :--- | :--- |
| `depLocL` / `arrLocL` | Array[Location] | Origin / destination (arrays allow alternatives, e.g. several Vienna stations). |
| `viaLocL` | Array | Optional via stations: `[{"loc": {"type": "S", "lid": "..."}}]`. |
| `outDate` / `outTime` | `YYYYMMDD` / `HHMMSS` | Search date/time. Omitted → defaults to *now*. |
| `outFrwd` | Boolean | `true` = depart after `outTime`; `false` = arrive by `outTime`. |
| `numF` | Integer | Max connections to return. |
| `maxChg` | Integer | Max transfers (`-1` = unlimited). |
| `minChgTime` | Integer | Minimum transfer time in minutes. |
| `jnyFltrL` | Array | Product / meta filters (see §10). |
| `getPasslist` | Boolean | Include intermediate stopovers per leg. |
| `getPolyline` | Boolean | Include route geometry (requires `cfg.polyEnc = "GPA"`). |
| `getTariff` | Boolean | Include fares. |
| `getPT` / `getIV` | Boolean | Include public-transport / individual (walking) legs. |
| `ctxScr` | String | Paging context for earlier/later connections. |

### Response

```
svcResL[0].res
├── common
│   ├── locL[]    stations, indexed by locX
│   ├── prodL[]   lines/trains, indexed by prodX  (.name, .cls, .prodCtx.catOutL)
│   ├── dirL[]    direction texts, indexed by dirX (optional)
│   ├── remL[]    remarks
│   ├── opL[]     operators
│   └── himL[]    HIM alerts
└── outConL[]      one entry per connection
    ├── date                      YYYYMMDD
    ├── dep  { locX, dTimeS, dTimeR, dPltfS }
    ├── arr  { locX, aTimeS, aTimeR, aPltfS }
    ├── dur                        "HHMMSS" total duration
    ├── chg                        number of transfers
    ├── secL[]                     legs of this connection
    │   ├── type                   "JNY" | "WALK" | "TRSF"
    │   ├── jny   { jid, prodX, dirTxt, status, stopL[] }   (JNY only)
    │   ├── gis   { dist, durS }                            (WALK only)
    │   ├── dep   { locX, dTimeS, dTimeR, dPltfS }
    │   └── arr   { locX, aTimeS, aTimeR, aPltfS }
    └── ctxRecon                  token to refresh this connection
```

`locX`/`prodX`/`dirX` are indices into the `common` reference tables, not inline values. Paging refs are returned as `outCtxScrB` / `outCtxScrF` (send one back as `ctxScr`).