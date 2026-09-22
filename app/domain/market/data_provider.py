"""Port (interface) for market data, owned by the domain layer per the
dependency-inversion rule: domain code depends on this abstraction, and
concrete adapters (simulated, OANDA, MT5, ...) live in the infrastructure
layer and implement it.
"""

from __future__ import annotations

from typing import Protocol

from app.domain.market.models import Candle, Price, Timeframe


class MarketDataProvider(Protocol):
    def get_candles(self, symbol: str, timeframe: Timeframe, count: int) -> list[Candle]:
        """Return up to ``count`` most recent closed candles, oldest first."""
        ...

    def get_price(self, symbol: str) -> Price:
        """Return the current bid/ask price for ``symbol``."""
        ...
