from __future__ import annotations

from decimal import Decimal

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


def test_automation_settings_defaults_disabled(client: TestClient):
    response = client.get("/api/v1/automations/settings")
    assert response.status_code == 200
    body = response.json()
    assert body["breakeven_enabled"] is False
    assert body["trailing_stop_enabled"] is False


def test_automation_settings_update_persists(client: TestClient):
    updated = client.put(
        "/api/v1/automations/settings",
        json={
            "breakeven_enabled": True,
            "breakeven_at_r": "1.5",
            "trailing_stop_enabled": True,
            "trailing_stop_pips": "15",
        },
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["breakeven_enabled"] is True
    assert body["breakeven_at_r"] == "1.5"

    refetched = client.get("/api/v1/automations/settings").json()
    # The DB columns are fixed-precision Numeric, so round-tripping can add
    # trailing zeros (e.g. "15.00") without changing the value.
    assert refetched["breakeven_enabled"] == body["breakeven_enabled"]
    assert Decimal(refetched["breakeven_at_r"]) == Decimal(body["breakeven_at_r"])
    assert refetched["trailing_stop_enabled"] == body["trailing_stop_enabled"]
    assert Decimal(refetched["trailing_stop_pips"]) == Decimal(body["trailing_stop_pips"])


def test_automation_settings_rejects_non_positive_r(client: TestClient):
    response = client.put(
        "/api/v1/automations/settings",
        json={
            "breakeven_enabled": True,
            "breakeven_at_r": "0",
            "trailing_stop_enabled": False,
            "trailing_stop_pips": "15",
        },
    )
    assert response.status_code == 422
