from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_market_data_provider
from app.domain.analysis.timeframe_analysis import compute_timeframe_analysis
from app.domain.market.data_provider import MarketDataProvider
from app.domain.market.models import Timeframe
from app.domain.market.symbols import get_symbol
from app.domain.scanner.pair_scanner import DEFAULT_LOOKBACK_CANDLES
from app.schemas.analysis import PairAnalysisOut, TimeframeAnalysisOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/{symbol}", response_model=PairAnalysisOut)
def get_pair_analysis(
    symbol: str,
    higher_timeframe: Timeframe = Query(default=Timeframe.H4),
    entry_timeframe: Timeframe = Query(default=Timeframe.H1),
    lookback: int = Query(default=DEFAULT_LOOKBACK_CANDLES, ge=60, le=1000),
    provider: MarketDataProvider = Depends(get_market_data_provider),
) -> PairAnalysisOut:
    try:
        spec = get_symbol(symbol)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Unsupported symbol: {symbol}") from None

    try:
        higher_candles = provider.get_candles(spec.name, higher_timeframe, lookback)
        entry_candles = provider.get_candles(spec.name, entry_timeframe, lookback)
        higher_analysis = compute_timeframe_analysis(spec.name, higher_timeframe, higher_candles)
        entry_analysis = compute_timeframe_analysis(spec.name, entry_timeframe, entry_candles)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except Exception:
        logger.exception("Failed to compute analysis for %s", spec.name)
        raise HTTPException(status_code=502, detail="Market analysis is temporarily unavailable.") from None

    return PairAnalysisOut(
        symbol=spec.name,
        higher_timeframe=TimeframeAnalysisOut.from_domain(higher_analysis),
        entry_timeframe=TimeframeAnalysisOut.from_domain(entry_analysis),
    )
