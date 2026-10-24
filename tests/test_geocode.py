import pytest
from fastapi.testclient import TestClient

import api.geocode
import api.main
from api.geocode import GeocodeError, geocode
from api.main import app

client = TestClient(app)


# --- /search with near= (Google is replaced by a fake, so no key or network needed) ---

def test_near_is_geocoded_then_searched(monkeypatch):
    calls = []

    def fake_geocode(place):
        calls.append(place)
        return 49.2827, -123.1207  # Robson & Burrard

    monkeypatch.setattr(api.main, "geocode", fake_geocode)
    results = client.get("/search", params={"near": "Robson St"}).json()
    assert calls == ["Robson St"]
    assert results[0]["address"] == "1050 Robson St"


def test_unknown_place_returns_400(monkeypatch):
    def fake_geocode(place):
        raise GeocodeError(f'Could not find "{place}"')

    monkeypatch.setattr(api.main, "geocode", fake_geocode)
    response = client.get("/search", params={"near": "nowhereville"})
    assert response.status_code == 400
    assert response.json()["detail"] == 'Could not find "nowhereville"'


def test_neither_near_nor_coordinates_is_rejected():
    response = client.get("/search")
    assert response.status_code == 422


# --- geocode() itself, with Google's HTTP response faked ---

class FakeResponse:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


def fake_google(monkeypatch, data):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-key")
    monkeypatch.setattr(api.geocode.httpx, "get", lambda *args, **kwargs: FakeResponse(data))


def test_geocode_returns_lat_lon(monkeypatch):
    fake_google(monkeypatch, {
        "status": "OK",
        "results": [{"geometry": {"location": {"lat": 49.27, "lng": -123.07}}}],
    })
    assert geocode("Commercial Drive") == (49.27, -123.07)


def test_geocode_zero_results(monkeypatch):
    fake_google(monkeypatch, {"status": "ZERO_RESULTS", "results": []})
    with pytest.raises(GeocodeError, match="Could not find"):
        geocode("nowhereville")


def test_geocode_rejects_city_wide_fallback(monkeypatch):
    # What Google really returns for gibberish: a partial match on all of Vancouver.
    fake_google(monkeypatch, {
        "status": "OK",
        "results": [{
            "partial_match": True,
            "types": ["locality", "political"],
            "geometry": {"location": {"lat": 49.28, "lng": -123.12}},
        }],
    })
    with pytest.raises(GeocodeError, match="Could not find"):
        geocode("asdfqwerzxcv")


def test_geocode_adds_city_unless_given(monkeypatch):
    sent = []
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-key")

    def fake_get(url, params, timeout):
        sent.append(params["address"])
        return FakeResponse({"status": "OK", "results": [{"types": ["route"], "geometry": {"location": {"lat": 0, "lng": 0}}}]})

    monkeypatch.setattr(api.geocode.httpx, "get", fake_get)
    geocode("Main St")
    geocode("Metrotown, Burnaby")
    assert sent == ["Main St, Vancouver, BC", "Metrotown, Burnaby"]


def test_geocode_bad_key(monkeypatch):
    fake_google(monkeypatch, {"status": "REQUEST_DENIED", "error_message": "The provided API key is invalid."})
    with pytest.raises(GeocodeError, match="REQUEST_DENIED"):
        geocode("Main St")


def test_geocode_missing_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    with pytest.raises(GeocodeError, match="not set"):
        geocode("Main St")
