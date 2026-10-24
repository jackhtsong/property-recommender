from fastapi.testclient import TestClient

import api.main
from api.llm import Filters
from api.main import app

client = TestClient(app)


def test_config_gives_browser_key_only(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_BROWSER_KEY", "browser-key")
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "server-secret")
    response = client.get("/config")
    assert response.json() == {"maps_browser_key": "browser-key"}
    assert "server-secret" not in response.text


def test_config_without_browser_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_MAPS_BROWSER_KEY", raising=False)
    assert client.get("/config").json() == {"maps_browser_key": None}


def test_ask_returns_searched_place_as_center(monkeypatch):
    monkeypatch.setattr(api.main, "parse_query", lambda text: Filters(near="Commercial Drive"))
    monkeypatch.setattr(api.main, "geocode", lambda place: (49.2839, -123.0704))
    body = client.post("/ask", json={"text": "near commercial drive"}).json()
    assert body["center"] == {"lat": 49.2839, "lon": -123.0704}


def test_ask_city_wide_has_no_center(monkeypatch):
    monkeypatch.setattr(api.main, "parse_query", lambda text: Filters(property_type="loft"))
    body = client.post("/ask", json={"text": "a loft"}).json()
    assert body["center"] is None


def test_results_include_coordinates_for_pins():
    results = client.get("/search", params={"lat": 49.2827, "lon": -123.1207}).json()
    assert all(isinstance(r["lat"], float) and isinstance(r["lon"], float) for r in results)
