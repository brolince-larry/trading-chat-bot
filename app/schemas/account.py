from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.domain.account.models import (
    AccountSettings,
    AccountSummary,
    EquityPoint,
    PairPerformance,
)


class AccountSettingsOut(BaseModel):
    starting_balance: Decimal

    @classmethod
    def from_domain(cls, settings: AccountSettings) -> AccountSettingsOut:
        return cls(starting_balance=settings.starting_balance)


class AccountSettingsUpdateRequest(BaseModel):
    starting_balance: Decimal = Field(..., gt=0, le=Decimal(100000000))

    def to_domain(self) -> AccountSettings:
        return AccountSettings(starting_balance=self.starting_balance)


class EquityPointOut(BaseModel):
    timestamp: datetime
    balance: Decimal

    @classmethod
    def from_domain(cls, point: EquityPoint) -> EquityPointOut:
        return cls(timestamp=point.timestamp, balance=point.balance)


class PairPerformanceOut(BaseModel):
    symbol: str
    realized_pnl: Decimal
    trade_count: int

    @classmethod
    def from_domain(cls, perf: PairPerformance) -> PairPerformanceOut:
        return cls(symbol=perf.symbol, realized_pnl=perf.realized_pnl, trade_count=perf.trade_count)


class AccountSummaryOut(BaseModel):
    starting_balance: Decimal
    balance: Decimal
    total_realized_pnl: Decimal
    total_unrealized_pnl: Decimal
    total_pnl_percent: float
    active_trades: int
    win_rate: float | None
    equity_curve: list[EquityPointOut]
    top_pairs: list[PairPerformanceOut]

    @classmethod
    def from_domain(cls, summary: AccountSummary) -> AccountSummaryOut:
        return cls(
            starting_balance=summary.starting_balance,
            balance=summary.balance,
            total_realized_pnl=summary.total_realized_pnl,
            total_unrealized_pnl=summary.total_unrealized_pnl,
            total_pnl_percent=summary.total_pnl_percent,
            active_trades=summary.active_trades,
            win_rate=summary.win_rate,
            equity_curve=[EquityPointOut.from_domain(p) for p in summary.equity_curve],
            top_pairs=[PairPerformanceOut.from_domain(p) for p in summary.top_pairs],
        )
