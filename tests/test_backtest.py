from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.backtest.engine import BacktestError, run_backtest
from app.domain.strategies import ALL_STRATEGIES
from app.infrastructure.market_data.simulated import SimulatedMarketDataProvider

_TREND_PULLBACK = next(s for s in ALL_STRATEGIES if s.name == "trend_pullback")


def test_backtest_runs_and_returns_a_consistent_equity_curve():
    provider = SimulatedMarketDataProvider(seed=1)
    result = run_backtest(
        provider=provider, symbol="EUR_USD", strategy=_TREND_PULLBACK, lookback_candles=200
    )

    assert result.symbol == "EUR_USD"
    assert result.strategy == "trend_pullback"
    assert result.total_trades == len(result.trades)
    assert result.win_count + result.loss_count == result.total_trades
    # One equity point per closed trade, plus the initial starting point.
    assert len(result.equity_curve) == result.total_trades + 1
    assert result.equity_curve[0].balance == result.starting_balance
    assert result.equity_curve[-1].balance == result.ending_balance


def test_backtest_is_deterministic_for_a_fixed_seed():
    provider_a = SimulatedMarketDataProvider(seed=7)
    provider_b = SimulatedMarketDataProvider(seed=7)

    result_a = run_backtest(
        provider=provider_a, symbol="GBP_USD", strategy=_TREND_PULLBACK, lookback_candles=150
    )
    result_b = run_backtest(
        provider=provider_b, symbol="GBP_USD", strategy=_TREND_PULLBACK, lookback_candles=150
    )

    assert result_a.total_trades == result_b.total_trades
    assert result_a.ending_balance == result_b.ending_balance
    assert [t.entry_price for t in result_a.trades] == [t.entry_price for t in result_b.trades]


def test_backtest_trades_have_sane_risk_geometry():
    provider = SimulatedMarketDataProvider(seed=3)
    result = run_backtest(
        provider=provider, symbol="EUR_USD", strategy=_TREND_PULLBACK, lookback_candles=300
    )

    for trade in result.trades:
        assert trade.entered_at < trade.exited_at
        assert trade.bars_held >= 1
        assert trade.units > 0
        # A stop-loss exit should realize a loss (or breakeven); a
        # take-profit exit should realize a gain — the risk engine's own
        # sizing guarantees this, so a violation would indicate a real bug.
        if trade.exit_reason.value == "stop_loss":
            assert trade.pnl <= 0
        elif trade.exit_reason.value == "take_profit":
            assert trade.pnl >= 0


def test_backtest_rejects_lookback_below_minimum():
    provider = SimulatedMarketDataProvider()
    with pytest.raises(BacktestError):
        run_backtest(provider=provider, symbol="EUR_USD", strategy=_TREND_PULLBACK, lookback_candles=10)


def test_backtest_rejects_excessive_lookback():
    provider = SimulatedMarketDataProvider()
    with pytest.raises(BacktestError):
        run_backtest(
            provider=provider, symbol="EUR_USD", strategy=_TREND_PULLBACK, lookback_candles=5000
        )


def test_backtest_with_no_trades_reports_empty_stats_not_errors():
    provider = SimulatedMarketDataProvider(seed=99)
    # range_reversion on a small lookback may or may not confirm any setup;
    # either way the result must be well-formed, never raise.
    strategy = next(s for s in ALL_STRATEGIES if s.name == "range_reversion")
    result = run_backtest(provider=provider, symbol="EUR_USD", strategy=strategy, lookback_candles=80)

    assert result.total_trades == len(result.trades)
    if result.total_trades == 0:
        assert result.win_rate is None
        assert result.profit_factor is None
        assert result.ending_balance == result.starting_balance


def test_backtest_rejects_quote_currency_mismatch_without_a_conversion_rate():
    provider = SimulatedMarketDataProvider()
    with pytest.raises(BacktestError, match="quote_to_account_rate"):
        run_backtest(provider=provider, symbol="USD_CHF", strategy=_TREND_PULLBACK, lookback_candles=150)


def test_backtest_accepts_quote_currency_mismatch_with_a_conversion_rate():
    provider = SimulatedMarketDataProvider(seed=4)
    result = run_backtest(
        provider=provider,
        symbol="USD_CHF",
        strategy=_TREND_PULLBACK,
        lookback_candles=150,
        quote_to_account_rate=Decimal("1.13"),
    )
    assert result.symbol == "USD_CHF"


def test_backtest_uses_the_requested_starting_balance_and_risk():
    provider = SimulatedMarketDataProvider(seed=5)
    result = run_backtest(
        provider=provider,
        symbol="EUR_USD",
        strategy=_TREND_PULLBACK,
        lookback_candles=250,
        starting_balance=Decimal(5000),
        risk_percent=Decimal("2.0"),
    )
    assert result.starting_balance == Decimal(5000)
