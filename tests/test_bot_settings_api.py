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


def test_bot_settings_defaults_to_all_symbols_and_strategies(client: TestClient):
    response = client.get("/api/v1/bot/settings")
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert "EUR_USD" in body["active_symbols"]
    assert "trend_pullback" in body["active_strategies"]


def test_bot_settings_update_persists(client: TestClient):
    updated = client.put(
        "/api/v1/bot/settings",
        json={"enabled": False, "active_symbols": ["EUR_USD", "GBP_USD"], "active_strategies": ["trend_pullback"]},
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["enabled"] is False
    assert body["active_symbols"] == ["EUR_USD", "GBP_USD"]

    refetched = client.get("/api/v1/bot/settings").json()
    assert refetched == body


def test_bot_settings_update_raises_bot_update_notification(client: TestClient):
    client.put(
        "/api/v1/bot/settings",
        json={"enabled": False, "active_symbols": ["EUR_USD"], "active_strategies": ["trend_pullback"]},
    )
    notifications = client.get("/api/v1/notifications").json()
    assert any(n["type"] == "bot_update" for n in notifications)


def test_bot_settings_rejects_unsupported_symbol(client: TestClient):
    response = client.put(
        "/api/v1/bot/settings",
        json={"enabled": True, "active_symbols": ["XXX_YYY"], "active_strategies": ["trend_pullback"]},
    )
    assert response.status_code == 422


def test_bot_settings_rejects_unknown_strategy(client: TestClient):
    response = client.put(
        "/api/v1/bot/settings",
        json={"enabled": True, "active_symbols": ["EUR_USD"], "active_strategies": ["not_a_strategy"]},
    )
    assert response.status_code == 422
