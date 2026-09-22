from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from app.domain.analysis.candlestick_patterns import (
    CandlestickPatternName,
    PatternBias,
    detect_candlestick_pattern,
)
from app.domain.market.models import Candle, Timeframe

_TS = datetime(2026, 1, 1, tzinfo=UTC)


def _candle(o: str, h: str, low: str, c: str) -> Candle:
    return Candle(
        symbol="EUR_USD",
        timeframe=Timeframe.H1,
        timestamp=_TS,
        open=Decimal(o),
        high=Decimal(h),
        low=Decimal(low),
        close=Decimal(c),
    )


def test_no_pattern_with_no_candles():
    assert detect_candlestick_pattern([]) is None


def test_detects_doji_on_tiny_body():
    candle = _candle("1.1000", "1.1050", "1.0950", "1.1002")
    result = detect_candlestick_pattern([candle])
    assert result is not None
    assert result.name is CandlestickPatternName.DOJI
    assert result.bias is PatternBias.NEUTRAL


def test_detects_hammer_on_long_lower_wick_small_upper_wick():
    # Body 1.1000-1.1010 (10), lower wick down to 1.0950 (60), upper wick to 1.1012 (2).
    candle = _candle("1.1000", "1.1012", "1.0950", "1.1010")
    result = detect_candlestick_pattern([candle])
    assert result is not None
    assert result.name is CandlestickPatternName.HAMMER
    assert result.bias is PatternBias.BULLISH


def test_detects_shooting_star_on_long_upper_wick_small_lower_wick():
    candle = _candle("1.1015", "1.1070", "1.1001", "1.1005")
    result = detect_candlestick_pattern([candle])
    assert result is not None
    assert result.name is CandlestickPatternName.SHOOTING_STAR
    assert result.bias is PatternBias.BEARISH


def test_detects_bullish_engulfing():
    prev = _candle("1.1020", "1.1025", "1.0990", "1.1000")  # bearish, body 20 pips
    last = _candle("1.0995", "1.1040", "1.0990", "1.1030")  # bullish, engulfs prev body
    result = detect_candlestick_pattern([prev, last])
    assert result is not None
    assert result.name is CandlestickPatternName.BULLISH_ENGULFING
    assert result.bias is PatternBias.BULLISH


def test_detects_bearish_engulfing():
    prev = _candle("1.1000", "1.1025", "1.0995", "1.1020")  # bullish, body 20 pips
    last = _candle("1.1030", "1.1035", "1.0990", "1.0995")  # bearish, engulfs prev body
    result = detect_candlestick_pattern([prev, last])
    assert result is not None
    assert result.name is CandlestickPatternName.BEARISH_ENGULFING
    assert result.bias is PatternBias.BEARISH


def test_engulfing_takes_priority_over_single_candle_pattern():
    # The "last" candle here also happens to have a small-ish body, but the
    # engulfing relationship with prev should still be reported first.
    prev = _candle("1.1020", "1.1025", "1.0990", "1.1000")
    last = _candle("1.0995", "1.1040", "1.0990", "1.1030")
    result = detect_candlestick_pattern([prev, last])
    assert result.name is CandlestickPatternName.BULLISH_ENGULFING


def test_no_pattern_for_an_ordinary_trending_candle():
    # A normal bullish candle with a modest body and modest wicks on both
    # sides — none of the pattern thresholds should fire.
    candle = _candle("1.1000", "1.1030", "1.0995", "1.1025")
    result = detect_candlestick_pattern([candle])
    assert result is None
