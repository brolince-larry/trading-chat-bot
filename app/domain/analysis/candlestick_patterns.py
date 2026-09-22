"""Deterministic candlestick pattern recognition.

Plain geometric rules against real OHLC data — the same "no LLM decides
market structure" principle as the rest of ``app.domain.analysis``. Each
pattern is a widely-used textbook definition (body-to-range ratios, wick
ratios), not a fabricated or fuzzy classification.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from app.domain.market.models import Candle

_DOJI_MAX_BODY_RATIO = Decimal("0.1")
_PIN_MIN_WICK_TO_BODY = Decimal("2.0")
_PIN_MAX_OPPOSITE_WICK_TO_BODY = Decimal("0.5")
_ENGULFING_MIN_BODY_GROWTH = Decimal("1.0")


class CandlestickPatternName(str, Enum):
    DOJI = "doji"
    HAMMER = "hammer"
    SHOOTING_STAR = "shooting_star"
    BULLISH_ENGULFING = "bullish_engulfing"
    BEARISH_ENGULFING = "bearish_engulfing"


class PatternBias(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass(frozen=True, slots=True)
class CandlestickPattern:
    name: CandlestickPatternName
    bias: PatternBias


def detect_candlestick_pattern(candles: list[Candle]) -> CandlestickPattern | None:
    """Checks the most recent candle(s) for a recognized pattern.

    Two-candle patterns (engulfing) take priority over single-candle ones
    since they're the stronger reversal signal when both are present.
    """
    if len(candles) < 1:
        return None

    if len(candles) >= 2:
        engulfing = _detect_engulfing(candles[-2], candles[-1])
        if engulfing is not None:
            return engulfing

    return _detect_single_candle_pattern(candles[-1])


def _detect_engulfing(prev: Candle, last: Candle) -> CandlestickPattern | None:
    if prev.body <= 0 or last.body <= prev.body * _ENGULFING_MIN_BODY_GROWTH:
        return None

    if (
        last.is_bullish
        and prev.is_bearish
        and last.open <= prev.close
        and last.close >= prev.open
    ):
        return CandlestickPattern(CandlestickPatternName.BULLISH_ENGULFING, PatternBias.BULLISH)

    if (
        last.is_bearish
        and prev.is_bullish
        and last.open >= prev.close
        and last.close <= prev.open
    ):
        return CandlestickPattern(CandlestickPatternName.BEARISH_ENGULFING, PatternBias.BEARISH)

    return None


def _detect_single_candle_pattern(candle: Candle) -> CandlestickPattern | None:
    candle_range = candle.range
    if candle_range <= 0:
        return None

    body = candle.body
    if body <= _DOJI_MAX_BODY_RATIO * candle_range:
        return CandlestickPattern(CandlestickPatternName.DOJI, PatternBias.NEUTRAL)

    if body <= 0:
        return None

    upper_wick = candle.high - max(candle.open, candle.close)
    lower_wick = min(candle.open, candle.close) - candle.low

    if lower_wick >= _PIN_MIN_WICK_TO_BODY * body and upper_wick <= _PIN_MAX_OPPOSITE_WICK_TO_BODY * body:
        return CandlestickPattern(CandlestickPatternName.HAMMER, PatternBias.BULLISH)

    if upper_wick >= _PIN_MIN_WICK_TO_BODY * body and lower_wick <= _PIN_MAX_OPPOSITE_WICK_TO_BODY * body:
        return CandlestickPattern(CandlestickPatternName.SHOOTING_STAR, PatternBias.BEARISH)

    return None
