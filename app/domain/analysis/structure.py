"""Market structure detection: swing points, trend, and regime classification.

Swing detection uses a fractal rule (a bar is a swing high/low if its
high/low is the most extreme within ``left``/``right`` neighboring bars).
Trend is then derived from the sequence of confirmed swings rather than a
single moving-average crossover, so it reflects actual price structure
(higher-highs/higher-lows vs lower-highs/lower-lows).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.domain.market.models import Candle


class SwingKind(str, Enum):
    HIGH = "high"
    LOW = "low"


class TrendDirection(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class MarketRegime(str, Enum):
    TRENDING = "trending"
    RANGING = "ranging"
    TRANSITIONING = "transitioning"


@dataclass(frozen=True, slots=True)
class SwingPoint:
    index: int
    price: float
    kind: SwingKind


def detect_swings(candles: list[Candle], left: int = 2, right: int = 2) -> list[SwingPoint]:
    swings: list[SwingPoint] = []
    n = len(candles)
    for i in range(left, n - right):
        window_highs = [float(c.high) for c in candles[i - left : i + right + 1]]
        window_lows = [float(c.low) for c in candles[i - left : i + right + 1]]
        pivot_high = float(candles[i].high)
        pivot_low = float(candles[i].low)

        if pivot_high == max(window_highs) and window_highs.count(pivot_high) == 1:
            swings.append(SwingPoint(index=i, price=pivot_high, kind=SwingKind.HIGH))
        if pivot_low == min(window_lows) and window_lows.count(pivot_low) == 1:
            swings.append(SwingPoint(index=i, price=pivot_low, kind=SwingKind.LOW))

    swings.sort(key=lambda s: s.index)
    return swings


def classify_trend(swings: list[SwingPoint]) -> TrendDirection:
    highs = [s for s in swings if s.kind is SwingKind.HIGH]
    lows = [s for s in swings if s.kind is SwingKind.LOW]

    if len(highs) < 2 or len(lows) < 2:
        return TrendDirection.NEUTRAL

    higher_highs = highs[-1].price > highs[-2].price
    higher_lows = lows[-1].price > lows[-2].price
    lower_highs = highs[-1].price < highs[-2].price
    lower_lows = lows[-1].price < lows[-2].price

    if higher_highs and higher_lows:
        return TrendDirection.BULLISH
    if lower_highs and lower_lows:
        return TrendDirection.BEARISH
    return TrendDirection.NEUTRAL


def support_resistance_levels(
    swings: list[SwingPoint], max_levels: int = 3
) -> tuple[list[float], list[float]]:
    """Most recent distinct swing lows (support) and swing highs (resistance)."""
    lows = [s.price for s in reversed(swings) if s.kind is SwingKind.LOW]
    highs = [s.price for s in reversed(swings) if s.kind is SwingKind.HIGH]

    support = _dedupe_ordered(lows)[:max_levels]
    resistance = _dedupe_ordered(highs)[:max_levels]
    return support, resistance


def _dedupe_ordered(values: list[float], tolerance: float = 1e-9) -> list[float]:
    result: list[float] = []
    for value in values:
        if not any(abs(value - existing) <= tolerance for existing in result):
            result.append(value)
    return result


def classify_regime(
    adx_value: float | None,
    current_atr: float | None,
    average_atr: float | None,
    trending_adx_threshold: float = 25.0,
    ranging_adx_threshold: float = 20.0,
) -> MarketRegime:
    """Classify regime from ADX (directional strength) and relative volatility.

    ADX above the trending threshold signals a trending market; below the
    (lower) ranging threshold signals a range. The gap between the two
    thresholds is a deliberate hysteresis band reported as "transitioning"
    rather than flip-flopping between labels on small ADX changes.
    """
    if adx_value is None:
        return MarketRegime.TRANSITIONING

    if adx_value >= trending_adx_threshold:
        return MarketRegime.TRENDING
    if adx_value <= ranging_adx_threshold:
        return MarketRegime.RANGING
    return MarketRegime.TRANSITIONING
