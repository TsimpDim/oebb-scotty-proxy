from transport.scotty import BASE_PAYLOAD, STATIONS
import re

def get_station_by_extid(station_id: str) -> dict:
    """
    Retrieve station information based on the external ID.

    Args:
        station_id (str): The external ID of the station.

    Returns:
        dict: A dictionary containing the station's name and city.
              Returns None if the station is not found.
    """
    for station in STATIONS:
        if station["extId"] == station_id:
            return station
    return None

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

def format_time(time_str: str) -> str:
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

        simplified_journey['planned_time'] = format_time(planned_time_raw)
        simplified_journey['predicted_time'] = format_time(predicted_time_raw)
        simplified_journey['direction'] = "Outbound" if journey.get("dirFlg", "") == 'H' else "Inbound"
        simplified_journey['loc_x'] = journey.get('pos', {'x': None})['x']
        simplified_journey['loc_y'] = journey.get('pos', {'y': None})['y']
        simplified_journey['delayed'] = planned_time_raw != predicted_time_raw
        simplified_journey['delay_minutes'] = (int(predicted_time_raw) - int(planned_time_raw))/100
        simplified_journeys.append(simplified_journey)

    return simplified_journeys

def get_journey_payload(
    origin_extid: str,
    origin_name: str,
    dest_extid: str,
    dest_name: str,
    date: str | None = None,
    time: str | None = None,
    num_journeys: int = 10,
    max_changes: int = 2,
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

    Returns:
        dict: A dictionary representing the TripSearch payload.
    """
    req = {
        "depLocL": [{"lid": f"A=1@O={origin_name}@L={origin_extid}@", "type": "S"}],
        "arrLocL": [{"lid": f"A=1@O={dest_name}@L={dest_extid}@", "type": "S"}],
        "outFrwd": True,
        "numF": num_journeys,
        "maxChg": max_changes,
        "jnyFltrL": [{"type": "PROD", "mode": "INC", "value": "1023"}],
        "getPasslist": True,
        "getPolyline": False,
        "getPT": True,
        "getIV": False,
    }
    if date:
        req["outDate"] = date
    if time:
        req["outTime"] = time

    payload = BASE_PAYLOAD.copy()
    payload["svcReqL"] = [{"meth": "TripSearch", "req": req}]
    return payload

def _resolve(common: dict, key: str, index: int | None) -> dict | None:
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

def _delay_minutes(scheduled: str | None, realtime: str | None) -> int | None:
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

def _platform(stop: dict, prefix: str) -> str | None:
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

def _time_detail(scheduled: str | None, realtime: str | None, platform: str | None) -> dict:
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
        "planned_time": format_time(scheduled) if scheduled else None,
        "predicted_time": format_time(realtime) if realtime else None,
        "platform": platform,
        "delayed": bool(scheduled and realtime and scheduled != realtime),
        "delay_minutes": _delay_minutes(scheduled, realtime),
    }

def _stop_detail(common: dict, stop: dict, prefix: str) -> dict:
    """
    Build a station and time detail dict for a departure or arrival stop.

    Args:
        common (dict): The common reference tables from the API response.
        stop (dict): A stop object from the API response.
        prefix (str): 'd' for departure or 'a' for arrival.

    Returns:
        dict: A dictionary with station info and time details.
    """
    loc = _resolve(common, "locL", stop.get("locX"))
    scheduled = stop.get(f"{prefix}TimeS")
    realtime = stop.get(f"{prefix}TimeR", scheduled)
    detail = {
        "station": loc.get("name") if loc else None,
    }
    detail.update(_time_detail(scheduled, realtime, _platform(stop, prefix)))
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
    product = _resolve(common, "prodL", journey.get("prodX"))

    return {
        "departure": _stop_detail(common, section.get("dep", {}), "d"),
        "arrival": _stop_detail(common, section.get("arr", {}), "a"),
        "line": product.get("name") if product else None,
        "cls": product.get("cls") if product else None,
        "category": (product.get("prodCtx") or {}).get("catOutL") if product else None,
        "direction": journey.get("dirTxt"),
        "status": journey.get("status"),
        "duration": _format_duration(journey.get("durS")),
    }

def simplify_trip_response(response: dict) -> list:
    """
    Simplify a TripSearch API response into connections with legs.

    Args:
        response (dict): The raw response from the API.

    Returns:
        list: A list of simplified connection dictionaries.
    """
    res = response.get("svcResL", [{}])[0].get("res", {})
    common = res.get("common", {})

    connections = []
    for connection in res.get("outConL", []):
        legs = []
        for section in connection.get("secL", []):
            if section.get("type") == "JNY":
                leg = _parse_leg(common, section)
                if leg:
                    legs.append(leg)
        connections.append({
            "departure": _stop_detail(common, connection.get("dep", {}), "d"),
            "arrival": _stop_detail(common, connection.get("arr", {}), "a"),
            "changes": connection.get("chg"),
            "legs": legs,
        })

    return connections


SALZBURG_VOLKSGARTEN = "Salzburg Volksgarten"
SALZBURG_PARSCH = "Salzburg Parsch Bahnhst"
O_BUS_6 = "O-Bus 6"
LONG_DISTANCE_CLASSES = {1, 2, 4}


def _first_leg(connection: dict) -> dict | None:
    legs = connection.get("legs", [])
    return legs[0] if legs else None


def _main_leg(connection: dict) -> dict | None:
    """
    Return the long-distance rail leg of a connection.

    Falls back to the last leg when no intercity/railjet leg is present.
    """
    legs = connection.get("legs", [])
    for leg in legs:
        if leg.get("cls") in LONG_DISTANCE_CLASSES:
            return leg
    return legs[-1] if legs else None


def _starts_from(connection: dict, station: str) -> bool:
    first = _first_leg(connection)
    if not first:
        return False
    return first.get("departure", {}).get("station") == station


def _is_obus6_from_volksgarten(connection: dict) -> bool:
    first = _first_leg(connection)
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


def refine_connections(connections: list, reference_minutes: int | None = None) -> list:
    """
    Filter, deduplicate and prioritize a list of trip connections.

    - Removes connections starting from Salzburg Parsch Bahnhst.
    - Keeps only one connection per destination line (long-distance rail
      leg, falling back to the last leg).
    - Orders chronologically by departure, breaking ties in favour of
      connections starting with O-Bus 6 from Salzburg Volksgarten.

    Args:
        connections (list): Simplified connection dicts (with a
            'destination' label set).
        reference_minutes (int | None): Minutes since midnight of the
            search reference time. Departures earlier than this are treated
            as occurring the next day (midnight rollover).

    Returns:
        list: The filtered, deduplicated and sorted connections.
    """
    filtered = [c for c in connections if not _starts_from(c, SALZBURG_PARSCH)]

    seen = set()
    deduped = []
    for connection in filtered:
        main = _main_leg(connection)
        key = (connection.get("destination"), main.get("line") if main else None)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(connection)

    def sort_key(connection: dict) -> tuple:
        departure = _departure_minutes(connection)
        if departure is None:
            departure = 10**9
        elif reference_minutes is not None and departure < reference_minutes:
            departure += 24 * 60
        return (departure, 0 if _is_obus6_from_volksgarten(connection) else 1)

    return sorted(deduped, key=sort_key)