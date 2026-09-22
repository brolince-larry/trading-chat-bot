"""Pip-value math done correctly, instead of hardcoding "1 pip = $10".

The pip value of one unit of the base currency, expressed in the account
currency, is always: ``pip_size * (value of 1 unit of quote currency in
account currency)``. That single formula covers every case — quote currency
equal to the account currency, base currency equal to the account currency,
or neither — as long as the correct quote->account conversion rate is
supplied (it collapses to ``1`` when quote currency == account currency).
"""

from __future__ import annotations

from decimal import Decimal

from app.domain.market.models import SymbolSpec
from app.domain.risk.decimal_utils import to_plain


def pip_value_per_unit(
    symbol: SymbolSpec,
    account_currency: str,
    quote_to_account_rate: Decimal | None = None,
) -> Decimal:
    """Value, in the account currency, of a 1-pip move on 1 unit of ``symbol``.

    :param quote_to_account_rate: how many units of ``account_currency`` one
        unit of the pair's quote currency is worth. Required unless the
        quote currency already equals the account currency.
    """
    if symbol.quote_currency == account_currency:
        return symbol.pip_size

    if quote_to_account_rate is None or quote_to_account_rate <= 0:
        raise ValueError(
            f"A positive {symbol.quote_currency}->{account_currency} conversion rate is "
            f"required to price {symbol.name} in {account_currency}."
        )

    return to_plain(symbol.pip_size * quote_to_account_rate)
