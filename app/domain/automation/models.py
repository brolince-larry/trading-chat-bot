"""Trade-management automation: rules the background loop applies to
already-open positions (moving a stop to breakeven, trailing it behind
price). This is distinct from ``app.domain.bot`` (which controls whether
new setups are scanned for) and from opening/closing trades, which always
requires an explicit user action.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class TradeAutomationSettings:
    breakeven_enabled: bool = False
    breakeven_at_r: Decimal = Decimal("1.0")
    trailing_stop_enabled: bool = False
    trailing_stop_pips: Decimal = Decimal(20)
