from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.market.symbols import get_symbol
from app.domain.risk.exposure import PositionExposure, calculate_currency_exposure
from app.domain.risk.pip_value import pip_value_per_unit
from app.domain.risk.position_sizing import calculate_position_size
from app.domain.risk.validation import RiskCheckContext, RiskLimits, validate_trade_risk
from app.domain.strategies.base import Direction

# --- pip value --------------------------------------------------------------


def test_pip_value_when_quote_equals_account_currency():
    eur_usd = get_symbol("EUR_USD")
    value = pip_value_per_unit(eur_usd, account_currency="USD")
    assert value == eur_usd.pip_size


def test_pip_value_requires_conversion_rate_when_quote_differs_from_account():
    eur_usd = get_symbol("EUR_USD")  # quote=USD, account=EUR
    with pytest.raises(ValueError):
        pip_value_per_unit(eur_usd, account_currency="EUR")


def test_pip_value_uses_provided_conversion_rate():
    eur_usd = get_symbol("EUR_USD")
    # If 1 USD = 0.90 EUR, a 1-pip move (0.0001 USD) is worth 0.00009 EUR.
    value = pip_value_per_unit(eur_usd, account_currency="EUR", quote_to_account_rate=Decimal("0.90"))
    assert value == Decimal("0.0001") * Decimal("0.90")


def test_pip_value_never_serializes_in_scientific_notation():
    eur_usd = get_symbol("EUR_USD")
    value = pip_value_per_unit(eur_usd, account_currency="EUR", quote_to_account_rate=Decimal("500"))
    assert "E" not in str(value)


# --- position sizing ---------------------------------------------------------


def test_position_size_basic_usd_account_eur_usd():
    eur_usd = get_symbol("EUR_USD")
    result = calculate_position_size(
        account_balance=Decimal("10000"),
        risk_percent=Decimal("1"),
        entry_price=Decimal("1.1000"),
        stop_loss_price=Decimal("1.0950"),
        symbol=eur_usd,
        account_currency="USD",
    )
    assert result.risk_amount == Decimal("100.00")
    assert result.stop_distance_pips == Decimal("50")
    assert result.lots == Decimal("0.2")
    assert result.meets_minimum_lot is True
    assert result.warnings == []


def test_position_size_below_broker_minimum_returns_zero_with_warning():
    eur_usd = get_symbol("EUR_USD")
    result = calculate_position_size(
        account_balance=Decimal("100"),
        risk_percent=Decimal("0.1"),
        entry_price=Decimal("1.1000"),
        stop_loss_price=Decimal("1.0950"),
        symbol=eur_usd,
        account_currency="USD",
    )
    assert result.lots == Decimal("0")
    assert result.meets_minimum_lot is False
    assert result.warnings


def test_position_size_rejects_equal_entry_and_stop():
    eur_usd = get_symbol("EUR_USD")
    with pytest.raises(ValueError):
        calculate_position_size(
            account_balance=Decimal("10000"),
            risk_percent=Decimal("1"),
            entry_price=Decimal("1.1000"),
            stop_loss_price=Decimal("1.1000"),
            symbol=eur_usd,
            account_currency="USD",
        )


def test_position_size_never_serializes_pip_distance_in_scientific_notation():
    # Decimal('1.1') - Decimal('1.095') divided by pip_size (0.0001) is
    # exactly Decimal('5E+1') before normalization — str()'d straight into
    # an API response that would read "5E+1 pips" instead of "50 pips".
    eur_usd = get_symbol("EUR_USD")
    result = calculate_position_size(
        account_balance=Decimal("10000"),
        risk_percent=Decimal("1"),
        entry_price=Decimal("1.1"),
        stop_loss_price=Decimal("1.095"),
        symbol=eur_usd,
        account_currency="USD",
    )
    assert str(result.stop_distance_pips) == "50"
    assert "E" not in str(result.risk_amount)
    assert "E" not in str(result.raw_units)
    assert "E" not in str(result.units)


def test_position_size_rejects_invalid_risk_percent():
    eur_usd = get_symbol("EUR_USD")
    with pytest.raises(ValueError):
        calculate_position_size(
            account_balance=Decimal("10000"),
            risk_percent=Decimal("0"),
            entry_price=Decimal("1.1000"),
            stop_loss_price=Decimal("1.0950"),
            symbol=eur_usd,
            account_currency="USD",
        )


# --- currency exposure -------------------------------------------------------


def test_currency_exposure_aggregates_correlated_usd_shorts():
    positions = [
        PositionExposure("EUR_USD", Direction.LONG),
        PositionExposure("GBP_USD", Direction.LONG),
        PositionExposure("AUD_USD", Direction.LONG),
    ]
    exposures = calculate_currency_exposure(positions)
    usd_exposure = next(e for e in exposures if e.currency == "USD")
    assert usd_exposure.net_position_count == -3
    assert usd_exposure.level.value == "high"

    eur_exposure = next(e for e in exposures if e.currency == "EUR")
    assert eur_exposure.net_position_count == 1
    assert eur_exposure.level.value == "low"


def test_currency_exposure_ignores_flat_positions():
    positions = [
        PositionExposure("EUR_USD", Direction.LONG),
        PositionExposure("EUR_USD", Direction.SHORT),
    ]
    exposures = calculate_currency_exposure(positions)
    assert exposures == []


# --- risk validation ----------------------------------------------------------


def test_validate_trade_risk_passes_within_all_limits():
    context = RiskCheckContext(
        account_balance=Decimal("10000"),
        proposed_risk_percent=Decimal("1"),
        risk_reward=2.0,
    )
    result = validate_trade_risk(context)
    assert result.passed is True
    assert result.violations == []


def test_validate_trade_risk_flags_excessive_per_trade_risk():
    context = RiskCheckContext(account_balance=Decimal("10000"), proposed_risk_percent=Decimal("5"))
    result = validate_trade_risk(context, RiskLimits(max_risk_per_trade_percent=Decimal("1")))
    assert result.passed is False
    assert any("per-trade limit" in v for v in result.violations)


def test_validate_trade_risk_flags_daily_loss_limit():
    context = RiskCheckContext(
        account_balance=Decimal("10000"),
        proposed_risk_percent=Decimal("1"),
        daily_loss_so_far=Decimal("290"),
    )
    result = validate_trade_risk(context, RiskLimits(max_daily_loss_percent=Decimal("3")))
    assert result.passed is False
    assert any("daily" in v.lower() for v in result.violations)


def test_validate_trade_risk_flags_too_many_open_positions():
    context = RiskCheckContext(
        account_balance=Decimal("10000"), proposed_risk_percent=Decimal("1"), open_positions_count=5
    )
    result = validate_trade_risk(context, RiskLimits(max_open_positions=5))
    assert result.passed is False


def test_validate_trade_risk_flags_excessive_spread():
    context = RiskCheckContext(
        account_balance=Decimal("10000"),
        proposed_risk_percent=Decimal("1"),
        current_spread_pips=Decimal("5"),
    )
    result = validate_trade_risk(context, RiskLimits(max_spread_pips=Decimal("3")))
    assert result.passed is False


def test_validate_trade_risk_flags_low_risk_reward():
    context = RiskCheckContext(account_balance=Decimal("10000"), proposed_risk_percent=Decimal("1"), risk_reward=1.0)
    result = validate_trade_risk(context, RiskLimits(min_risk_reward=Decimal("1.5")))
    assert result.passed is False


def test_validate_trade_risk_can_fail_on_multiple_violations_simultaneously():
    context = RiskCheckContext(
        account_balance=Decimal("10000"),
        proposed_risk_percent=Decimal("10"),
        open_positions_count=10,
        current_spread_pips=Decimal("10"),
        risk_reward=0.5,
    )
    result = validate_trade_risk(context)
    assert result.passed is False
    assert len(result.violations) >= 3
