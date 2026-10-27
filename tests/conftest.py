"""Shared test helpers.

Tests check rules that hold for any seed data (filters respected, nearest first,
nothing outside the radius) instead of expecting specific addresses, so adding
or regenerating listings doesn't break them.
"""
import psycopg
import pytest
from psycopg.rows import dict_row

from api.main import DATABASE_URL


@pytest.fixture
def db():
    """Run a query straight against the database, to check what the API returned."""
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        def query(sql, params=None):
            return conn.execute(sql, params or {}).fetchall()
        yield query


@pytest.fixture
def ids_within(db):
    """Ids of listings within `radius` metres of a point, matching an optional SQL condition."""
    def ids_within(lat, lon, radius, where="TRUE", params=None):
        rows = db(
            f"""SELECT id FROM listings
                WHERE ST_DWithin(location, ST_MakePoint(%(lon)s, %(lat)s)::geography, %(radius)s)
                  AND {where}""",
            {"lat": lat, "lon": lon, "radius": radius, **(params or {})},
        )
        return {row["id"] for row in rows}
    return ids_within
