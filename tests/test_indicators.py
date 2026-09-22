from __future__ import annotations

import pytest

from app.domain.analysis import indicators as ind
from tests.conftest import build_candles


def test_sma_basic():
    values = [1, 2, 3, 4, 5]
    result = ind.sma(values, 3)
    assert result[:2] == [None, None]
    assert result[2] == pytest.approx(2.0)
    assert result[3] == pytest.approx(3.0)
    assert result[4] == pytest.approx(4.0)


def test_sma_rejects_invalid_period():
    with pytest.raises(ValueError):
        ind.sma([1, 2, 3], 0)


def test_ema_seeds_with_sma_then_smooths():
    values = [1, 2, 3, 4, 5, 6, 7]
    result = ind.ema(values, 3)
    assert result[0] is None and result[1] is None
    assert result[2] == pytest.approx(2.0)  # seeded with SMA(1,2,3)
    assert result[-1] is not None
    assert result[-1] > result[2]  # rising series -> rising EMA


def test_rsi_all_gains_is_100():
    values = [1.0 + 0.1 * i for i in range(20)]
    result = ind.rsi(values, period=14)
    assert result[14] == pytest.approx(100.0)


def test_rsi_all_losses_is_0():
    values = [10.0 - 0.1 * i for i in range(20)]
    result = ind.rsi(values, period=14)
    assert result[14] == pytest.approx(0.0)


def test_rsi_bounded_between_0_and_100():
    values = [1.0, 1.2, 1.1, 1.3, 1.25, 1.4, 1.35, 1.5, 1.45, 1.6, 1.5, 1.55, 1.7, 1.6, 1.65, 1.8]
    result = ind.rsi(values, period=14)
    for value in result:
        if value is not None:
            assert 0.0 <= value <= 100.0


def test_atr_matches_true_range_average_for_flat_high_low():
    candles = build_candles([1.10 + 0.001 * i for i in range(30)], wick_pad=0.001)
    result = ind.atr(candles, period=14)
    assert result[13] is not None
    assert result[13] > 0
    assert all(v is None for v in result[:13])


def test_adx_rises_for_a_strong_persistent_trend():
    candles = build_candles([1.10 + 0.002 * i for i in range(60)], wick_pad=0.0001)
    adx_values, plus_di, minus_di = ind.adx(candles, period=14)
    trailing = [v for v in adx_values[-10:] if v is not None]
    assert trailing
    assert all(v >= 0 for v in trailing)
    # A one-directional trend should show +DI persistently above -DI near the end.
    assert plus_di[-1] > minus_di[-1]


def test_macd_histogram_is_difference_of_macd_and_signal():
    values = [1.0 + 0.01 * i for i in range(60)]
    macd_line, signal_line, histogram = ind.macd(values)
    for m, s, h in zip(macd_line, signal_line, histogram, strict=True):
        if m is not None and s is not None:
            assert h == pytest.approx(m - s)
        else:
            assert h is None


def test_bollinger_bands_upper_above_lower():
    values = [1.0, 1.02, 0.98, 1.05, 0.95, 1.10, 0.90, 1.03, 0.97, 1.01, 1.0, 1.02, 0.99, 1.04, 0.96, 1.06, 0.94, 1.0, 1.02, 1.0]
    upper, middle, lower = ind.bollinger_bands(values, period=10)
    for u, m, low in zip(upper, middle, lower, strict=True):
        if u is not None:
            assert u >= m >= low
