from __future__ import annotations

from pydantic import BaseModel

from app.domain.analysis.structure import MarketRegime, TrendDirection
from app.domain.analysis.timeframe_analysis import TimeframeAnalysis
from app.domain.market.models import Timeframe


class TimeframeAnalysisOut(BaseModel):
    timeframe: Timeframe
    last_close: float
    ema_20: float | None
    ema_50: float | None
    ema_200: float | None
    rsi_14: float | None
    atr_14: float | None
    adx_14: float | None
    trend: TrendDirection
    regime: MarketRegime
    support_levels: list[float]
    resistance_levels: list[float]

    @classmethod
    def from_domain(cls, analysis: TimeframeAnalysis) -> "TimeframeAnalysisOut":
        return cls(
            timeframe=analysis.timeframe,
            last_close=analysis.last_close,
            ema_20=analysis.ema_20,
            ema_50=analysis.ema_50,
            ema_200=analysis.ema_200,
            rsi_14=analysis.rsi_14,
            atr_14=analysis.atr_14,
            adx_14=analysis.adx_14,
            trend=analysis.trend,
            regime=analysis.regime,
            support_levels=analysis.support_levels,
            resistance_levels=analysis.resistance_levels,
        )


class PairAnalysisOut(BaseModel):
    symbol: str
    higher_timeframe: TimeframeAnalysisOut
    entry_timeframe: TimeframeAnalysisOut
