from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.domain.backtest.models import (
    BacktestResult,
    BacktestTrade,
    EquityPoint,
    ExitReason,
)
from app.domain.market.models import Timeframe
from app.domain.market.symbols import SUPPORTED_SYMBOLS
from app.domain.strategies import ALL_STRATEGIES
from app.domain.strategies.base import Direction

_VALID_STRATEGIES = {s.name for s in ALL_STRATEGIES}
MAX_LOOKBACK_CANDLES = 3000


class BacktestRequest(BaseModel):
    symbol: str = Field(..., min_length=3, max_length=16)
    strategy: str = Field(..., min_length=1, max_length=64)
    higher_timeframe: Timeframe = Timeframe.H4
    entry_timeframe: Timeframe = Timeframe.H1
    lookback_candles: int = Field(default=500, ge=70, le=MAX_LOOKBACK_CANDLES)
    starting_balance: Decimal = Field(default=Decimal(10000), gt=0, le=Decimal(100000000))
    risk_percent: Decimal = Field(default=Decimal("1.0"), gt=0, le=Decimal(100))
    account_currency: str = Field(default="USD", min_length=3, max_length=3)
    quote_to_account_rate: Decimal | None = Field(default=None, gt=0)

    @field_validator("symbol")
    @classmethod
    def _validate_symbol(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in SUPPORTED_SYMBOLS:
            raise ValueError(f"Unsupported symbol: {normalized}")
        return normalized

    @field_validator("strategy")
    @classmethod
    def _validate_strategy(cls, value: str) -> str:
        if value not in _VALID_STRATEGIES:
            raise ValueError(f"Unknown strategy: {value}")
        return value

    @field_validator("account_currency")
    @classmethod
    def _uppercase_currency(cls, value: str) -> str:
        return value.strip().upper()


class BacktestTradeOut(BaseModel):
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

    @classmethod
    def from_domain(cls, trade: BacktestTrade) -> BacktestTradeOut:
        return cls(
            direction=trade.direction,
            entry_price=trade.entry_price,
            stop_loss=trade.stop_loss,
            take_profit=trade.take_profit,
            exit_price=trade.exit_price,
            exit_reason=trade.exit_reason,
            entered_at=trade.entered_at,
            exited_at=trade.exited_at,
            bars_held=trade.bars_held,
            units=trade.units,
            pnl=trade.pnl,
            r_multiple=trade.r_multiple,
        )


class BacktestEquityPointOut(BaseModel):
    timestamp: datetime
    balance: Decimal

    @classmethod
    def from_domain(cls, point: EquityPoint) -> BacktestEquityPointOut:
        return cls(timestamp=point.timestamp, balance=point.balance)


class BacktestResultOut(BaseModel):
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
    trades: list[BacktestTradeOut]
    equity_curve: list[BacktestEquityPointOut]

    @classmethod
    def from_domain(cls, result: BacktestResult) -> BacktestResultOut:
        return cls(
            symbol=result.symbol,
            strategy=result.strategy,
            higher_timeframe=result.higher_timeframe,
            entry_timeframe=result.entry_timeframe,
            starting_balance=result.starting_balance,
            ending_balance=result.ending_balance,
            total_return_percent=result.total_return_percent,
            total_trades=result.total_trades,
            win_count=result.win_count,
            loss_count=result.loss_count,
            win_rate=result.win_rate,
            profit_factor=result.profit_factor,
            expectancy_r=result.expectancy_r,
            average_r_multiple=result.average_r_multiple,
            max_drawdown_percent=result.max_drawdown_percent,
            largest_win=result.largest_win,
            largest_loss=result.largest_loss,
            trades=[BacktestTradeOut.from_domain(t) for t in result.trades],
            equity_curve=[BacktestEquityPointOut.from_domain(p) for p in result.equity_curve],
        )
