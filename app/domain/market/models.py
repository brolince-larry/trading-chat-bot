"""Core market data value objects.

These are plain, immutable domain objects with no framework dependencies.
Persistence (SQLAlchemy) and transport (Pydantic) models are separate and
map onto these where needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum


class Timeframe(str, Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"

    @property
    def minutes(self) -> int:
        return {
            Timeframe.M1: 1,
            Timeframe.M5: 5,
            Timeframe.M15: 15,
            Timeframe.M30: 30,
            Timeframe.H1: 60,
            Timeframe.H4: 240,
            Timeframe.D1: 1440,
        }[self]


@dataclass(frozen=True, slots=True)
class SymbolSpec:
    """Instrument specification required for correct pip/lot math.

    ``name`` follows the broker-agnostic BASE_QUOTE convention (e.g. EUR_USD).
    """

    name: str
    base_currency: str
    quote_currency: str
    pip_size: Decimal
    contract_size: Decimal = Decimal("100000")
    min_lot: Decimal = Decimal("0.01")
    max_lot: Decimal = Decimal("100")
    lot_step: Decimal = Decimal("0.01")

    @property
    def is_jpy_quote(self) -> bool:
        return self.quote_currency == "JPY"


@dataclass(frozen=True, slots=True)
class Candle:
    symbol: str
    timeframe: Timeframe
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if self.high < self.low:
            raise ValueError(
                f"Invalid candle for {self.symbol}: high {self.high} < low {self.low}"
            )
        if not (self.low <= self.open <= self.high):
            raise ValueError(
                f"Invalid candle for {self.symbol}: open {self.open} outside [{self.low}, {self.high}]"
            )
        if not (self.low <= self.close <= self.high):
            raise ValueError(
                f"Invalid candle for {self.symbol}: close {self.close} outside [{self.low}, {self.high}]"
            )

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        return self.close < self.open

    @property
    def body(self) -> Decimal:
        return abs(self.close - self.open)

    @property
    def range(self) -> Decimal:
        return self.high - self.low


@dataclass(frozen=True, slots=True)
class Price:
    symbol: str
    bid: Decimal
    ask: Decimal
    timestamp: datetime

    @property
    def mid(self) -> Decimal:
        return (self.bid + self.ask) / 2

    @property
    def spread(self) -> Decimal:
        return self.ask - self.bid
