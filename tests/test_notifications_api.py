from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
    from app.config import get_settings
    from app.infrastructure.database.session import reset_engine

    get_settings.cache_clear()
    reset_engine()

    with TestClient(app) as test_client:
        yield test_client

    get_settings.cache_clear()
    reset_engine()


def _raise_a_notification(client: TestClient) -> dict:
    # Toggling the bot raises a real bot_update notification (see
    # app/api/routes/bot.py) — reused here instead of writing to the DB
    # directly, so this test exercises the same path a user would trigger.
    client.put(
        "/api/v1/bot/settings",
        json={"enabled": False, "active_symbols": ["EUR_USD"], "active_strategies": ["trend_pullback"]},
    )
    return client.get("/api/v1/notifications").json()[0]


def test_list_notifications_returns_raised_events(client: TestClient):
    notification = _raise_a_notification(client)
    assert notification["type"] == "bot_update"
    assert notification["read"] is False


def test_mark_notification_read(client: TestClient):
    notification = _raise_a_notification(client)
    response = client.post(f"/api/v1/notifications/{notification['id']}/read")
    assert response.status_code == 204

    updated = next(n for n in client.get("/api/v1/notifications").json() if n["id"] == notification["id"])
    assert updated["read"] is True


def test_mark_unknown_notification_read_returns_404(client: TestClient):
    response = client.post("/api/v1/notifications/does-not-exist/read")
    assert response.status_code == 404


def test_mark_all_read(client: TestClient):
    _raise_a_notification(client)
    client.put(
        "/api/v1/bot/settings",
        json={"enabled": True, "active_symbols": ["EUR_USD"], "active_strategies": ["trend_pullback"]},
    )
    assert len(client.get("/api/v1/notifications").json()) == 2

    response = client.post("/api/v1/notifications/read-all")
    assert response.status_code == 204

    notifications = client.get("/api/v1/notifications").json()
    assert all(n["read"] for n in notifications)


def test_unread_only_filter(client: TestClient):
    notification = _raise_a_notification(client)
    client.post(f"/api/v1/notifications/{notification['id']}/read")

    unread = client.get("/api/v1/notifications", params={"unread_only": True}).json()
    assert unread == []
