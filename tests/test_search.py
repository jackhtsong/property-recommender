from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

# Near Robson & Burrard, downtown Vancouver.
DOWNTOWN = {"lat": 49.2827, "lon": -123.1207}


def test_returns_nearby_listings_nearest_first():
    response = client.get("/search", params=DOWNTOWN)
    assert response.status_code == 200
    results = response.json()
    assert len(results) > 0
    assert results[0]["address"] == "1050 Robson St"
    distances = [r["distance_m"] for r in results]
    assert distances == sorted(distances)
    assert all(d <= 3000 for d in distances)


def test_bedrooms_min_filter():
    response = client.get("/search", params={**DOWNTOWN, "bedrooms_min": 2})
    results = response.json()
    assert [r["address"] for r in results] == [
        "1560 W Hastings St",
        "1290 W 10th Ave",
        "720 Union St",
        "2250 Main St",
    ]


def test_price_max_and_property_type_filters():
    params = {**DOWNTOWN, "price_max": 800000, "property_type": "condo"}
    results = client.get("/search", params=params).json()
    assert len(results) > 0
    assert all(r["property_type"] == "condo" for r in results)
    assert all(r["price"] <= 800000 for r in results)


def test_no_matches_returns_empty_list():
    # Out in the Pacific Ocean, nowhere near any listing.
    params = {"lat": 49.0, "lon": -125.0, "radius": 1000}
    response = client.get("/search", params=params)
    assert response.status_code == 200
    assert response.json() == []


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
