# ÖBB HAFAS (`mgate.exe`) API Field Reference

This document provides a breakdown of the JSON structures returned by the HaCon HAFAS RPC gateway (`mgate.exe`) used by ÖBB SCOTTY and regional transport web applications.

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