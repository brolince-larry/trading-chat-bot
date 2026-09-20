"""Trade-plan risk validation: the rules that decide whether a strategy's
confirmed setup is actually safe to present or act on.

This is deliberately the only place these checks live — a strategy module
never decides for itself whether a trade is "safe," and the LLM never does
either.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.domain.risk.exposure import ExposureLevel

_EXPOSURE_RANK = {ExposureLevel.LOW: 0, ExposureLevel.MEDIUM: 1, ExposureLevel.HIGH: 2}


@dataclass(frozen=True, slots=True)
class RiskLimits:
    max_risk_per_trade_percent: Decimal = Decimal("1.0")
    max_daily_loss_percent: Decimal = Decimal("3.0")
    max_open_positions: int = 5
    max_spread_pips: Decimal = Decimal("3.0")
    max_correlated_exposure: ExposureLevel = ExposureLevel.MEDIUM
    min_risk_reward: Decimal | None = Decimal("1.5")


@dataclass(frozen=True, slots=True)
class RiskCheckContext:
    account_balance: Decimal
    proposed_risk_percent: Decimal
    daily_loss_so_far: Decimal = Decimal("0")
    open_positions_count: int = 0
    current_spread_pips: Decimal | None = None
    risk_reward: float | None = None
    projected_exposure_level: ExposureLevel | None = None


@dataclass(frozen=True, slots=True)
class RiskCheckResult:
    passed: bool
    violations: list[str] = field(default_factory=list)


def validate_trade_risk(context: RiskCheckContext, limits: RiskLimits = RiskLimits()) -> RiskCheckResult:
    violations: list[str] = []

    if context.proposed_risk_percent > limits.max_risk_per_trade_percent:
        violations.append(
            f"Proposed risk {context.proposed_risk_percent}% exceeds the "
            f"per-trade limit of {limits.max_risk_per_trade_percent}%."
        )

    proposed_risk_amount = context.account_balance * (context.proposed_risk_percent / Decimal("100"))
    projected_daily_loss = context.daily_loss_so_far + proposed_risk_amount
    max_daily_loss_amount = context.account_balance * (limits.max_daily_loss_percent / Decimal("100"))
    if projected_daily_loss > max_daily_loss_amount:
        violations.append(
            f"Taking this trade would bring today's realized+at-risk loss to "
            f"{projected_daily_loss}, above the daily limit of {max_daily_loss_amount}."
        )

    if context.open_positions_count >= limits.max_open_positions:
        violations.append(
            f"Open position count ({context.open_positions_count}) is already at or "
            f"above the maximum of {limits.max_open_positions}."
        )

    if context.current_spread_pips is not None and context.current_spread_pips > limits.max_spread_pips:
        violations.append(
            f"Current spread ({context.current_spread_pips} pips) exceeds the maximum "
            f"allowed spread of {limits.max_spread_pips} pips."
        )

    if (
        limits.min_risk_reward is not None
        and context.risk_reward is not None
        and Decimal(str(context.risk_reward)) < limits.min_risk_reward
    ):
        violations.append(
            f"Risk/reward ({context.risk_reward}) is below the minimum threshold of "
            f"{limits.min_risk_reward}."
        )

    if (
        context.projected_exposure_level is not None
        and _EXPOSURE_RANK[context.projected_exposure_level] > _EXPOSURE_RANK[limits.max_correlated_exposure]
    ):
        violations.append(
            f"Taking this trade would push correlated currency exposure to "
            f"{context.projected_exposure_level.value}, above the allowed maximum of "
            f"{limits.max_correlated_exposure.value}."
        )

    return RiskCheckResult(passed=not violations, violations=violations)
