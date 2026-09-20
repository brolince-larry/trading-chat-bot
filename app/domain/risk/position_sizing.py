"""Position sizing: given account risk tolerance and a stop distance, how
many units/lots correspond to that risk?

All money math is done in ``Decimal`` to avoid floating-point drift on
account balances and position sizes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_DOWN, Decimal

from app.domain.market.models import SymbolSpec
from app.domain.risk.decimal_utils import to_plain
from app.domain.risk.pip_value import pip_value_per_unit


@dataclass(frozen=True, slots=True)
class PositionSizeResult:
    symbol: str
    account_currency: str
    risk_amount: Decimal
    stop_distance_pips: Decimal
    pip_value_per_unit: Decimal
    raw_units: Decimal
    lots: Decimal
    units: Decimal
    meets_minimum_lot: bool
    warnings: list[str] = field(default_factory=list)


def calculate_position_size(
    *,
    account_balance: Decimal,
    risk_percent: Decimal,
    entry_price: Decimal,
    stop_loss_price: Decimal,
    symbol: SymbolSpec,
    account_currency: str,
    quote_to_account_rate: Decimal | None = None,
) -> PositionSizeResult:
    if account_balance <= 0:
        raise ValueError("account_balance must be positive")
    if not (Decimal(0) < risk_percent <= Decimal(100)):
        raise ValueError("risk_percent must be between 0 and 100")

    stop_distance = abs(entry_price - stop_loss_price)
    if stop_distance <= 0:
        raise ValueError("entry_price and stop_loss_price cannot be equal")

    risk_amount = to_plain(account_balance * (risk_percent / Decimal(100)))
    stop_distance_pips = to_plain(stop_distance / symbol.pip_size)

    pip_value = pip_value_per_unit(symbol, account_currency, quote_to_account_rate)
    loss_per_unit = stop_distance_pips * pip_value
    if loss_per_unit <= 0:
        raise ValueError("Computed loss per unit is not positive; check inputs")

    raw_units = to_plain(risk_amount / loss_per_unit)
    raw_lots = raw_units / symbol.contract_size

    lot_steps = (raw_lots / symbol.lot_step).to_integral_value(rounding=ROUND_DOWN)
    lots = lot_steps * symbol.lot_step

    warnings: list[str] = []
    meets_minimum_lot = lots >= symbol.min_lot

    if not meets_minimum_lot:
        warnings.append(
            f"Calculated size ({lots} lots) is below the broker minimum of "
            f"{symbol.min_lot} lots for the requested risk. Increase risk percent, "
            "account size, or accept the broker minimum with higher effective risk."
        )
        lots = Decimal(0)
    elif lots > symbol.max_lot:
        warnings.append(
            f"Calculated size ({lots} lots) exceeds the broker maximum of "
            f"{symbol.max_lot} lots; capped at the maximum."
        )
        lots = symbol.max_lot

    units = to_plain(lots * symbol.contract_size)

    return PositionSizeResult(
        symbol=symbol.name,
        account_currency=account_currency,
        risk_amount=risk_amount,
        stop_distance_pips=stop_distance_pips,
        pip_value_per_unit=pip_value,
        raw_units=raw_units,
        lots=lots,
        units=units,
        meets_minimum_lot=meets_minimum_lot,
        warnings=warnings,
    )
