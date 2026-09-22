from __future__ import annotations

import pytest

from app.domain.analysis.structure import MarketRegime, TrendDirection
from app.domain.analysis.timeframe_analysis import compute_timeframe_analysis
from app.domain.market.models import Timeframe
from app.domain.strategies.base import Direction, SetupStatus
from app.domain.strategies.breakout_retest import BreakoutRetestStrategy
from app.domain.strategies.range_reversion import RangeReversionStrategy
from app.domain.strategies.trend_pullback import TrendPullbackStrategy
from tests.conftest import (
    build_breakout_retest_candles,
    build_candles,
    build_trend_pullback_scenario,
    make_timeframe_analysis,
)

# --- TrendPullbackStrategy -----------------------------------------------


@pytest.mark.parametrize("direction", ["long", "short"])
def test_trend_pullback_rejects_without_higher_timeframe_alignment(direction):
    _, entry_tf = build_trend_pullback_scenario(direction, "watching")
    misaligned_higher = make_timeframe_analysis(trend=TrendDirection.NEUTRAL)

    setup = TrendPullbackStrategy().analyze(misaligned_higher, entry_tf)

    assert setup.status is SetupStatus.REJECTED
    assert setup.direction is Direction.NONE


@pytest.mark.parametrize("direction", ["long", "short"])
def test_trend_pullback_watches_while_awaiting_confirmation(direction):
    higher_tf, entry_tf = build_trend_pullback_scenario(direction, "watching")

    setup = TrendPullbackStrategy().analyze(higher_tf, entry_tf)

    assert setup.status is SetupStatus.WATCHING
    assert setup.direction is (Direction.LONG if direction == "long" else Direction.SHORT)
    assert setup.entry_price is None
    assert "confirmation" in setup.reason.lower() or "retrace" in setup.reason.lower()


@pytest.mark.parametrize("direction", ["long", "short"])
def test_trend_pullback_confirms_on_confirmation_candle(direction):
    higher_tf, entry_tf = build_trend_pullback_scenario(direction, "confirmed")

    setup = TrendPullbackStrategy().analyze(higher_tf, entry_tf)

    assert setup.status is SetupStatus.CONFIRMED
    expected_direction = Direction.LONG if direction == "long" else Direction.SHORT
    assert setup.direction is expected_direction
    assert setup.entry_price is not None
    assert setup.stop_loss is not None
    assert len(setup.take_profits) == 2
    assert setup.risk_reward == pytest.approx(2.5)

    if direction == "long":
        assert setup.stop_loss < setup.entry_price
        assert all(tp.price > setup.entry_price for tp in setup.take_profits)
    else:
        assert setup.stop_loss > setup.entry_price
        assert all(tp.price < setup.entry_price for tp in setup.take_profits)


def test_trend_pullback_rejects_when_insufficient_entry_data():
    higher_tf = make_timeframe_analysis(trend=TrendDirection.BULLISH, ema_20=1.10, ema_50=1.09, ema_200=1.08)
    entry_tf = make_timeframe_analysis(ema_20=None, atr_14=None)

    setup = TrendPullbackStrategy().analyze(higher_tf, entry_tf)

    assert setup.status is SetupStatus.REJECTED


# --- BreakoutRetestStrategy ------------------------------------------------


@pytest.mark.parametrize("direction", ["long", "short"])
def test_breakout_retest_rejects_without_a_breakout(direction):
    candles = build_breakout_retest_candles(direction, "rejected")
    analysis = compute_timeframe_analysis("EUR_USD", Timeframe.H1, candles)

    setup = BreakoutRetestStrategy().analyze(analysis, analysis)

    assert setup.status is SetupStatus.REJECTED
    assert setup.direction is Direction.NONE


@pytest.mark.parametrize("direction", ["long", "short"])
def test_breakout_retest_watches_after_breakout_before_retest(direction):
    candles = build_breakout_retest_candles(direction, "watching")
    analysis = compute_timeframe_analysis("EUR_USD", Timeframe.H1, candles)

    setup = BreakoutRetestStrategy().analyze(analysis, analysis)

    assert setup.status is SetupStatus.WATCHING
    assert setup.direction is (Direction.LONG if direction == "long" else Direction.SHORT)
    assert "retest" in setup.reason.lower() or "retest" in (setup.entry_trigger or "").lower()


@pytest.mark.parametrize("direction", ["long", "short"])
def test_breakout_retest_confirms_on_retest_rejection(direction):
    candles = build_breakout_retest_candles(direction, "confirmed")
    analysis = compute_timeframe_analysis("EUR_USD", Timeframe.H1, candles)

    setup = BreakoutRetestStrategy().analyze(analysis, analysis)

    assert setup.status is SetupStatus.CONFIRMED
    expected_direction = Direction.LONG if direction == "long" else Direction.SHORT
    assert setup.direction is expected_direction
    assert setup.entry_price is not None
    assert setup.stop_loss is not None
    if direction == "long":
        assert setup.stop_loss < setup.entry_price
    else:
        assert setup.stop_loss > setup.entry_price


# --- RangeReversionStrategy -------------------------------------------------


def test_range_reversion_rejects_when_not_ranging():
    analysis = make_timeframe_analysis(
        regime=MarketRegime.TRENDING,
        support_levels=[1.0950],
        resistance_levels=[1.1050],
    )

    setup = RangeReversionStrategy().analyze(analysis, analysis)

    assert setup.status is SetupStatus.REJECTED


def test_range_reversion_rejects_away_from_boundaries():
    analysis = make_timeframe_analysis(
        regime=MarketRegime.RANGING,
        last_close=1.1000,
        support_levels=[1.0950],
        resistance_levels=[1.1050],
        rsi_14=50.0,
        atr_14=0.0010,
    )

    setup = RangeReversionStrategy().analyze(analysis, analysis)

    assert setup.status is SetupStatus.REJECTED


def test_range_reversion_watches_at_resistance_without_rejection_candle():
    candles = build_candles([1.1040, 1.1050], wick_pad=0.0002)  # bullish last candle
    analysis = make_timeframe_analysis(
        regime=MarketRegime.RANGING,
        last_close=1.1050,
        support_levels=[1.0950],
        resistance_levels=[1.1052],
        rsi_14=70.0,
        atr_14=0.0010,
        candles=candles,
    )

    setup = RangeReversionStrategy().analyze(analysis, analysis)

    assert setup.status is SetupStatus.WATCHING
    assert setup.direction is Direction.SHORT


def test_range_reversion_confirms_short_at_resistance_with_rejection_candle():
    # A rejection candle only needs to close back inside the range; it
    # doesn't travel far, so last_close must stay within the strategy's
    # boundary tolerance (0.4 * ATR = 0.0004 here) of resistance.
    candles = build_candles([1.1060, 1.1049], wick_pad=0.0002)  # bearish last candle
    analysis = make_timeframe_analysis(
        regime=MarketRegime.RANGING,
        last_close=1.1049,
        support_levels=[1.0950],
        resistance_levels=[1.1052],
        rsi_14=70.0,
        atr_14=0.0010,
        candles=candles,
    )

    setup = RangeReversionStrategy().analyze(analysis, analysis)

    assert setup.status is SetupStatus.CONFIRMED
    assert setup.direction is Direction.SHORT
    assert setup.entry_price == pytest.approx(1.1049)
    assert setup.stop_loss > setup.entry_price
    assert setup.take_profits[0].price == pytest.approx(1.0950)


def test_range_reversion_confirms_long_at_support_with_rejection_candle():
    candles = build_candles([1.0940, 1.0951], wick_pad=0.0002)  # bullish last candle
    analysis = make_timeframe_analysis(
        regime=MarketRegime.RANGING,
        last_close=1.0951,
        support_levels=[1.0948],
        resistance_levels=[1.1050],
        rsi_14=30.0,
        atr_14=0.0010,
        candles=candles,
    )

    setup = RangeReversionStrategy().analyze(analysis, analysis)

    assert setup.status is SetupStatus.CONFIRMED
    assert setup.direction is Direction.LONG
    assert setup.stop_loss < setup.entry_price
    assert setup.take_profits[0].price == pytest.approx(1.1050)
