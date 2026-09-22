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


def test_account_summary_defaults_to_starting_balance(client: TestClient):
    response = client.get("/api/v1/account/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["balance"] == "10000"
    assert body["active_trades"] == 0
    assert body["win_rate"] is None
    assert body["top_pairs"] == []
    assert len(body["equity_curve"]) == 1


def test_account_settings_update_changes_starting_balance(client: TestClient):
    updated = client.put("/api/v1/account/settings", json={"starting_balance": "5000"})
    assert updated.status_code == 200
    assert updated.json()["starting_balance"] == "5000"

    summary = client.get("/api/v1/account/summary").json()
    assert Decimal(summary["balance"]) == Decimal(5000)


def test_account_summary_reflects_closed_trade_pnl_and_top_pairs(client: TestClient):
    price = float(client.get("/api/v1/market/EUR_USD/price").json()["ask"])
    opened = client.post(
        "/api/v1/positions/open",
        json={
            "symbol": "EUR_USD",
            "strategy": "trend_pullback",
            "direction": "long",
            "entry_price": f"{price:.5f}",
            "stop_loss": f"{price - 0.0050:.5f}",
            "take_profit": f"{price + 0.0100:.5f}",
            "lots": "0.1",
            "units": "10000",
            "account_currency": "USD",
            "pip_value_per_unit": "0.0001",
        },
    ).json()
    client.post(f"/api/v1/positions/{opened['id']}/close", json={"close_price": f"{price + 0.0050:.5f}"})

    summary = client.get("/api/v1/account/summary?period=all").json()
    assert summary["active_trades"] == 0
    assert summary["win_rate"] == 1.0
    assert float(summary["total_realized_pnl"]) > 0
    assert len(summary["top_pairs"]) == 1
    assert summary["top_pairs"][0]["symbol"] == "EUR_USD"
    assert len(summary["equity_curve"]) >= 2


def test_account_summary_rejects_invalid_range(client: TestClient):
    response = client.get("/api/v1/account/summary?period=decade")
    assert response.status_code == 422
