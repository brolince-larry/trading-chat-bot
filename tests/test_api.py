from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_check(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_symbols(client: TestClient):
    response = client.get("/api/v1/market/symbols")
    assert response.status_code == 200
    symbols = response.json()
    assert len(symbols) >= 8
    assert any(s["name"] == "EUR_USD" for s in symbols)


def test_get_candles_for_supported_symbol(client: TestClient):
    response = client.get("/api/v1/market/EUR_USD/candles", params={"timeframe": "1h", "count": 100})
    assert response.status_code == 200
    candles = response.json()
    assert len(candles) == 100
    assert all({"open", "high", "low", "close", "timestamp"} <= c.keys() for c in candles)


def test_get_candles_for_unknown_symbol_returns_404(client: TestClient):
    response = client.get("/api/v1/market/XXX_YYY/candles")
    assert response.status_code == 404


def test_get_candles_rejects_excessive_count(client: TestClient):
    response = client.get("/api/v1/market/EUR_USD/candles", params={"count": 10000})
    assert response.status_code == 422


def test_get_price(client: TestClient):
    response = client.get("/api/v1/market/EUR_USD/price")
    assert response.status_code == 200
    body = response.json()
    assert float(body["ask"]) > float(body["bid"])
    assert float(body["spread_pips"]) > 0


def test_get_pair_analysis(client: TestClient):
    response = client.get("/api/v1/analysis/EUR_USD")
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "EUR_USD"
    assert body["higher_timeframe"]["timeframe"] == "4h"
    assert body["entry_timeframe"]["timeframe"] == "1h"
    assert body["higher_timeframe"]["trend"] in {"bullish", "bearish", "neutral"}


def test_get_pair_analysis_unknown_symbol(client: TestClient):
    response = client.get("/api/v1/analysis/NOT_REAL")
    assert response.status_code == 404


def test_run_scan_default_symbols(client: TestClient):
    response = client.post("/api/v1/scanner/run", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["symbols_scanned"] == 11
    for candidate in body["candidates"]:
        assert 0 <= candidate["quality_score"] <= 100
        assert candidate["setup"]["status"] in {"watching", "confirmed"}


def test_run_scan_with_specific_symbols(client: TestClient):
    response = client.post("/api/v1/scanner/run", json={"symbols": ["eur_usd", "gbp_usd"]})
    assert response.status_code == 200
    assert response.json()["symbols_scanned"] == 2


def test_run_scan_rejects_unsupported_symbol(client: TestClient):
    response = client.post("/api/v1/scanner/run", json={"symbols": ["FAKE_PAIR"]})
    assert response.status_code == 422


def test_run_scan_rejects_too_many_symbols(client: TestClient):
    response = client.post("/api/v1/scanner/run", json={"symbols": ["EUR_USD"] * 26})
    assert response.status_code == 422


def test_run_scan_filters_by_min_quality_score(client: TestClient):
    response = client.post("/api/v1/scanner/run", json={"min_quality_score": 90})
    assert response.status_code == 200
    for candidate in response.json()["candidates"]:
        assert candidate["quality_score"] >= 90


def test_position_size_endpoint(client: TestClient):
    response = client.post(
        "/api/v1/risk/position-size",
        json={
            "symbol": "EUR_USD",
            "account_balance": "10000",
            "risk_percent": "1",
            "entry_price": "1.1000",
            "stop_loss_price": "1.0950",
            "account_currency": "USD",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["lots"] == "0.2"
    assert body["meets_minimum_lot"] is True


def test_position_size_endpoint_rejects_negative_balance(client: TestClient):
    response = client.post(
        "/api/v1/risk/position-size",
        json={
            "symbol": "EUR_USD",
            "account_balance": "-100",
            "risk_percent": "1",
            "entry_price": "1.1000",
            "stop_loss_price": "1.0950",
        },
    )
    assert response.status_code == 422


def test_position_size_endpoint_unknown_symbol(client: TestClient):
    response = client.post(
        "/api/v1/risk/position-size",
        json={
            "symbol": "NOT_REAL",
            "account_balance": "10000",
            "risk_percent": "1",
            "entry_price": "1.1000",
            "stop_loss_price": "1.0950",
        },
    )
    assert response.status_code == 404


def test_position_size_endpoint_rejects_equal_entry_and_stop(client: TestClient):
    response = client.post(
        "/api/v1/risk/position-size",
        json={
            "symbol": "EUR_USD",
            "account_balance": "10000",
            "risk_percent": "1",
            "entry_price": "1.1000",
            "stop_loss_price": "1.1000",
        },
    )
    assert response.status_code == 422
