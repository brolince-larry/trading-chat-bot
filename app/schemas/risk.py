from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.domain.risk.position_sizing import PositionSizeResult

_VALID_CURRENCY_LENGTH = 3


class PositionSizeRequest(BaseModel):
    symbol: str = Field(..., min_length=3, max_length=16)
    account_balance: Decimal = Field(..., gt=0, le=Decimal("100000000"))
    risk_percent: Decimal = Field(..., gt=0, le=Decimal("100"))
    entry_price: Decimal = Field(..., gt=0)
    stop_loss_price: Decimal = Field(..., gt=0)
    account_currency: str = Field(default="USD", min_length=3, max_length=3)
    quote_to_account_rate: Decimal | None = Field(default=None, gt=0)

    @field_validator("symbol")
    @classmethod
    def _uppercase_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("account_currency")
    @classmethod
    def _uppercase_currency(cls, value: str) -> str:
        cleaned = value.strip().upper()
        if len(cleaned) != _VALID_CURRENCY_LENGTH or not cleaned.isalpha():
            raise ValueError("account_currency must be a 3-letter ISO currency code")
        return cleaned


class PositionSizeResponseOut(BaseModel):
    symbol: str
    account_currency: str
    risk_amount: Decimal
    stop_distance_pips: Decimal
    pip_value_per_unit: Decimal
    lots: Decimal
    units: Decimal
    meets_minimum_lot: bool
    warnings: list[str]

    @classmethod
    def from_domain(cls, result: PositionSizeResult) -> "PositionSizeResponseOut":
        return cls(
            symbol=result.symbol,
            account_currency=result.account_currency,
            risk_amount=result.risk_amount,
            stop_distance_pips=result.stop_distance_pips,
            pip_value_per_unit=result.pip_value_per_unit,
            lots=result.lots,
            units=result.units,
            meets_minimum_lot=result.meets_minimum_lot,
            warnings=result.warnings,
        )
