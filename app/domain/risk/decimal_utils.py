"""Shared Decimal formatting helper for the risk engine.

Decimal arithmetic can legitimately produce a result expressed with a
positive exponent — e.g. ``Decimal('0.0050') / Decimal('0.0001')`` is
``Decimal('5E+1')``, not ``Decimal('50')`` — because that's a valid,
exact representation. But ``Decimal.__str__`` renders that as scientific
notation, which is what every JSON/API consumer of this module sees since
Pydantic serializes Decimal via ``str()``. ``to_plain`` re-expresses any
Decimal in fixed-point form without changing its value.
"""

from __future__ import annotations

from decimal import Decimal


def to_plain(value: Decimal) -> Decimal:
    return Decimal(format(value, "f"))
