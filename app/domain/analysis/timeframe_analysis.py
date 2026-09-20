"""Aggregates indicators + structure for one symbol/timeframe into one snapshot.

This is the object strategies and the AI explanation layer consume — the
"structured market data" the architecture calls for, as opposed to letting
anything downstream recompute indicators itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.analysis import indicators as ind
from app.domain.analysis.structure import (
    MarketRegime,
    SwingPoint,
    TrendDirection,
    classify_regime,
    classify_trend,
    detect_swings,
    support_resistance_levels,
)
from app.domain.market.models import Candle, Timeframe

MIN_CANDLES_REQUIRED = 60


@dataclass(frozen=True, slots=True)
class TimeframeAnalysis:
    symbol: str
    timeframe: Timeframe
    last_close: float
    ema_20: float | None
    ema_50: float | None
    ema_200: float | None
    rsi_14: float | None
    atr_14: float | None
    average_atr_14: float | None
    adx_14: float | None
    trend: TrendDirection
    regime: MarketRegime
    support_levels: list[float] = field(default_factory=list)
    resistance_levels: list[float] = field(default_factory=list)
    swings: list[SwingPoint] = field(default_factory=list)
    candles: list[Candle] = field(default_factory=list)

    @property
    def bullish_ema_alignment(self) -> bool:
        if self.ema_20 is None or self.ema_50 is None or self.ema_200 is None:
            return False
        return self.ema_20 > self.ema_50 > self.ema_200

    @property
    def bearish_ema_alignment(self) -> bool:
        if self.ema_20 is None or self.ema_50 is None or self.ema_200 is None:
            return False
        return self.ema_20 < self.ema_50 < self.ema_200


def compute_timeframe_analysis(
    symbol: str, timeframe: Timeframe, candles: list[Candle]
) -> TimeframeAnalysis:
    if len(candles) < MIN_CANDLES_REQUIRED:
        raise ValueError(
            f"Need at least {MIN_CANDLES_REQUIRED} candles for {symbol} {timeframe.value}, "
            f"got {len(candles)}"
        )

    closes = [float(c.close) for c in candles]

    ema_20 = ind.ema(closes, 20)
    ema_50 = ind.ema(closes, 50)
    ema_200_series = ind.ema(closes, 200)
    rsi_series = ind.rsi(closes, 14)
    atr_series = ind.atr(candles, 14)
    adx_series, _plus_di, _minus_di = ind.adx(candles, 14)

    recent_atr_values = [v for v in atr_series[-20:] if v is not None]
    average_atr = sum(recent_atr_values) / len(recent_atr_values) if recent_atr_values else None

    swings = detect_swings(candles)
    trend = classify_trend(swings)
    regime = classify_regime(adx_series[-1], atr_series[-1], average_atr)
    support, resistance = support_resistance_levels(swings)

    return TimeframeAnalysis(
        symbol=symbol,
        timeframe=timeframe,
        last_close=closes[-1],
        ema_20=ema_20[-1],
        ema_50=ema_50[-1],
        ema_200=ema_200_series[-1],
        rsi_14=rsi_series[-1],
        atr_14=atr_series[-1],
        average_atr_14=average_atr,
        adx_14=adx_series[-1],
        trend=trend,
        regime=regime,
        support_levels=support,
        resistance_levels=resistance,
        swings=swings,
        candles=candles,
    )
