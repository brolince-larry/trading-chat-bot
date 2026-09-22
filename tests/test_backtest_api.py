from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_backtest_run_returns_a_full_result():
    response = client.post(
        "/api/v1/backtest/run",
        json={"symbol": "EUR_USD", "strategy": "trend_pullback", "lookback_candles": 150},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "EUR_USD"
    assert body["strategy"] == "trend_pullback"
    assert body["total_trades"] == len(body["trades"])
    assert len(body["equity_curve"]) == body["total_trades"] + 1


def test_backtest_run_rejects_unsupported_symbol():
    response = client.post(
        "/api/v1/backtest/run", json={"symbol": "XXX_YYY", "strategy": "trend_pullback"}
    )
    assert response.status_code == 422


def test_backtest_run_rejects_unknown_strategy():
    response = client.post(
        "/api/v1/backtest/run", json={"symbol": "EUR_USD", "strategy": "not_a_strategy"}
    )
    assert response.status_code == 422


def test_backtest_run_rejects_lookback_out_of_range():
    response = client.post(
        "/api/v1/backtest/run",
        json={"symbol": "EUR_USD", "strategy": "trend_pullback", "lookback_candles": 5},
    )
    assert response.status_code == 422


def test_backtest_run_accepts_custom_timeframes_and_balance():
    response = client.post(
        "/api/v1/backtest/run",
        json={
            "symbol": "USD_JPY",
            "strategy": "breakout_retest",
            "higher_timeframe": "1d",
            "entry_timeframe": "4h",
            "lookback_candles": 150,
            "starting_balance": "25000",
            "risk_percent": "0.5",
            "quote_to_account_rate": "0.0067",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["starting_balance"] == "25000"
    assert body["higher_timeframe"] == "1d"
    assert body["entry_timeframe"] == "4h"


def test_backtest_run_rejects_jpy_pair_without_conversion_rate():
    response = client.post(
        "/api/v1/backtest/run",
        json={"symbol": "USD_JPY", "strategy": "breakout_retest", "lookback_candles": 150},
    )
    assert response.status_code == 422
    assert "quote_to_account_rate" in response.json()["detail"]
