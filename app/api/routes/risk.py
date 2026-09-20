from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.domain.market.symbols import get_symbol
from app.domain.risk.position_sizing import calculate_position_size
from app.schemas.risk import PositionSizeRequest, PositionSizeResponseOut

router = APIRouter(prefix="/risk", tags=["risk"])


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
