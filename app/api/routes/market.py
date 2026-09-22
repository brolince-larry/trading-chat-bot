from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_market_data_provider
from app.domain.market.data_provider import MarketDataProvider
from app.domain.market.models import Timeframe
from app.domain.market.symbols import get_symbol, list_symbols
from app.schemas.market import CandleOut, PriceOut, SymbolOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/market", tags=["market"])

MAX_CANDLE_COUNT = 500


@router.get("/symbols", response_model=list[SymbolOut])
def get_symbols() -> list[SymbolOut]:
    return [SymbolOut.from_domain(spec) for spec in list_symbols()]


@router.get("/{symbol}/price", response_model=PriceOut)
def get_price(
    symbol: str, provider: MarketDataProvider = Depends(get_market_data_provider)
) -> PriceOut:
    spec = _resolve_symbol(symbol)
    try:
        price = provider.get_price(spec.name)
    except Exception:
        logger.exception("Failed to fetch live price for %s", spec.name)
        raise HTTPException(status_code=502, detail="Live price is temporarily unavailable.") from None
    return PriceOut.from_domain(price, spec.pip_size)


@router.get("/{symbol}/candles", response_model=list[CandleOut])
def get_candles(
    symbol: str,
    timeframe: Timeframe = Query(default=Timeframe.H1),
    count: int = Query(default=200, ge=1, le=MAX_CANDLE_COUNT),
    provider: MarketDataProvider = Depends(get_market_data_provider),
) -> list[CandleOut]:
    spec = _resolve_symbol(symbol)
    try:
        candles = provider.get_candles(spec.name, timeframe, count)
    except Exception:
        logger.exception("Failed to fetch candles for %s", spec.name)
        raise HTTPException(status_code=502, detail="Historical candles are temporarily unavailable.") from None
    return [CandleOut.from_domain(c) for c in candles]


def _resolve_symbol(symbol: str):
    try:
        return get_symbol(symbol)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Unsupported symbol: {symbol}") from None
