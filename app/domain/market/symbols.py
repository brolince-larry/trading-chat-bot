"""Static registry of supported instruments.

Kept small and explicit per the "start with 8-12 pairs" guidance rather than
trying to support every possible instrument from day one.
"""

from __future__ import annotations

from decimal import Decimal

from app.domain.market.models import SymbolSpec

_MAJOR_PIP = Decimal("0.0001")
_JPY_PIP = Decimal("0.01")

SUPPORTED_SYMBOLS: dict[str, SymbolSpec] = {
    spec.name: spec
    for spec in (
        SymbolSpec("EUR_USD", "EUR", "USD", _MAJOR_PIP),
        SymbolSpec("GBP_USD", "GBP", "USD", _MAJOR_PIP),
        SymbolSpec("USD_JPY", "USD", "JPY", _JPY_PIP),
        SymbolSpec("USD_CHF", "USD", "CHF", _MAJOR_PIP),
        SymbolSpec("AUD_USD", "AUD", "USD", _MAJOR_PIP),
        SymbolSpec("USD_CAD", "USD", "CAD", _MAJOR_PIP),
        SymbolSpec("NZD_USD", "NZD", "USD", _MAJOR_PIP),
        SymbolSpec("EUR_GBP", "EUR", "GBP", _MAJOR_PIP),
        SymbolSpec("EUR_JPY", "EUR", "JPY", _JPY_PIP),
        SymbolSpec("GBP_JPY", "GBP", "JPY", _JPY_PIP),
        SymbolSpec("AUD_JPY", "AUD", "JPY", _JPY_PIP),
    )
}


def get_symbol(name: str) -> SymbolSpec:
    try:
        return SUPPORTED_SYMBOLS[name.upper()]
    except KeyError as exc:
        raise ValueError(f"Unsupported symbol: {name}") from exc


def list_symbols() -> list[SymbolSpec]:
    return list(SUPPORTED_SYMBOLS.values())
