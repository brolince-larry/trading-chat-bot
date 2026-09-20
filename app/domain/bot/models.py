"""Bot configuration: which pairs/strategies the background scanner watches,
and whether it is running at all.

This is deliberately scan-only automation — enabling the bot makes the
background loop actively re-scan the configured pairs/strategies and keep
the dashboard live. It never opens or closes a trade on its own; every
position still requires an explicit user action (see
``app.domain.trading.paper_trading_service``). That boundary is a product
decision, not a technical limitation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.market.symbols import list_symbols
from app.domain.strategies import ALL_STRATEGIES


def _default_symbols() -> list[str]:
    return [spec.name for spec in list_symbols()]


def _default_strategies() -> list[str]:
    return [s.name for s in ALL_STRATEGIES]


@dataclass(frozen=True, slots=True)
class BotSettings:
    enabled: bool = True
    active_symbols: list[str] = field(default_factory=_default_symbols)
    active_strategies: list[str] = field(default_factory=_default_strategies)
