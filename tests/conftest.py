from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal

from app.domain.analysis.structure import MarketRegime, TrendDirection
from app.domain.analysis.timeframe_analysis import (
    TimeframeAnalysis,
    compute_timeframe_analysis,
)
from app.domain.market.models import Candle, Timeframe
from app.domain.strategies.base import Direction


def build_candles(
    closes: list[float],
    symbol: str = "EUR_USD",
    timeframe: Timeframe = Timeframe.H1,
    wick_pad: float = 0.0002,
) -> list[Candle]:
    """Build a simple candle series from a list of closes.

    Each candle opens at the previous close (or the first close for the
    first bar) and gets a small wick beyond the open/close range, which is
    enough for indicator/structure tests without needing real market data.
    """
    start = datetime(2024, 1, 1, tzinfo=UTC)
    step = timedelta(minutes=timeframe.minutes)
    candles: list[Candle] = []
    prev_close = closes[0]
    for i, close in enumerate(closes):
        open_ = prev_close
        # A tiny deterministic-but-non-monotonic jitter (far smaller than
        # wick_pad or the price step size) keeps consecutive candle
        # highs/lows from tying exactly, which would otherwise happen
        # whenever candle i's close becomes candle i+1's open at a local
        # peak/trough — and break fractal-based swing detection in tests
        # that use this fixture. It must be non-monotonic in ``i``, or a
        # later, unrelated candle would always "win" a tie against the
        # true local extreme purely because it comes later.
        epsilon = ((i * 2654435761) % 1000) * 1e-9
        high = max(open_, close) + wick_pad + epsilon
        low = min(open_, close) - wick_pad - epsilon
        candles.append(
            Candle(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=start + step * i,
                open=Decimal(str(round(open_, 8))),
                high=Decimal(str(round(high, 8))),
                low=Decimal(str(round(low, 8))),
                close=Decimal(str(round(close, 8))),
            )
        )
        prev_close = close
    return candles


def staircase_closes(n_cycles: int, up_total: float, down_total: float, leg_len: int, base: float) -> list[float]:
    """A "two steps forward, one step back" close series: enough swing
    structure for fractal-based trend detection, with net drift set by
    ``up_total``/``down_total`` per cycle.
    """
    closes = [base]
    price = base
    for _ in range(n_cycles):
        for _ in range(leg_len):
            price += up_total / leg_len
            closes.append(price)
        for _ in range(leg_len):
            price -= down_total / leg_len
            closes.append(price)
    return closes


def make_timeframe_analysis(
    *,
    symbol: str = "EUR_USD",
    timeframe: Timeframe = Timeframe.H1,
    last_close: float = 1.1000,
    ema_20: float | None = 1.0990,
    ema_50: float | None = 1.0970,
    ema_200: float | None = 1.0900,
    rsi_14: float | None = 50.0,
    atr_14: float | None = 0.0010,
    average_atr_14: float | None = 0.0010,
    adx_14: float | None = 15.0,
    trend: TrendDirection = TrendDirection.NEUTRAL,
    regime: MarketRegime = MarketRegime.RANGING,
    support_levels: list[float] | None = None,
    resistance_levels: list[float] | None = None,
    candles: list[Candle] | None = None,
) -> TimeframeAnalysis:
    """Directly construct a :class:`TimeframeAnalysis` with explicit,
    caller-controlled indicator values.

    Strategy unit tests care about decision boundaries (e.g. "RSI >= 65 AND
    within 0.4 ATR of resistance"), not about reverse-engineering an OHLC
    series that happens to produce those exact values through the real
    indicator pipeline. Constructing the analysis object directly keeps
    those tests precise and readable; separate integration tests cover the
    real indicator -> structure -> strategy pipeline end to end.
    """
    return TimeframeAnalysis(
        symbol=symbol,
        timeframe=timeframe,
        last_close=last_close,
        ema_20=ema_20,
        ema_50=ema_50,
        ema_200=ema_200,
        rsi_14=rsi_14,
        atr_14=atr_14,
        average_atr_14=average_atr_14,
        adx_14=adx_14,
        trend=trend,
        regime=regime,
        support_levels=support_levels or [],
        resistance_levels=resistance_levels or [],
        swings=[],
        candles=candles or [],
    )


def build_trend_pullback_scenario(
    direction: Literal["long", "short"], outcome: Literal["watching", "confirmed"]
) -> tuple[TimeframeAnalysis, TimeframeAnalysis]:
    """Build a real (higher_tf, entry_tf) pair, computed through the actual
    indicator/structure pipeline, that exercises
    :class:`TrendPullbackStrategy`'s "watching" or "confirmed" branch.

    This is an integration-style fixture: rather than asserting on hardcoded
    numbers, it engineers each next candle from the *live* EMA/ATR of the
    series built so far, so it stays correct if indicator internals change.
    """
    bullish = direction == "long"
    sign = 1 if bullish else -1

    higher_closes = (
        staircase_closes(60, 0.0060, 0.0020, 4, 1.0500)
        if bullish
        else staircase_closes(60, 0.0020, 0.0060, 4, 1.2000)
    )
    higher_candles = build_candles(higher_closes, timeframe=Timeframe.H4, wick_pad=0.0001)
    higher_tf = compute_timeframe_analysis("EUR_USD", Timeframe.H4, higher_candles)

    base_closes = (
        staircase_closes(20, 0.0060, 0.0020, 4, 1.1000)
        if bullish
        else staircase_closes(20, 0.0020, 0.0060, 4, 1.2000)
    )
    base_candles = build_candles(base_closes, timeframe=Timeframe.H1)
    base_analysis = compute_timeframe_analysis("EUR_USD", Timeframe.H1, base_candles)

    target = base_analysis.ema_20 + sign * 0.3 * base_analysis.atr_14
    last_close = float(base_candles[-1].close)
    steps = 4
    pullback_closes = [last_close + (target - last_close) * i / steps for i in range(1, steps + 1)]
    closes = base_closes + pullback_closes

    if outcome == "confirmed":
        pullback_candles = build_candles(closes, timeframe=Timeframe.H1)
        confirm_close = (
            float(pullback_candles[-1].high) + 0.0010
            if bullish
            else float(pullback_candles[-1].low) - 0.0010
        )
        closes = closes + [confirm_close]

    entry_candles = build_candles(closes, timeframe=Timeframe.H1)
    entry_tf = compute_timeframe_analysis("EUR_USD", Timeframe.H1, entry_candles)
    return higher_tf, entry_tf


def build_breakout_retest_candles(
    direction: Literal["long", "short"], outcome: Literal["rejected", "watching", "confirmed"]
) -> list[Candle]:
    """Build a range -> breakout -> (optional retest/confirmation) candle
    series for :class:`BreakoutRetestStrategy`.

    The strategy defines its range from ``candles[-36:-6]`` and looks for a
    breakout/retest within the final 6 bars, so this builder keeps a 54-bar
    ranging lead-in (oscillating, non-trending) and constructs those exact
    final 6 bars to hit each outcome.
    """
    bullish = direction == "long"
    base = 1.1015
    amplitude = 0.0012
    lead_in_bars = 54

    oscillation = [base + amplitude * math.sin(i * 0.6) for i in range(lead_in_bars)]
    oscillation_candles = build_candles(oscillation, wick_pad=0.0001)
    # Mirrors the strategy's own candles[-36:-6] slice once 6 event bars follow.
    range_slice = oscillation_candles[24:54]
    range_high = max(float(c.high) for c in range_slice)
    range_low = min(float(c.low) for c in range_slice)
    representative_atr = 0.0006

    closes = list(oscillation)

    if outcome == "rejected":
        closes += [
            oscillation[-1],
            oscillation[-1] + 0.0001,
            oscillation[-1] - 0.0001,
            oscillation[-1] + 0.0001,
            oscillation[-1],
            oscillation[-1] + 0.0001,
        ]
        return build_candles(closes, wick_pad=0.0001)

    drift = 0.0002 if bullish else -0.0002
    breakout_close = range_high + 1.2 * representative_atr if bullish else range_low - 1.2 * representative_atr
    bar1 = breakout_close + drift
    bar2 = bar1 + drift

    if outcome == "watching":
        bar3 = bar2 + drift
        bar4 = bar3 + drift
        bar5 = bar4 + drift
        closes += [breakout_close, bar1, bar2, bar3, bar4, bar5]
        return build_candles(closes, wick_pad=0.0001)

    # confirmed: drift back toward the level, then a final bar that dips to
    # retest it and closes back beyond it (bullish for a long breakout).
    if bullish:
        bar3 = bar2 - 0.3 * representative_atr
        bar4 = range_high + 0.05 * representative_atr
        final_close = range_high + 0.20 * representative_atr
    else:
        bar3 = bar2 + 0.3 * representative_atr
        bar4 = range_low - 0.05 * representative_atr
        final_close = range_low - 0.20 * representative_atr
    closes += [breakout_close, bar1, bar2, bar3, bar4, final_close]
    return build_candles(closes, wick_pad=0.0001)


__all__ = [
    "Direction",
    "build_breakout_retest_candles",
    "build_candles",
    "build_trend_pullback_scenario",
    "make_timeframe_analysis",
    "staircase_closes",
]
