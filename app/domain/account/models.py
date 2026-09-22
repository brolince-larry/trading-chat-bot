"""Account-level summary: balance, P&L, and equity curve.

Everything here is derived from real paper-trading history (closed/open
positions) plus a configurable starting balance — never a fabricated
number. There is no live brokerage balance to report; "balance" means
starting balance + realized P&L (+ unrealized P&L for the open-position
view), exactly as a paper-trading ledger would compute it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class AccountSettings:
    starting_balance: Decimal = Decimal(10000)


@dataclass(frozen=True, slots=True)
class EquityPoint:
    timestamp: datetime
    balance: Decimal


@dataclass(frozen=True, slots=True)
class PairPerformance:
    symbol: str
    realized_pnl: Decimal
    trade_count: int


@dataclass(frozen=True, slots=True)
class AccountSummary:
    starting_balance: Decimal
    balance: Decimal
    total_realized_pnl: Decimal
    total_unrealized_pnl: Decimal
    total_pnl_percent: float
    active_trades: int
    win_rate: float | None
    equity_curve: list[EquityPoint] = field(default_factory=list)
    top_pairs: list[PairPerformance] = field(default_factory=list)
