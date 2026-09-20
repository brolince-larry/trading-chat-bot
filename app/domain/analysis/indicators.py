"""Deterministic technical indicator calculations.

Every function is a pure, stateless transform over a sequence of closes or
candles. Indicator math operates on ``float`` (these are derived analytical
values, not money), while trade/account money math elsewhere in the codebase
stays on ``Decimal``. Each series is returned aligned to the input length,
with ``None`` for indices that don't yet have enough history.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.market.models import Candle


def sma(values: Sequence[float], period: int) -> list[float | None]:
    if period <= 0:
        raise ValueError("period must be positive")
    out: list[float | None] = [None] * len(values)
    window_sum = 0.0
    for i, value in enumerate(values):
        window_sum += value
        if i >= period:
            window_sum -= values[i - period]
        if i >= period - 1:
            out[i] = window_sum / period
    return out


def ema(values: Sequence[float], period: int) -> list[float | None]:
    if period <= 0:
        raise ValueError("period must be positive")
    out: list[float | None] = [None] * len(values)
    if len(values) < period:
        return out

    multiplier = 2.0 / (period + 1)
    seed = sum(values[:period]) / period
    out[period - 1] = seed
    prev = seed
    for i in range(period, len(values)):
        prev = (values[i] - prev) * multiplier + prev
        out[i] = prev
    return out


def rsi(values: Sequence[float], period: int = 14) -> list[float | None]:
    """Wilder's RSI."""
    out: list[float | None] = [None] * len(values)
    if len(values) < period + 1:
        return out

    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        change = values[i] - values[i - 1]
        gains += max(change, 0.0)
        losses += max(-change, 0.0)

    avg_gain = gains / period
    avg_loss = losses / period
    out[period] = _rsi_from_averages(avg_gain, avg_loss)

    for i in range(period + 1, len(values)):
        change = values[i] - values[i - 1]
        gain = max(change, 0.0)
        loss = max(-change, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        out[i] = _rsi_from_averages(avg_gain, avg_loss)

    return out


def _rsi_from_averages(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def true_range(candles: Sequence[Candle]) -> list[float]:
    out: list[float] = [0.0] * len(candles)
    for i, candle in enumerate(candles):
        high = float(candle.high)
        low = float(candle.low)
        if i == 0:
            out[i] = high - low
            continue
        prev_close = float(candles[i - 1].close)
        out[i] = max(high - low, abs(high - prev_close), abs(low - prev_close))
    return out


def atr(candles: Sequence[Candle], period: int = 14) -> list[float | None]:
    """Wilder's ATR."""
    tr = true_range(candles)
    out: list[float | None] = [None] * len(candles)
    if len(candles) < period:
        return out

    avg = sum(tr[1 : period + 1]) / period if len(tr) > period else sum(tr[:period]) / period
    out[period - 1] = avg
    prev = avg
    for i in range(period, len(candles)):
        prev = (prev * (period - 1) + tr[i]) / period
        out[i] = prev
    return out


def adx(
    candles: Sequence[Candle], period: int = 14
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    """Wilder's ADX, +DI and -DI. Returns (adx, plus_di, minus_di)."""
    n = len(candles)
    plus_di: list[float | None] = [None] * n
    minus_di: list[float | None] = [None] * n
    adx_out: list[float | None] = [None] * n
    if n < period + 1:
        return adx_out, plus_di, minus_di

    tr = true_range(candles)
    plus_dm = [0.0] * n
    minus_dm = [0.0] * n
    for i in range(1, n):
        up_move = float(candles[i].high) - float(candles[i - 1].high)
        down_move = float(candles[i - 1].low) - float(candles[i].low)
        plus_dm[i] = up_move if (up_move > down_move and up_move > 0) else 0.0
        minus_dm[i] = down_move if (down_move > up_move and down_move > 0) else 0.0

    smoothed_tr = sum(tr[1 : period + 1])
    smoothed_plus_dm = sum(plus_dm[1 : period + 1])
    smoothed_minus_dm = sum(minus_dm[1 : period + 1])

    dx_values: list[float | None] = [None] * n

    def _fill(idx: int, s_tr: float, s_plus: float, s_minus: float) -> float:
        p_di = 100.0 * (s_plus / s_tr) if s_tr else 0.0
        m_di = 100.0 * (s_minus / s_tr) if s_tr else 0.0
        plus_di[idx] = p_di
        minus_di[idx] = m_di
        di_sum = p_di + m_di
        dx = 100.0 * abs(p_di - m_di) / di_sum if di_sum else 0.0
        dx_values[idx] = dx
        return dx

    _fill(period, smoothed_tr, smoothed_plus_dm, smoothed_minus_dm)

    for i in range(period + 1, n):
        smoothed_tr = smoothed_tr - (smoothed_tr / period) + tr[i]
        smoothed_plus_dm = smoothed_plus_dm - (smoothed_plus_dm / period) + plus_dm[i]
        smoothed_minus_dm = smoothed_minus_dm - (smoothed_minus_dm / period) + minus_dm[i]
        _fill(i, smoothed_tr, smoothed_plus_dm, smoothed_minus_dm)

    first_adx_idx = period * 2 - 1
    if first_adx_idx < n:
        valid_dx = [d for d in dx_values[period : first_adx_idx + 1] if d is not None]
        adx_out[first_adx_idx] = sum(valid_dx) / len(valid_dx) if valid_dx else None
        prev_adx = adx_out[first_adx_idx]
        for i in range(first_adx_idx + 1, n):
            dx_i = dx_values[i] or 0.0
            prev_adx = ((prev_adx or 0.0) * (period - 1) + dx_i) / period
            adx_out[i] = prev_adx

    return adx_out, plus_di, minus_di


def macd(
    values: Sequence[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    fast_ema = ema(values, fast)
    slow_ema = ema(values, slow)
    macd_line: list[float | None] = [
        (f - s) if f is not None and s is not None else None
        for f, s in zip(fast_ema, slow_ema, strict=True)
    ]

    signal_input = [m for m in macd_line if m is not None]
    signal_ema_raw = ema(signal_input, signal) if signal_input else []

    signal_line: list[float | None] = [None] * len(values)
    offset = len(macd_line) - len(signal_input)
    for i, val in enumerate(signal_ema_raw):
        if val is not None:
            signal_line[i + offset] = val

    histogram: list[float | None] = [
        (m - s) if m is not None and s is not None else None
        for m, s in zip(macd_line, signal_line, strict=True)
    ]
    return macd_line, signal_line, histogram


def bollinger_bands(
    values: Sequence[float], period: int = 20, num_std: float = 2.0
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    middle = sma(values, period)
    upper: list[float | None] = [None] * len(values)
    lower: list[float | None] = [None] * len(values)

    for i in range(len(values)):
        mid = middle[i]
        if mid is None:
            continue
        window = values[i - period + 1 : i + 1]
        variance = sum((v - mid) ** 2 for v in window) / period
        std_dev = variance**0.5
        upper[i] = mid + num_std * std_dev
        lower[i] = mid - num_std * std_dev

    return upper, middle, lower
