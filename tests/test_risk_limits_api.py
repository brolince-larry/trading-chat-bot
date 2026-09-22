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


def test_get_risk_limits_returns_defaults_when_unset(client: TestClient):
    response = client.get("/api/v1/risk/limits")
    assert response.status_code == 200
    body = response.json()
    assert body["max_risk_per_trade_percent"] == "1.0"
    assert body["max_open_positions"] == 5


def test_put_risk_limits_persists_and_is_returned_by_get(client: TestClient):
    update = client.put(
        "/api/v1/risk/limits",
        json={
            "max_risk_per_trade_percent": "2.5",
            "max_daily_loss_percent": "5",
            "max_open_positions": 8,
            "max_spread_pips": "4",
            "max_correlated_exposure": "high",
            "min_risk_reward": "2.0",
        },
    )
    assert update.status_code == 200
    assert update.json()["max_open_positions"] == 8

    fetched = client.get("/api/v1/risk/limits").json()
    # The DB column is a fixed-precision Numeric, so round-tripping can add
    # trailing zeros (e.g. "2.50") without changing the value.
    assert Decimal(fetched["max_risk_per_trade_percent"]) == Decimal("2.5")
    assert fetched["max_correlated_exposure"] == "high"


def test_put_risk_limits_rejects_invalid_percent(client: TestClient):
    response = client.put(
        "/api/v1/risk/limits",
        json={
            "max_risk_per_trade_percent": "150",
            "max_daily_loss_percent": "5",
            "max_open_positions": 8,
            "max_spread_pips": "4",
        },
    )
    assert response.status_code == 422
