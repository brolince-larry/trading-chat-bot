"""Currency exposure aggregation.

Three "separate" trades (long EUR/USD, long GBP/USD, long AUD/USD) can
really be one concentrated short-USD bet. This module makes that visible so
the risk engine — not the LLM — can flag concentrated exposure.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.domain.market.symbols import get_symbol
from app.domain.strategies.base import Direction


class ExposureLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class PositionExposure:
    symbol: str
    direction: Direction


@dataclass(frozen=True, slots=True)
class CurrencyExposure:
    currency: str
    net_position_count: int  # positive = net long, negative = net short
    contributing_symbols: list[str]

    @property
    def level(self) -> ExposureLevel:
        magnitude = abs(self.net_position_count)
        if magnitude >= 3:
            return ExposureLevel.HIGH
        if magnitude == 2:
            return ExposureLevel.MEDIUM
        return ExposureLevel.LOW


def calculate_currency_exposure(positions: list[PositionExposure]) -> list[CurrencyExposure]:
    net_count: dict[str, int] = {}
    contributors: dict[str, list[str]] = {}

    for position in positions:
        if position.direction is Direction.NONE:
            continue
        symbol_spec = get_symbol(position.symbol)
        sign = 1 if position.direction is Direction.LONG else -1

        net_count[symbol_spec.base_currency] = net_count.get(symbol_spec.base_currency, 0) + sign
        net_count[symbol_spec.quote_currency] = net_count.get(symbol_spec.quote_currency, 0) - sign

        contributors.setdefault(symbol_spec.base_currency, []).append(position.symbol)
        contributors.setdefault(symbol_spec.quote_currency, []).append(position.symbol)

    return [
        CurrencyExposure(
            currency=currency,
            net_position_count=count,
            contributing_symbols=sorted(set(contributors.get(currency, []))),
        )
        for currency, count in sorted(net_count.items())
        if count != 0
    ]
