import os

import httpx

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

# Results are biased toward Greater Vancouver (south-west, north-east corners)
# and limited to Canada.
VANCOUVER_BOUNDS = "49.00,-123.30|49.40,-122.90"

# When Google can't find a place it falls back to the whole city, province or
# country and marks it partial_match. Those are too broad to search around.
TOO_BROAD = {"locality", "administrative_area_level_1", "administrative_area_level_2", "country"}


class GeocodeError(Exception):
    """The place could not be turned into coordinates."""


def geocode(place: str) -> tuple[float, float]:
    """Return (lat, lon) for a place name like "Commercial Drive"."""
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise GeocodeError("GOOGLE_MAPS_API_KEY is not set in .env")

    # "Main St" alone can match the North Shore's Main St; adding the city picks
    # Vancouver's. A place that already names its city ("Metrotown, Burnaby") is left as is.
    address = place if "," in place else f"{place}, Vancouver, BC"

    response = httpx.get(
        GEOCODE_URL,
        params={
            "address": address,
            "bounds": VANCOUVER_BOUNDS,
            "components": "country:CA",
            "key": api_key,
        },
        timeout=5,
    )
    response.raise_for_status()
    data = response.json()

    # Google reports problems in "status" even when the HTTP request succeeds.
    if data["status"] == "ZERO_RESULTS":
        raise GeocodeError(f'Could not find "{place}"')
    if data["status"] != "OK":
        raise GeocodeError(f"Geocoding failed: {data['status']} {data.get('error_message', '')}".strip())

    result = data["results"][0]
    if result.get("partial_match") and TOO_BROAD & set(result["types"]):
        raise GeocodeError(f'Could not find "{place}"')

    location = result["geometry"]["location"]
    return location["lat"], location["lng"]
