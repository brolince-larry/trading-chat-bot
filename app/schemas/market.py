from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.domain.market.models import Candle, Price, SymbolSpec


class SymbolOut(BaseModel):
    name: str
    base_currency: str
    quote_currency: str
    pip_size: Decimal
    contract_size: Decimal
    min_lot: Decimal
    max_lot: Decimal

    @classmethod
    def from_domain(cls, spec: SymbolSpec) -> "SymbolOut":
        return cls(
            name=spec.name,
            base_currency=spec.base_currency,
            quote_currency=spec.quote_currency,
            pip_size=spec.pip_size,
            contract_size=spec.contract_size,
            min_lot=spec.min_lot,
            max_lot=spec.max_lot,
        )


class CandleOut(BaseModel):
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    @classmethod
    def from_domain(cls, candle: Candle) -> "CandleOut":
        return cls(
            timestamp=candle.timestamp,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=candle.volume,
        )


class PriceOut(BaseModel):
    symbol: str
    bid: Decimal
    ask: Decimal
    spread_pips: Decimal
    timestamp: datetime

    @classmethod
    def from_domain(cls, price: Price, pip_size: Decimal) -> "PriceOut":
        return cls(
            symbol=price.symbol,
            bid=price.bid,
            ask=price.ask,
            spread_pips=price.spread / pip_size,
            timestamp=price.timestamp,
        )
