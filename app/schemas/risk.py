from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.domain.risk.exposure import ExposureLevel
from app.domain.risk.position_sizing import PositionSizeResult
from app.domain.risk.validation import RiskLimits

_VALID_CURRENCY_LENGTH = 3


class PositionSizeRequest(BaseModel):
    symbol: str = Field(..., min_length=3, max_length=16)
    account_balance: Decimal = Field(..., gt=0, le=Decimal(100000000))
    risk_percent: Decimal = Field(..., gt=0, le=Decimal(100))
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
    def from_domain(cls, result: PositionSizeResult) -> PositionSizeResponseOut:
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


class RiskLimitsOut(BaseModel):
    max_risk_per_trade_percent: Decimal
    max_daily_loss_percent: Decimal
    max_open_positions: int
    max_spread_pips: Decimal
    max_correlated_exposure: ExposureLevel
    min_risk_reward: Decimal | None
    max_drawdown_percent: Decimal | None

    @classmethod
    def from_domain(cls, limits: RiskLimits) -> RiskLimitsOut:
        return cls(
            max_risk_per_trade_percent=limits.max_risk_per_trade_percent,
            max_daily_loss_percent=limits.max_daily_loss_percent,
            max_open_positions=limits.max_open_positions,
            max_spread_pips=limits.max_spread_pips,
            max_correlated_exposure=limits.max_correlated_exposure,
            min_risk_reward=limits.min_risk_reward,
            max_drawdown_percent=limits.max_drawdown_percent,
        )


class RiskLimitsUpdateRequest(BaseModel):
    max_risk_per_trade_percent: Decimal = Field(..., gt=0, le=Decimal(100))
    max_daily_loss_percent: Decimal = Field(..., gt=0, le=Decimal(100))
    max_open_positions: int = Field(..., gt=0, le=100)
    max_spread_pips: Decimal = Field(..., gt=0, le=Decimal(100))
    max_correlated_exposure: ExposureLevel = ExposureLevel.MEDIUM
    min_risk_reward: Decimal | None = Field(default=None, gt=0)
    max_drawdown_percent: Decimal | None = Field(default=None, gt=0, le=Decimal(100))

    def to_domain(self) -> RiskLimits:
        return RiskLimits(
            max_risk_per_trade_percent=self.max_risk_per_trade_percent,
            max_daily_loss_percent=self.max_daily_loss_percent,
            max_open_positions=self.max_open_positions,
            max_spread_pips=self.max_spread_pips,
            max_correlated_exposure=self.max_correlated_exposure,
            min_risk_reward=self.min_risk_reward,
            max_drawdown_percent=self.max_drawdown_percent,
        )
