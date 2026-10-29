import re

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from transport.scotty import BASE_PAYLOAD, STATIONS, HEADERS


def get_payload(station_id: str, station_name: str) -> dict:
    """
    Generate a payload for the API request based on the station ID and name.

    Args:
        station_id (str): The ID of the station.
        station_name (str): The name of the station.

    Returns:
        dict: A dictionary representing the payload for the API request.
    """
    payload = BASE_PAYLOAD.copy()
    payload["svcReqL"][0]["req"]["stbLoc"]["extId"] = station_id
    payload["svcReqL"][0]["req"]["stbLoc"]["name"] = station_name
    return payload

def format_time_hh_mm(time_str: str) -> str:
    """
    Format a time string from 'HHMM' to 'HH:MM'.

    Args:
        time_str (str): The time string in 'HHMM' format.

    Returns:
        str: The formatted time string in 'HH:MM' format.
    """
    time_str = time_str[:4]
    if  time_str.isdigit():
        return f"{time_str[:2]}:{time_str[2:]}"
    return time_str

def simplify_response(response: dict) -> list:
    """
    Simplify the API response to extract relevant journey information.

    Args:
        response (dict): The raw response from the API.

    Returns:
        list: A list of simplified journey dictionaries.
    """
    journeys = response.get("svcResL", [{}])[0].get("res", {}).get("jnyL", [])
    simplified_journeys = []
    
    for journey in journeys:
        simplified_journey = {}
        stop_data = journey['stbStop']
        simplified_journey['going_to'] = journey.get("dirTxt", "")

        line_match = re.search(r"\b(?:O-)?Bus\s+\d+\b", journey.get("jid", ""))
        if line_match:
            simplified_journey['line'] = line_match.group(0)

        planned_time_raw = stop_data['dTimeS']
        predicted_time_raw = stop_data.get('dTimeR', planned_time_raw)

        simplified_journey['planned_time'] = format_time_hh_mm(planned_time_raw)
        simplified_journey['predicted_time'] = format_time_hh_mm(predicted_time_raw)
        simplified_journey['direction'] = "Outbound" if journey.get("dirFlg", "") == 'H' else "Inbound"
        simplified_journey['loc_x'] = journey.get('pos', {'x': None})['x']
        simplified_journey['loc_y'] = journey.get('pos', {'y': None})['y']
        simplified_journey['delayed'] = planned_time_raw != predicted_time_raw
        simplified_journey['delay_minutes'] = _get_delay_in_minutes(planned_time_raw, predicted_time_raw)
        simplified_journeys.append(simplified_journey)

    return simplified_journeys

def get_journey_payload(
    origin_extid: str,
    origin_name: str,
    dest_extid: str,
    dest_name: str,
    date: str | None = None,
    time: str | None = None,
    num_journeys: int = 30,
    max_changes: int = 2,
) -> dict:
    """
    Generate a TripSearch payload between two stations.
    """
    return _build_tripsearch_payload(
        origin_extid, origin_name, dest_extid, dest_name,
        date, time, num_journeys, max_changes,
    )


def get_scroll_payload(
    origin_extid: str,
    origin_name: str,
    dest_extid: str,
    dest_name: str,
    scroll_ctx: str,
    date: str | None = None,
    time: str | None = None,
    num_journeys: int = 30,
    max_changes: int = 2,
) -> dict:
    """
    Generate a TripSearch payload with a scroll context for pagination.
    """
    return _build_tripsearch_payload(
        origin_extid, origin_name, dest_extid, dest_name,
        date, time, num_journeys, max_changes,
        scroll_ctx=scroll_ctx,
    )


def _build_tripsearch_payload(
    origin_extid: str,
    origin_name: str,
    dest_extid: str,
    dest_name: str,
    date: str | None = None,
    time: str | None = None,
    num_journeys: int = 20,
    max_changes: int = 2,
    scroll_ctx: str | None = None,
) -> dict:
    """
    Generate a TripSearch payload between two stations.

    Args:
        origin_extid (str): External ID of the origin station.
        origin_name (str): Name of the origin station.
        dest_extid (str): External ID of the destination station.
        dest_name (str): Name of the destination station.
        date (str | None): Search date in YYYYMMDD format.
        time (str | None): Search time in HHMMSS format.
        num_journeys (int): Maximum number of journeys to return.
        max_chg (int): Maximum number of transfers.
        scroll_ctx (str | None): Pagination token from a previous response.

    Returns:
        dict: A dictionary representing the TripSearch payload.
    """
    req = {
        "depLocL": [{"lid": f"A=1@O={origin_name}@L={origin_extid}@", "type": "S"}],
        "arrLocL": [{"lid": f"A=1@O={dest_name}@L={dest_extid}@", "type": "S"}],
        "outFrwd": True,
        "numF": num_journeys,
        "maxChg": max_changes,
        "jnyFltrL": [{"type": "PROD", "mode": "INC", "value": "65535"}],
        "getPasslist": False,
        "getPolyline": False,
        "getPT": True,
        "getIV": False,
    }
    if date:
        req["outDate"] = date
    if time:
        req["outTime"] = time

    if scroll_ctx:
        req["ctxScr"] = scroll_ctx

    payload = BASE_PAYLOAD.copy()
    payload["svcReqL"] = [{"meth": "TripSearch", "req": req}]

    return payload

def _resolve_train_bus_or_stop(common: dict, key: str, index: int | None) -> dict | None:
    """
    Resolve an entry from a common reference list by index.

    Args:
        common (dict): The common reference tables from the API response.
        key (str): The list key to look up (e.g. 'locL', 'prodL').
        index (int | None): The index into the list.

    Returns:
        dict | None: The resolved entry, or None if out of range.
    """
    entries = common.get(key, [])
    if index is None or not isinstance(index, int):
        return None
    if 0 <= index < len(entries):
        return entries[index]
    return None

def _get_delay_in_minutes(scheduled: str | None, realtime: str | None) -> int | None:
    """
    Compute the delay in minutes between scheduled and realtime HHMMSS times.

    Args:
        scheduled (str | None): Scheduled time in HHMMSS format.
        realtime (str | None): Realtime time in HHMMSS format.

    Returns:
        int | None: The delay in minutes, or None if times are missing.
    """
    if not scheduled or not realtime or not scheduled.isdigit() or not realtime.isdigit():
        return None
    if len(scheduled) < 6 or len(realtime) < 6:
        return None
    scheduled_sec = int(scheduled[:2]) * 3600 + int(scheduled[2:4]) * 60 + int(scheduled[4:6])
    realtime_sec = int(realtime[:2]) * 3600 + int(realtime[2:4]) * 60 + int(realtime[4:6])
    return (realtime_sec - scheduled_sec) // 60

def _format_duration(duration: str | None) -> str | None:
    """
    Format a duration string from 'HHMMSS' to 'hh:mm:ss'.

    Args:
        duration (str | None): The duration in HHMMSS format.

    Returns:
        str | None: The formatted duration, or None if missing/invalid.
    """
    if not duration or not duration.isdigit() or len(duration) < 6:
        return duration
    return f"{duration[:2]}:{duration[2:4]}:{duration[4:6]}"

def _get_platform_detail_dict(stop: dict, prefix: str) -> str | None:
    """
    Extract the platform text from a stop object.

    Args:
        stop (dict): A stop object from the API response.
        prefix (str): 'd' for departure or 'a' for arrival.

    Returns:
        str | None: The platform text, or None if not present.
    """
    for key in (f"{prefix}PltfS", f"{prefix}PltfR", f"{prefix}PlatfS", f"{prefix}PlatfR"):
        value = stop.get(key)
        if isinstance(value, dict) and value.get("txt"):
            return value["txt"]
        if isinstance(value, str) and value:
            return value
    return None

def _get_time_detail_dict(scheduled: str | None, realtime: str | None, platform: str | None) -> dict:
    """
    Build a time detail dict with planned/realtime times and delay info.

    Args:
        scheduled (str | None): Scheduled time in HHMMSS format.
        realtime (str | None): Realtime time in HHMMSS format.
        platform (str | None): Platform text.

    Returns:
        dict: A dictionary with formatted times, platform, and delay info.
    """
    realtime = realtime or scheduled
    return {
        "planned_time": format_time_hh_mm(scheduled) if scheduled else None,
        "predicted_time": format_time_hh_mm(realtime) if realtime else None,
        "platform": platform,
        "delayed": bool(scheduled and realtime and scheduled != realtime),
        "delay_minutes": _get_delay_in_minutes(scheduled, realtime),
    }

def _get_stop_detail_dict(common: dict, stop: dict, prefix: str) -> dict:
    """
    Build a station and time detail dict for a departure or arrival stop.

    Args:
        common (dict): The common reference tables from the API response.
        stop (dict): A stop object from the API response.
        prefix (str): 'd' for departure or 'a' for arrival.

    Returns:
        dict: A dictionary with station info and time details.
    """

    # The 'locX' field in the stop references an index into the 'locL' list in 'common'.
    # locL contains location entries, which may be stations, stops, etc.
    # locL contains:
    #   "lid": "A=1@O=Salzburg Volksgarten@X=13061632@Y=47798773@U=81@L=591161@",
    #   "type": "S",
    #   "name": "Salzburg Volksgarten",
    #   "icoX": 0,
    #   "extId": "591161",
    #   "state": "F",
    #   "crd": {
    #     "x": 13061632,
    #     "y": 47798773,
    #     "floor": 0
    #   },
    #   "pCls": 2112,
    #   "chgTime": "000500",
    #   "countryCodeL": [
    #     "at"
    #   ]
    loc = _resolve_train_bus_or_stop(common, "locL", stop.get("locX"))

    scheduled = stop.get(f"{prefix}TimeS")
    realtime = stop.get(f"{prefix}TimeR", scheduled)
    detail = {
        "station": loc.get("name") if loc else None,
    }
    detail.update(_get_time_detail_dict(scheduled, realtime, _get_platform_detail_dict(stop, prefix)))
    return detail

def _parse_leg(common: dict, section: dict) -> dict:
    """
    Parse a single journey (JNY) leg of a connection.

    Args:
        common (dict): The common reference tables from the API response.
        section (dict): A section entry from the connection's secL list.

    Returns:
        dict: A dictionary representing a simplified leg.
    """
    journey = section.get("jny", {})
    
    # The 'prodX' field in the journey references an index into the 'prodL' list in 'common'.
    # By doing common.prodL[prodX] we know what product (train/bus type) this leg is.
    product = _resolve_train_bus_or_stop(common, "prodL", journey.get("prodX"))

    return {
        "departure": _get_stop_detail_dict(common, section.get("dep", {}), "d"),
        "arrival": _get_stop_detail_dict(common, section.get("arr", {}), "a"),
        "line": product.get("name") if product else None,
        "cls": product.get("cls") if product else None,
        "category": (product.get("prodCtx") or {}).get("catOutL") if product else None,
        "direction": journey.get("dirTxt"),
        "status": journey.get("status"),
        "duration": _format_duration(journey.get("durS")),
    }


def _contains_blacklisted_station(legs: list) -> bool:
    """Return True if any leg's departure or arrival station is blacklisted."""
    for leg in legs:
        dep_station = (leg.get("departure") or {}).get("station") or ""
        arr_station = (leg.get("arrival") or {}).get("station") or ""
        for blacklisted in BLACKLISTED_STATIONS:
            if blacklisted in dep_station or blacklisted in arr_station:
                return True
    return False



def _is_valid_connection(legs: list) -> bool:
    """Return True if the connection passes all validity checks."""
    if not legs:
        return False
    if _contains_blacklisted_station(legs):
        return False
    return True

def _connection_signature(connection: dict) -> tuple:
    """Return a stable identity for a connection so page overlaps can be deduped."""
    legs = tuple(
        (
            (leg.get("departure") or {}).get("planned_time"),
            (leg.get("arrival") or {}).get("planned_time"),
            leg.get("line"),
        )
        for leg in connection.get("legs", [])
    )
    return (
        (connection.get("departure") or {}).get("planned_time"),
        (connection.get("arrival") or {}).get("planned_time"),
        connection.get("changes"),
        legs,
    )


def _minutes_ahead(connection: dict, reference_minutes: int) -> int | None:
    """Minutes from the reference time to this connection's departure.

    Departures within the last hour are treated as slightly negative (still
    catchable); anything earlier is rolled forward to the next day.
    """
    departure = _departure_minutes(connection)
    if departure is None:
        return None
    ahead = departure - reference_minutes
    if ahead < -60:
        ahead += 24 * 60
    return ahead


def fetch_trips_with_scroll(
    requests,
    base_url: str,
    headers: dict,
    payload: dict,
    *,
    reference_minutes: int | None = None,
    max_hours: float = 4.0,
    max_pages: int = 12,
    max_connections: int = 200,
) -> list:
    """
    Fetch TripSearch results forward in time, paginating with the forward
    scroll context until connections cover roughly `max_hours` ahead of
    `reference_minutes`, or until `max_pages` / `max_connections` is hit.

    Each page is parsed against its own `common` reference table, so product
    and location indices always resolve correctly across pages.

    Returns:
        list: Simplified connection dicts across all fetched pages.
    """
    all_connections: list = []
    seen: set = set()
    scroll_ctx = None

    meta = {
        "origin_extid": payload.get("_origin_extid"),
        "origin_name": payload.get("_origin_name"),
        "dest_extid": payload.get("_dest_extid"),
        "dest_name": payload.get("_dest_name"),
        "date": payload.get("_date"),
        "time": payload.get("_time"),
    }

    target_ahead = int(max_hours * 60)

    for _page in range(max_pages):
        if scroll_ctx:
            payload = get_scroll_payload(
                meta["origin_extid"],
                meta["origin_name"],
                meta["dest_extid"],
                meta["dest_name"],
                scroll_ctx=scroll_ctx,
                date=meta["date"],
                time=meta["time"],
                num_journeys=50,
                max_changes=2,
            )

        api_payload = {k: v for k, v in payload.items() if not k.startswith("_")}
        data = requests.post(base_url, json=api_payload, headers=headers, timeout=(5, 30))
        if data.status_code != 200:
            break

        response = data.json()
        svc_res = response.get("svcResL", [])
        if not svc_res or svc_res[0].get("err") != "OK":
            break

        res = svc_res[0].get("res", {})

        for connection in simplify_trip_response(response):
            signature = _connection_signature(connection)
            if signature in seen:
                continue
            seen.add(signature)
            all_connections.append(connection)
            if len(all_connections) >= max_connections:
                break

        if len(all_connections) >= max_connections:
            break

        if reference_minutes is not None:
            max_ahead = max(
                (
                    ahead
                    for c in all_connections
                    if (ahead := _minutes_ahead(c, reference_minutes)) is not None
                ),
                default=None,
            )
            if max_ahead is not None and max_ahead >= target_ahead:
                break

        scroll_ctx = res.get("outCtxScrF")
        if not scroll_ctx:
            break

    return all_connections


def simplify_trip_response(response: dict) -> list:
    """
    Simplify a TripSearch API response into connections with legs.

    Args:
        response (dict): The raw response from the API.

    Returns:
        list: A list of simplified connection dictionaries.
    """
    #svcResL is a top-level object that contains multiple responses (res)
    # 'res' contains stuff life 'common', 'outConL' (list of connections), outCtxScrB, etc.
    res = response.get("svcResL", [{}])[0].get("res", {})

    # The 'common' object contains reference tables for locations, products, etc.
    # Specifically 'locL' for locations, 'prodL' for products, 'opL' for operators, 'remL' for remarks, etc.
    common = res.get("common", {})

    # outConL.secL is a list of sections, each of which may be a leg (JNY) or a footpath (WALK)
    connections = []
    for connection in res.get("outConL", []):
        legs = []
        for section in connection.get("secL", []):
            # We want to explicitly exclude WALK sections, so we only parse JNY ones
            # and add them to a new "legs" list in the simplified connection dict.
            if section.get("type") == "JNY":
                leg = _parse_leg(common, section)
                if leg:
                    legs.append(leg)

        if not _is_valid_connection(legs):
            continue

        connections.append({
            "departure": _get_stop_detail_dict(common, connection.get("dep", {}), "d"),
            "arrival": _get_stop_detail_dict(common, connection.get("arr", {}), "a"),
            "changes": connection.get("chg"),
            "legs": legs,
        })

    return connections


SALZBURG_VOLKSGARTEN = "Salzburg Volksgarten"
SALZBURG_PARSCH = "Parsch Bahnhst"
O_BUS_6 = "O-Bus 6"

# 1 = first class, 2 = second class, 4 = railjet, 6 = intercity
LONG_DISTANCE_CLASSES = {1, 2, 4}

# Stations that, if present in any leg, cause the entire journey to be skipped.
BLACKLISTED_STATIONS = ["Salzburg Parsch Bahnhst", "Bregenz Bahnhof"]

def _get_first_leg(connection: dict) -> dict | None:
    legs = connection.get("legs", [])
    return legs[0] if legs else None


def _leg_is_train(connection: dict) -> dict | None:
    """
    Return the long-distance rail leg of a connection.

    Falls back to the last leg when no intercity/railjet leg is present.
    """
    legs = connection.get("legs", [])
    for leg in legs:
        # cls = class of service
        if leg.get("cls") in LONG_DISTANCE_CLASSES:
            return leg
    return legs[-1] if legs else None


def _connection_starts_from(connection: dict, station_fragment: str) -> bool:
    first = _get_first_leg(connection)
    if not first:
        return False
    name = first.get("departure", {}).get("station") or ""
    return station_fragment in name


def _is_obus6_from_volksgarten(connection: dict) -> bool:
    first = _get_first_leg(connection)
    if not first:
        return False
    return (
        first.get("departure", {}).get("station") == SALZBURG_VOLKSGARTEN
        and first.get("line") == O_BUS_6
    )


def _departure_minutes(connection: dict) -> int | None:
    time_str = (connection.get("departure") or {}).get("predicted_time")
    if not time_str or ":" not in time_str:
        return None
    hours, minutes = time_str.split(":", 1)
    if not hours.isdigit() or not minutes.isdigit():
        return None
    return int(hours) * 60 + int(minutes)


def filter_journeys_by_window(connections: list, now_minutes: int, hours: int = 5) -> list:
    """
    Keep only connections departing between `now_minutes` and
    `now_minutes + hours * 60` minutes since midnight.

    Departures earlier in the day than `now_minutes` are treated as the
    next day (midnight rollover).
    """
    end_minutes = now_minutes + hours * 60
    filtered = []
    for connection in connections:
        departure = _departure_minutes(connection)
        if departure is None:
            filtered.append(connection)
            continue
        if departure < now_minutes:
            departure += 24 * 60
        if now_minutes <= departure < end_minutes:
            filtered.append(connection)
    return filtered


def refine_connections(connections: list, reference_minutes: int | None = None) -> list:
    """
    Filter, deduplicate and prioritize a list of trip connections.

    - Removes connections starting from Salzburg Parsch Bahnhst.    - Keeps only one connection per destination line (long-distance rail
      leg, falling back to the last leg).
    - Orders chronologically by departure, breaking ties in favour of
      connections starting with O-Bus 6 from Salzburg Volksgarten.

    Args:
        connections (list): Simplified connection dicts (with a
            'destination' label set).
        reference_minutes (int | None): Minutes since midnight of the
            search reference time. Departures more than 60 minutes earlier
            than this are treated as occurring the next day (midnight
            rollover); the buffer keeps slightly-past, still-catchable
            connections on the correct day.

    Returns:
        list: The filtered, deduplicated and sorted connections.
    """

    # Filter out connections starting from Salzburg Parsch Bahnhst
    filtered = [c for c in connections if not _connection_starts_from(c, SALZBURG_PARSCH)]

    # Filter out connections that departed more than 60 minutes ago
    if reference_minutes is not None:
        filtered = [
            c for c in filtered
            if _departure_minutes(c) is None
            or _departure_minutes(c) >= reference_minutes - 60
        ]

    seen = set()
    deduped = []
    for connection in filtered:
        main = _leg_is_train(connection)

        main_dep = main.get("departure", {}).get("planned_time") if main else None
        key = (connection.get("destination"), main.get("line"), main_dep)

        # Skip duplicate connections for the same destination and line
        # so if a journey with RX123 has been processed already, only show it once
        if key in seen:
            continue
        seen.add(key)
        deduped.append(connection)

    def sort_key(connection: dict) -> tuple:
        departure = _departure_minutes(connection)
        if departure is None:
            departure = 10**9
        elif reference_minutes is not None and departure < reference_minutes - 60:
            departure += 24 * 60
        return (departure, 0 if _is_obus6_from_volksgarten(connection) else 1)

    return sorted(deduped, key=sort_key)


def fetch_vienna_journeys(
    requests, base_url: str, headers: dict, search_date: str, search_time: str, max_hours: float = 4.0
) -> list:
    """
    Fetch and refine upcoming journeys from Salzburg Volksgarten to Wien Hbf.

    Returns a list of simplified connections spanning roughly `max_hours` into
    the future, or an empty list on failure.
    """
    origin = STATIONS.get("591161")
    destination = STATIONS.get("8103000")
    if not origin or not destination:
        return []

    reference_minutes = int(search_time[:2]) * 60 + int(search_time[2:4])

    payload = get_journey_payload(
        origin["extId"], origin["name"],
        destination["extId"], destination["name"],
        search_date, search_time,
        num_journeys=100,
    )
    payload["_origin_extid"] = origin["extId"]
    payload["_origin_name"] = origin["name"]
    payload["_dest_extid"] = destination["extId"]
    payload["_dest_name"] = destination["name"]
    payload["_date"] = search_date
    payload["_time"] = search_time

    connections = fetch_trips_with_scroll(
        requests, base_url, headers, payload,
        reference_minutes=reference_minutes,
        max_hours=max_hours,
    )
    if not connections:
        return []

    for connection in connections:
        connection["destination"] = destination["name"]

    return refine_connections(connections, reference_minutes)


def make_retrying_session() -> requests.Session:
    """Build a requests.Session with OEBB headers that retries transient failures."""
    session = requests.Session()
    session.headers.update(HEADERS)
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=(500, 502, 503, 504),
        allowed_methods=frozenset(["POST"]),
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session