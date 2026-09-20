from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.domain.strategies.base import Direction
from app.domain.trading.models import PaperPosition, PerformanceStats, PositionStatus


class OpenPositionRequest(BaseModel):
    symbol: str = Field(..., min_length=3, max_length=16)
    strategy: str = Field(..., min_length=1, max_length=64)
    direction: Direction
    entry_price: Decimal = Field(..., gt=0)
    stop_loss: Decimal = Field(..., gt=0)
    take_profit: Decimal | None = Field(default=None, gt=0)
    lots: Decimal = Field(..., gt=0, le=Decimal(1000))
    units: Decimal = Field(..., gt=0)
    account_currency: str = Field(default="USD", min_length=3, max_length=3)
    pip_value_per_unit: Decimal = Field(..., gt=0)

    @field_validator("symbol")
    @classmethod
    def _uppercase_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("account_currency")
    @classmethod
    def _uppercase_currency(cls, value: str) -> str:
        return value.strip().upper()


class ClosePositionRequest(BaseModel):
    close_price: Decimal | None = Field(default=None, gt=0)


class PositionOut(BaseModel):
    id: str
    symbol: str
    strategy: str
    direction: Direction
    status: PositionStatus
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal | None
    lots: Decimal
    units: Decimal
    account_currency: str
    opened_at: datetime
    closed_at: datetime | None
    close_price: Decimal | None
    realized_pnl: Decimal | None
    risk_multiple: Decimal | None
    unrealized_pnl: Decimal | None = None

    @classmethod
    def from_domain(cls, position: PaperPosition, unrealized_pnl: Decimal | None = None) -> PositionOut:
        return cls(
            id=position.id,
            symbol=position.symbol,
            strategy=position.strategy,
            direction=position.direction,
            status=position.status,
            entry_price=position.entry_price,
            stop_loss=position.stop_loss,
            take_profit=position.take_profit,
            lots=position.lots,
            units=position.units,
            account_currency=position.account_currency,
            opened_at=position.opened_at,
            closed_at=position.closed_at,
            close_price=position.close_price,
            realized_pnl=position.realized_pnl,
            risk_multiple=position.risk_multiple,
            unrealized_pnl=unrealized_pnl,
        )


class PerformanceStatsOut(BaseModel):
    closed_count: int
    win_count: int
    loss_count: int
    win_rate: float | None
    total_realized_pnl: Decimal
    average_r_multiple: float | None
    expectancy_r: float | None
    profit_factor: float | None

    @classmethod
    def from_domain(cls, stats: PerformanceStats) -> PerformanceStatsOut:
        return cls(
            closed_count=stats.closed_count,
            win_count=stats.win_count,
            loss_count=stats.loss_count,
            win_rate=stats.win_rate,
            total_realized_pnl=stats.total_realized_pnl,
            average_r_multiple=stats.average_r_multiple,
            expectancy_r=stats.expectancy_r,
            profit_factor=stats.profit_factor,
        )
