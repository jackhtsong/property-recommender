import pytest
from fastapi.testclient import TestClient

import api.llm
import api.main
from api.llm import Explanation, Filters, LLMError, explain_listings
from api.main import app

client = TestClient(app)

KITS_BEACH = (49.2754, -123.1535)


def fake_parse(filters):
    return lambda text: filters


# --- /ask: Gemini and Google are both faked, so no keys or network needed ---

def test_ask_parses_geocodes_and_searches(monkeypatch, ids_within):
    monkeypatch.setattr(api.main, "parse_query", fake_parse(
        Filters(near="Kitsilano Beach", bedrooms_min=3, property_type="townhouse")))
    monkeypatch.setattr(api.main, "geocode", lambda place: KITS_BEACH)

    body = client.post("/ask", json={"text": "3 bed townhouse near kits beach"}).json()
    assert body["filters"]["near"] == "Kitsilano Beach"
    # Same results as searching those filters directly, within the nearby radius.
    lat, lon = KITS_BEACH
    expected = ids_within(lat, lon, api.main.NEARBY_RADIUS, where="property_type = 'townhouse' AND bedrooms >= 3")
    assert len(expected) > 0
    assert {r["id"] for r in body["results"]} == expected


def test_ask_widens_radius_until_something_matches(monkeypatch):
    monkeypatch.setattr(api.main, "parse_query", fake_parse(Filters(near="Quiet Corner")))
    monkeypatch.setattr(api.main, "geocode", lambda place: (49.25, -123.1))
    one_real_listing = api.main.run_search(49.2827, -123.1207, 2000)[:1]
    tried = []

    def fake_search(lat, lon, radius, *filters):
        # Nothing nearby: only the widest radius finds a listing.
        tried.append(radius)
        return one_real_listing if radius >= 20000 else []

    monkeypatch.setattr(api.main, "run_search", fake_search)

    body = client.post("/ask", json={"text": "near a quiet corner"}).json()
    assert tried == [3000, 8000, 20000]
    assert body["radius_m"] == 20000
    assert len(body["results"]) == 1


def test_ask_stops_at_first_radius_with_results(monkeypatch):
    monkeypatch.setattr(api.main, "parse_query", fake_parse(Filters(near="Downtown")))
    monkeypatch.setattr(api.main, "geocode", lambda place: (49.2827, -123.1207))
    body = client.post("/ask", json={"text": "downtown"}).json()
    assert body["radius_m"] == api.main.NEARBY_RADII[0]
    assert len(body["results"]) > 0


def test_ask_without_place_searches_whole_city(monkeypatch):
    monkeypatch.setattr(api.main, "parse_query", fake_parse(Filters(property_type="duplex")))

    def geocode_should_not_run(place):
        raise AssertionError("geocode called without a place")

    monkeypatch.setattr(api.main, "geocode", geocode_should_not_run)
    results = client.post("/ask", json={"text": "a duplex"}).json()["results"]
    assert len(results) > 0
    assert all(r["property_type"] == "duplex" for r in results)


def test_ask_reports_gemini_failure(monkeypatch):
    def broken(text):
        raise LLMError("Gemini request failed: quota exceeded")

    monkeypatch.setattr(api.main, "parse_query", broken)
    response = client.post("/ask", json={"text": "3 bed house"})
    assert response.status_code == 502
    assert "quota" in response.json()["detail"]


def test_ask_rejects_empty_text():
    assert client.post("/ask", json={"text": ""}).status_code == 422


# --- /explain ---

def test_explain_uses_database_facts(monkeypatch, db):
    seen = {}

    def fake_explain(query, listings):
        seen["query"] = query
        seen["addresses"] = sorted(l["address"] for l in listings)
        return {l["id"]: f"Fits: {l['address']}" for l in listings}

    # Any two real listings; their addresses come from the database, not the request.
    rows = db("SELECT id, address FROM listings ORDER BY id LIMIT 2")
    ids = [r["id"] for r in rows]

    monkeypatch.setattr(api.main, "explain_listings", fake_explain)
    response = client.post("/explain", json={"text": "condo downtown", "listing_ids": ids})
    assert response.status_code == 200
    assert response.json() == {str(r["id"]): f"Fits: {r['address']}" for r in rows}
    assert seen == {"query": "condo downtown", "addresses": sorted(r["address"] for r in rows)}


def test_explain_limits_listing_count():
    response = client.post("/explain", json={"text": "x" * 5, "listing_ids": list(range(1, 7))})
    assert response.status_code == 422


def test_explain_unknown_ids_returns_404():
    response = client.post("/explain", json={"text": "condo", "listing_ids": [9999]})
    assert response.status_code == 404


# --- llm.py itself, with the Gemini client faked ---

class FakeModels:
    def __init__(self, parsed):
        self.parsed = parsed

    def generate_content(self, **kwargs):
        return type("Response", (), {"parsed": self.parsed})()


def fake_gemini(monkeypatch, parsed):
    fake_client = type("Client", (), {"models": FakeModels(parsed)})()
    monkeypatch.setattr(api.llm, "_client", lambda: fake_client)


def test_explain_drops_ids_gemini_made_up(monkeypatch):
    fake_gemini(monkeypatch, [
        Explanation(id=1, explanation="Real listing"),
        Explanation(id=42, explanation="Invented listing"),
    ])
    assert explain_listings("condo", [{"id": 1, "address": "1050 Robson St"}]) == {1: "Real listing"}


def test_explain_accepts_database_decimals(monkeypatch):
    # Prices come from Postgres as Decimal, which plain json.dumps rejects.
    from decimal import Decimal
    fake_gemini(monkeypatch, [Explanation(id=1, explanation="ok")])
    listing = {"id": 1, "address": "1050 Robson St", "price": Decimal("699000.00"), "washrooms": Decimal("1.0")}
    assert explain_listings("condo", [listing]) == {1: "ok"}


def test_unusable_reply_raises(monkeypatch):
    fake_gemini(monkeypatch, None)
    with pytest.raises(LLMError, match="unexpected format"):
        api.llm.parse_query("3 bed house")


def test_busy_gemini_gives_friendly_message(monkeypatch):
    from google.genai import errors

    class BusyModels:
        def generate_content(self, **kwargs):
            raise errors.ServerError(503, {"error": {"code": 503, "message": "high demand", "status": "UNAVAILABLE"}})

    monkeypatch.setattr(api.llm, "_client", lambda: type("Client", (), {"models": BusyModels()})())
    with pytest.raises(LLMError, match="Gemini is busy"):
        api.llm.parse_query("3 bed house")


def test_missing_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(LLMError, match="not set"):
        api.llm.parse_query("3 bed house")


def test_ask_starts_wider_for_a_whole_city(monkeypatch):
    monkeypatch.setattr(api.main, "parse_query", fake_parse(Filters(near="Surrey")))
    monkeypatch.setattr(api.main, "geocode", lambda place: (49.19, -122.85))
    tried = []
    monkeypatch.setattr(api.main, "run_search", lambda lat, lon, radius, *f: tried.append(radius) or [])
    client.post("/ask", json={"text": "townhouse in surrey"})
    assert tried == list(api.main.CITY_RADII)
