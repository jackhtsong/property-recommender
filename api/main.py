import os
from pathlib import Path
from typing import Literal

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from psycopg.rows import dict_row
from pydantic import BaseModel

from api.geocode import GeocodeError, geocode

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

    params = {
        "lat": lat, "lon": lon, "radius": radius,
        "bedrooms_min": bedrooms_min, "price_max": price_max,
        "property_type": property_type,
    }
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        return conn.execute(SEARCH_SQL, params).fetchall()


# Serve the frontend from web/ at "/". Mounted last so /search and /docs match first.
WEB_DIR = Path(__file__).resolve().parent.parent / "web"
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
