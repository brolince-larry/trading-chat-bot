from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_risk_limits_repository
from app.domain.market.symbols import get_symbol
from app.domain.risk.position_sizing import calculate_position_size
from app.infrastructure.database.repositories import RiskLimitsRepository
from app.schemas.risk import (
    PositionSizeRequest,
    PositionSizeResponseOut,
    RiskLimitsOut,
    RiskLimitsUpdateRequest,
)

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/limits", response_model=RiskLimitsOut)
def get_risk_limits(repo: RiskLimitsRepository = Depends(get_risk_limits_repository)) -> RiskLimitsOut:
    return RiskLimitsOut.from_domain(repo.get())


@router.put("/limits", response_model=RiskLimitsOut)
def update_risk_limits(
    request: RiskLimitsUpdateRequest, repo: RiskLimitsRepository = Depends(get_risk_limits_repository)
) -> RiskLimitsOut:
    saved = repo.save(request.to_domain())
    return RiskLimitsOut.from_domain(saved)


@router.post("/position-size", response_model=PositionSizeResponseOut)
def calculate_position_size_endpoint(request: PositionSizeRequest) -> PositionSizeResponseOut:
    try:
        symbol_spec = get_symbol(request.symbol)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Unsupported symbol: {request.symbol}") from None

    try:
        result = calculate_position_size(
            account_balance=request.account_balance,
            risk_percent=request.risk_percent,
            entry_price=request.entry_price,
            stop_loss_price=request.stop_loss_price,
            symbol=symbol_spec,
            account_currency=request.account_currency,
            quote_to_account_rate=request.quote_to_account_rate,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    return PositionSizeResponseOut.from_domain(result)
