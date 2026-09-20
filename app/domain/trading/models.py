"""Paper-trading domain model.

A `PaperPosition` is a simulated trade opened from a scanner candidate. It
lets the system demonstrate "what would have happened" without touching a
real broker — the necessary step before demo/live execution per the
project's phased rollout.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum

from app.domain.strategies.base import Direction


class PositionStatus(str, Enum):
    OPEN = "open"
    CLOSED_TAKE_PROFIT = "closed_take_profit"
    CLOSED_STOP_LOSS = "closed_stop_loss"
    CLOSED_MANUAL = "closed_manual"

    @property
    def is_open(self) -> bool:
        return self is PositionStatus.OPEN


@dataclass(frozen=True, slots=True)
class PaperPosition:
    id: str
    symbol: str
    strategy: str
    direction: Direction
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal | None
    lots: Decimal
    units: Decimal
    account_currency: str
    pip_value_per_unit: Decimal
    status: PositionStatus
    opened_at: datetime
    closed_at: datetime | None = None
    close_price: Decimal | None = None
    realized_pnl: Decimal | None = None
    risk_multiple: Decimal | None = None


@dataclass(frozen=True, slots=True)
class PerformanceStats:
    closed_count: int
    win_count: int
    loss_count: int
    win_rate: float | None
    total_realized_pnl: Decimal
    average_r_multiple: float | None
    expectancy_r: float | None
    profit_factor: float | None
