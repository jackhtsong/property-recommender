import os
from pathlib import Path
from typing import Literal

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from psycopg.rows import dict_row
from pydantic import BaseModel, Field

from api.geocode import GeocodeError, geocode
from api.llm import Filters, LLMError, explain_listings, parse_query

load_dotenv()  # read keys like GOOGLE_MAPS_API_KEY from .env

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/listings")

app = FastAPI(title="Property Recommender")


class Listing(BaseModel):
    id: int
    address: str
    description: str | None
    bedrooms: int | None
    washrooms: float | None
    sqft: int | None
    price: float
    property_type: str
    lat: float
    lon: float
    distance_m: int


# Each optional filter is written as "(value IS NULL OR condition)",
# so a filter you leave out has no effect. The ::int / ::numeric / ::text
# casts tell Postgres the value's type even when it is NULL.
SEARCH_SQL = """
WITH point AS (
  SELECT ST_MakePoint(%(lon)s, %(lat)s)::geography AS geog
)
SELECT
  l.id, l.address, l.description, l.bedrooms, l.washrooms, l.sqft,
  l.price, l.property_type,
  ST_Y(l.location::geometry) AS lat,
  ST_X(l.location::geometry) AS lon,
  round(ST_Distance(l.location, point.geog)) AS distance_m
FROM listings l, point
WHERE ST_DWithin(l.location, point.geog, %(radius)s)
  AND (%(bedrooms_min)s::int IS NULL OR l.bedrooms >= %(bedrooms_min)s)
  AND (%(price_max)s::numeric IS NULL OR l.price <= %(price_max)s)
  AND (%(property_type)s::text IS NULL OR l.property_type = %(property_type)s)
ORDER BY distance_m
LIMIT 50;
"""


@app.get("/search", response_model=list[Listing])
def search(
    near: str | None = Query(None, min_length=2, max_length=200, description="Place name, e.g. Commercial Drive"),
    lat: float | None = Query(None, ge=-90, le=90),
    lon: float | None = Query(None, ge=-180, le=180),
    radius: float = Query(3000, gt=0, le=50000, description="Metres"),
    bedrooms_min: int | None = Query(None, ge=0),
    price_max: int | None = Query(None, gt=0),
    property_type: Literal["condo", "townhouse", "house", "duplex", "loft"] | None = None,
):
    # A place name wins over coordinates; otherwise both lat and lon are needed.
    if near:
        try:
            lat, lon = geocode(near)
        except GeocodeError as error:
            raise HTTPException(status_code=400, detail=str(error))
    elif lat is None or lon is None:
        raise HTTPException(status_code=422, detail="Give either near, or both lat and lon")

    return run_search(lat, lon, radius, bedrooms_min, price_max, property_type)


def run_search(lat, lon, radius, bedrooms_min=None, price_max=None, property_type=None) -> list[dict]:
    params = {
        "lat": lat, "lon": lon, "radius": radius,
        "bedrooms_min": bedrooms_min, "price_max": price_max,
        "property_type": property_type,
    }
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        return conn.execute(SEARCH_SQL, params).fetchall()


# --- Natural-language search with Gemini ---

# With no place in the request, search all of Metro Vancouver from downtown
# (50 km reaches South Surrey).
DOWNTOWN = (49.2827, -123.1207)
CITY_WIDE_RADIUS = 50000
# Near a place: try close first, and widen only if nothing matches, so the
# place always comes first and an empty area still shows its nearest listings.
NEARBY_RADII = (3000, 8000, 20000)
NEARBY_RADIUS = NEARBY_RADII[0]
# A whole city geocodes to one point in its middle, and 3 km around it misses
# most of a big city like Surrey, so cities start wider.
CITY_RADII = (8000, 15000, 25000)
METRO_CITIES = {
    "vancouver", "richmond", "burnaby", "surrey", "new westminster", "coquitlam",
    "north vancouver", "west vancouver", "delta", "langley", "port moody", "white rock",
}


class AskRequest(BaseModel):
    text: str = Field(min_length=2, max_length=500)


class Point(BaseModel):
    lat: float
    lon: float


class AskResponse(BaseModel):
    filters: Filters
    center: Point | None  # the searched place, so the map can mark it; None for city-wide
    radius_m: int  # how far the search reached, after any widening
    results: list[Listing]


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest):
    """'3 bed condo near Kits under 1.5M' -> Gemini filters -> geocode -> search."""
    try:
        filters = parse_query(request.text)
    except LLMError as error:
        raise HTTPException(status_code=502, detail=str(error))

    if filters.near:
        try:
            lat, lon = geocode(filters.near)
        except GeocodeError as error:
            raise HTTPException(status_code=400, detail=str(error))
        is_city = filters.near.lower().removesuffix(", bc").strip() in METRO_CITIES
        radii = CITY_RADII if is_city else NEARBY_RADII
    else:
        lat, lon = DOWNTOWN
        radii = (CITY_WIDE_RADIUS,)

    for radius in radii:
        results = run_search(lat, lon, radius, filters.bedrooms_min, filters.price_max, filters.property_type)
        if results:
            break
    center = {"lat": lat, "lon": lon} if filters.near else None
    return {"filters": filters, "center": center, "radius_m": radius, "results": results}


@app.get("/config")
def config():
    """Settings the browser needs. The browser key is public by design: Google
    locks it to this site and the Maps JavaScript API, so it is safe to hand out.
    The server key (GOOGLE_MAPS_API_KEY) is never sent."""
    return {"maps_browser_key": os.environ.get("GOOGLE_MAPS_BROWSER_KEY")}


class ExplainRequest(BaseModel):
    text: str = Field(min_length=2, max_length=500)
    listing_ids: list[int] = Field(min_length=1, max_length=5)


EXPLAIN_SQL = """
SELECT id, address, description, bedrooms, washrooms, sqft, price, property_type
FROM listings WHERE id = ANY(%(ids)s);
"""


@app.post("/explain")
def explain(request: ExplainRequest) -> dict[int, str]:
    """Why each listing fits the request. Facts come from the database, never the browser."""
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        listings = conn.execute(EXPLAIN_SQL, {"ids": request.listing_ids}).fetchall()
    if not listings:
        raise HTTPException(status_code=404, detail="No listings with those ids")
    try:
        return explain_listings(request.text, listings)
    except LLMError as error:
        raise HTTPException(status_code=502, detail=str(error))


# Serve the frontend from web/ at "/". Mounted last so /search and /docs match first.
WEB_DIR = Path(__file__).resolve().parent.parent / "web"
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
