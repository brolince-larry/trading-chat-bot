from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_market_data_provider
from app.domain.backtest.engine import BacktestError, run_backtest
from app.domain.market.data_provider import MarketDataProvider
from app.domain.strategies import ALL_STRATEGIES
from app.schemas.backtest import BacktestRequest, BacktestResultOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/backtest", tags=["backtest"])

_STRATEGIES_BY_NAME = {s.name: s for s in ALL_STRATEGIES}


@router.post("/run", response_model=BacktestResultOut)
def backtest_run(
    request: BacktestRequest,
    provider: MarketDataProvider = Depends(get_market_data_provider),
) -> BacktestResultOut:
    strategy = _STRATEGIES_BY_NAME[request.strategy]
    try:
        result = run_backtest(
            provider=provider,
            symbol=request.symbol,
            strategy=strategy,
            higher_timeframe=request.higher_timeframe,
            entry_timeframe=request.entry_timeframe,
            lookback_candles=request.lookback_candles,
            starting_balance=request.starting_balance,
            risk_percent=request.risk_percent,
            account_currency=request.account_currency,
            quote_to_account_rate=request.quote_to_account_rate,
        )
    except BacktestError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except Exception:
        logger.exception("Backtest failed for symbol=%s strategy=%s", request.symbol, request.strategy)
        raise HTTPException(status_code=502, detail="The backtest could not be completed.") from None
    return BacktestResultOut.from_domain(result)
