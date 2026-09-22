"""Backtest result value objects.

Every number here comes from actually walking historical candles bar by
bar and applying the same ``Strategy.analyze()`` and
``calculate_position_size()`` the live scanner and paper-trading service
use — never a separate, hand-tuned "backtest version" of the rules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum

from app.domain.strategies.base import Direction


class ExitReason(str, Enum):
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    END_OF_DATA = "end_of_data"


@dataclass(frozen=True, slots=True)
class BacktestTrade:
    direction: Direction
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal | None
    exit_price: Decimal
    exit_reason: ExitReason
    entered_at: datetime
    exited_at: datetime
    bars_held: int
    units: Decimal
    pnl: Decimal
    r_multiple: Decimal


@dataclass(frozen=True, slots=True)
class EquityPoint:
    timestamp: datetime
    balance: Decimal


@dataclass(frozen=True, slots=True)
class BacktestResult:
    symbol: str
    strategy: str
    higher_timeframe: str
    entry_timeframe: str
    starting_balance: Decimal
    ending_balance: Decimal
    total_return_percent: float
    total_trades: int
    win_count: int
    loss_count: int
    win_rate: float | None
    profit_factor: float | None
    expectancy_r: float | None
    average_r_multiple: float | None
    max_drawdown_percent: float
    largest_win: Decimal | None
    largest_loss: Decimal | None
    trades: list[BacktestTrade] = field(default_factory=list)
    equity_curve: list[EquityPoint] = field(default_factory=list)
