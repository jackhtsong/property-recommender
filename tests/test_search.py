import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

# Near Robson & Burrard, downtown Vancouver.
DOWNTOWN = {"lat": 49.2827, "lon": -123.1207}
MAX_RESULTS = 50  # the LIMIT in the search query


def search(**params):
    response = client.get("/search", params=params)
    assert response.status_code == 200
    return response.json()


def test_returns_nearby_listings_nearest_first():
    results = search(**DOWNTOWN)
    assert len(results) > 0
    distances = [r["distance_m"] for r in results]
    assert distances == sorted(distances)
    assert all(d <= 3000 for d in distances)


def test_finds_every_listing_in_a_small_radius(ids_within):
    # Small enough that the 50-result limit can't hide anything.
    expected = ids_within(**DOWNTOWN, radius=800)
    assert 0 < len(expected) < MAX_RESULTS
    assert {r["id"] for r in search(**DOWNTOWN, radius=800)} == expected


def test_result_limit_keeps_the_nearest(ids_within):
    if len(ids_within(**DOWNTOWN, radius=20000)) <= MAX_RESULTS:
        pytest.skip(f"needs more than {MAX_RESULTS} listings in the database")
    results = search(**DOWNTOWN, radius=20000)
    assert len(results) == MAX_RESULTS
    # Everything left out must be at least as far away as the farthest result.
    farthest = results[-1]["distance_m"]
    closer_than_farthest = ids_within(**DOWNTOWN, radius=farthest - 1)
    assert closer_than_farthest <= {r["id"] for r in results}


def test_bedrooms_min_filter(ids_within):
    results = search(**DOWNTOWN, radius=1500, bedrooms_min=2)
    assert len(results) > 0
    assert all(r["bedrooms"] >= 2 for r in results)
    assert {r["id"] for r in results} == ids_within(**DOWNTOWN, radius=1500, where="bedrooms >= 2")


def test_price_max_and_property_type_filters(ids_within):
    results = search(**DOWNTOWN, radius=1500, price_max=800000, property_type="condo")
    assert len(results) > 0
    assert all(r["property_type"] == "condo" and r["price"] <= 800000 for r in results)
    expected = ids_within(**DOWNTOWN, radius=1500, where="property_type = 'condo' AND price <= 800000")
    assert {r["id"] for r in results} == expected


def test_no_matches_returns_empty_list():
    # Out in the Pacific Ocean, nowhere near any listing.
    assert search(lat=49.0, lon=-125.0, radius=1000) == []


def test_missing_lat_is_rejected():
    response = client.get("/search", params={"lon": -123.1207})
    assert response.status_code == 422


def test_out_of_range_lat_is_rejected():
    response = client.get("/search", params={"lat": 500, "lon": -123.1207})
    assert response.status_code == 422


def test_unknown_property_type_is_rejected():
    params = {**DOWNTOWN, "property_type": "castle"}
    response = client.get("/search", params=params)
    assert response.status_code == 422
