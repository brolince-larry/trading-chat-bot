from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_paper_trading_service
from app.domain.trading.models import PositionStatus
from app.domain.trading.paper_trading_service import (
    PaperTradingError,
    PaperTradingService,
)
from app.schemas.positions import (
    ClosePositionRequest,
    OpenPositionRequest,
    PerformanceStatsOut,
    PositionOut,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/positions", tags=["positions"])


@router.get("", response_model=list[PositionOut])
def list_positions(
    status: str = Query(default="open", pattern="^(open|closed)$"),
    service: PaperTradingService = Depends(get_paper_trading_service),
) -> list[PositionOut]:
    if status == "open":
        return [PositionOut.from_domain(p, pnl) for p, pnl in service.list_open_with_pnl()]
    return [PositionOut.from_domain(p) for p in service.list_closed()]


@router.get("/stats", response_model=PerformanceStatsOut)
def get_performance_stats(
    service: PaperTradingService = Depends(get_paper_trading_service),
) -> PerformanceStatsOut:
    return PerformanceStatsOut.from_domain(service.performance_stats())


@router.post("/open", response_model=PositionOut, status_code=201)
def open_position(
    request: OpenPositionRequest,
    service: PaperTradingService = Depends(get_paper_trading_service),
) -> PositionOut:
    try:
        position = service.open_position(
            symbol=request.symbol,
            strategy=request.strategy,
            direction=request.direction,
            entry_price=request.entry_price,
            stop_loss=request.stop_loss,
            take_profit=request.take_profit,
            lots=request.lots,
            units=request.units,
            account_currency=request.account_currency,
            pip_value_per_unit=request.pip_value_per_unit,
        )
    except PaperTradingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return PositionOut.from_domain(position)


@router.post("/{position_id}/close", response_model=PositionOut)
def close_position(
    position_id: str,
    request: ClosePositionRequest,
    service: PaperTradingService = Depends(get_paper_trading_service),
) -> PositionOut:
    try:
        position = service.close_position(
            position_id, close_price=request.close_price, reason=PositionStatus.CLOSED_MANUAL
        )
    except PaperTradingError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    return PositionOut.from_domain(position)
