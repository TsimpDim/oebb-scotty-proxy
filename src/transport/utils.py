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