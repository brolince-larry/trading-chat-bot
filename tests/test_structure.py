from __future__ import annotations

from app.domain.analysis.structure import (
    MarketRegime,
    SwingKind,
    TrendDirection,
    classify_regime,
    classify_trend,
    detect_swings,
    support_resistance_levels,
)
from tests.conftest import build_candles


def test_detect_swings_finds_alternating_highs_and_lows():
    closes = [1.0, 1.05, 1.02, 1.08, 1.03, 1.10, 1.04]
    candles = build_candles(closes, wick_pad=0.0)
    swings = detect_swings(candles, left=1, right=1)
    assert any(s.kind is SwingKind.HIGH for s in swings)
    assert any(s.kind is SwingKind.LOW for s in swings)


def test_classify_trend_bullish_on_higher_highs_and_lows():
    highs = [1.0, 1.1, 1.15, 1.2, 1.25]
    lows = [0.9, 0.95, 1.0, 1.02, 1.08]
    from app.domain.analysis.structure import SwingPoint

    swings = [SwingPoint(index=i, price=h, kind=SwingKind.HIGH) for i, h in enumerate(highs)]
    swings += [SwingPoint(index=i, price=low, kind=SwingKind.LOW) for i, low in enumerate(lows)]
    assert classify_trend(swings) is TrendDirection.BULLISH


def test_classify_trend_bearish_on_lower_highs_and_lows():
    from app.domain.analysis.structure import SwingPoint

    highs = [1.2, 1.15, 1.1, 1.05]
    lows = [1.1, 1.0, 0.95, 0.9]
    swings = [SwingPoint(index=i, price=h, kind=SwingKind.HIGH) for i, h in enumerate(highs)]
    swings += [SwingPoint(index=i, price=low, kind=SwingKind.LOW) for i, low in enumerate(lows)]
    assert classify_trend(swings) is TrendDirection.BEARISH


def test_classify_trend_neutral_with_insufficient_swings():
    assert classify_trend([]) is TrendDirection.NEUTRAL


def test_support_resistance_levels_are_deduplicated_and_ordered_by_recency():
    from app.domain.analysis.structure import SwingPoint

    swings = [
        SwingPoint(index=0, price=1.10, kind=SwingKind.LOW),
        SwingPoint(index=1, price=1.20, kind=SwingKind.HIGH),
        SwingPoint(index=2, price=1.10, kind=SwingKind.LOW),  # duplicate
        SwingPoint(index=3, price=1.05, kind=SwingKind.LOW),
    ]
    support, resistance = support_resistance_levels(swings, max_levels=5)
    assert support[0] == 1.05  # most recent first
    assert 1.10 in support
    assert support.count(1.10) == 1
    assert resistance == [1.20]


def test_classify_regime_trending_above_threshold():
    assert classify_regime(30.0, 0.001, 0.001) is MarketRegime.TRENDING


def test_classify_regime_ranging_below_threshold():
    assert classify_regime(10.0, 0.001, 0.001) is MarketRegime.RANGING


def test_classify_regime_transitioning_in_hysteresis_band():
    assert classify_regime(22.0, 0.001, 0.001) is MarketRegime.TRANSITIONING


def test_classify_regime_transitioning_when_adx_missing():
    assert classify_regime(None, None, None) is MarketRegime.TRANSITIONING
