from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_news_reports_not_connected_by_default():
    response = client.get("/api/v1/news")
    assert response.status_code == 200
    body = response.json()
    assert body["connected"] is False
    assert body["items"] == []
    assert body["message"]


def test_news_rejects_unsupported_symbol():
    response = client.get("/api/v1/news", params={"symbol": "XXX_YYY"})
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []


def test_sessions_endpoint_returns_four_sessions_and_world_clock():
    response = client.get("/api/v1/sessions")
    assert response.status_code == 200
    body = response.json()
    assert {s["id"] for s in body["sessions"]} == {"sydney", "tokyo", "london", "new_york"}
    assert len(body["world_clock"]) == 5
