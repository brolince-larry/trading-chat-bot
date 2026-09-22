from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    # An isolated on-disk SQLite DB per test keeps position/limits state from
    # leaking between tests (and from the developer's real forex_ai.db).
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
    from app.config import get_settings
    from app.infrastructure.database.session import reset_engine

    get_settings.cache_clear()
    reset_engine()

    with TestClient(app) as test_client:
        yield test_client

    get_settings.cache_clear()
    reset_engine()


def _open_sample_position(client: TestClient) -> dict:
    # open_position validates the setup against the live price (see
    # test_paper_trading.py), so entry/stop/target must bracket whatever
    # the simulated provider's current EUR_USD price actually is, not a
    # hardcoded level.
    price = float(client.get("/api/v1/market/EUR_USD/price").json()["ask"])
    response = client.post(
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
    )
    assert response.status_code == 201
    return response.json()


def test_open_and_list_open_position(client: TestClient):
    opened = _open_sample_position(client)
    assert opened["status"] == "open"

    listed = client.get("/api/v1/positions?status=open").json()
    assert len(listed) == 1
    assert listed[0]["id"] == opened["id"]
    assert listed[0]["unrealized_pnl"] is not None


def test_open_position_rejects_zero_lots(client: TestClient):
    response = client.post(
        "/api/v1/positions/open",
        json={
            "symbol": "EUR_USD",
            "strategy": "trend_pullback",
            "direction": "long",
            "entry_price": "1.1000",
            "stop_loss": "1.0950",
            "lots": "0",
            "units": "0",
            "pip_value_per_unit": "0.0001",
        },
    )
    assert response.status_code == 422


def test_close_position_manually(client: TestClient):
    opened = _open_sample_position(client)

    closed = client.post(f"/api/v1/positions/{opened['id']}/close", json={"close_price": "1.1050"})
    assert closed.status_code == 200
    body = closed.json()
    assert body["status"] == "closed_manual"
    assert body["close_price"] == "1.1050"
    assert body["realized_pnl"] is not None

    open_list = client.get("/api/v1/positions?status=open").json()
    assert open_list == []

    closed_list = client.get("/api/v1/positions?status=closed").json()
    assert len(closed_list) == 1


def test_close_unknown_position_returns_404(client: TestClient):
    response = client.post("/api/v1/positions/does-not-exist/close", json={})
    assert response.status_code == 404


def test_double_close_returns_404(client: TestClient):
    opened = _open_sample_position(client)
    client.post(f"/api/v1/positions/{opened['id']}/close", json={})
    second = client.post(f"/api/v1/positions/{opened['id']}/close", json={})
    assert second.status_code == 404


def test_update_stops_moves_stop_loss(client: TestClient):
    opened = _open_sample_position(client)
    entry = float(opened["entry_price"])

    updated = client.patch(
        f"/api/v1/positions/{opened['id']}", json={"stop_loss": f"{entry - 0.0010:.5f}"}
    )
    assert updated.status_code == 200
    assert updated.json()["stop_loss"] == f"{entry - 0.0010:.5f}"


def test_update_stops_requires_at_least_one_field(client: TestClient):
    opened = _open_sample_position(client)
    response = client.patch(f"/api/v1/positions/{opened['id']}", json={})
    assert response.status_code == 422


def test_close_all_closes_every_open_position(client: TestClient):
    _open_sample_position(client)
    _open_sample_position(client)
    assert len(client.get("/api/v1/positions?status=open").json()) == 2

    response = client.post("/api/v1/positions/close-all")
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert client.get("/api/v1/positions?status=open").json() == []


def test_performance_stats_reflects_closed_positions(client: TestClient):
    opened = _open_sample_position(client)
    client.post(f"/api/v1/positions/{opened['id']}/close", json={"close_price": "1.1100"})

    stats = client.get("/api/v1/positions/stats").json()
    assert stats["closed_count"] == 1
