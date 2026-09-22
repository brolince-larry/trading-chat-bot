"""Setup quality scoring.

Produces a 0-100 "setup quality score" from weighted, independently
explainable factors. This is explicitly NOT a probability of winning — it is
a measure of how many objective conditions the setup satisfies, so it must
never be presented to a user as a win-rate estimate.
"""

from __future__ import annotations

from decimal import Decimal

from app.domain.analysis.structure import MarketRegime, TrendDirection
from app.domain.analysis.timeframe_analysis import TimeframeAnalysis
from app.domain.strategies.base import Direction, SetupStatus, TradeSetup

MAX_ACCEPTABLE_SPREAD_PIPS = Decimal("3.0")


def score_setup(
    setup: TradeSetup,
    higher_tf: TimeframeAnalysis,
    entry_tf: TimeframeAnalysis,
    spread_pips: Decimal | None = None,
    max_acceptable_spread_pips: Decimal = MAX_ACCEPTABLE_SPREAD_PIPS,
) -> int:
    if not setup.is_actionable or setup.direction is Direction.NONE:
        return 0

    score = 0
    score += _trend_alignment_points(setup, higher_tf)
    score += _structure_points(entry_tf)
    score += _entry_confirmation_points(setup)
    score += _support_resistance_points(entry_tf)
    score += _volatility_points(entry_tf)
    score += _risk_reward_points(setup)
    score += _spread_points(spread_pips, max_acceptable_spread_pips)
    score += _session_points()

    return max(0, min(100, score))


def _trend_alignment_points(setup: TradeSetup, higher_tf: TimeframeAnalysis) -> int:
    bullish = setup.direction is Direction.LONG and higher_tf.trend is TrendDirection.BULLISH
    bearish = setup.direction is Direction.SHORT and higher_tf.trend is TrendDirection.BEARISH
    if bullish or bearish:
        return 20
    if higher_tf.trend is TrendDirection.NEUTRAL:
        return 8
    return 0


def _structure_points(entry_tf: TimeframeAnalysis) -> int:
    swing_count = len(entry_tf.swings)
    regime_ok = entry_tf.regime is not MarketRegime.TRANSITIONING
    if swing_count >= 4 and regime_ok:
        return 20
    if swing_count >= 2:
        return 10
    return 0


def _entry_confirmation_points(setup: TradeSetup) -> int:
    return 20 if setup.status is SetupStatus.CONFIRMED else 8


def _support_resistance_points(entry_tf: TimeframeAnalysis) -> int:
    if entry_tf.support_levels and entry_tf.resistance_levels:
        return 10
    if entry_tf.support_levels or entry_tf.resistance_levels:
        return 5
    return 0


def _volatility_points(entry_tf: TimeframeAnalysis) -> int:
    if entry_tf.atr_14 is None or entry_tf.average_atr_14 is None or entry_tf.average_atr_14 == 0:
        return 3
    ratio = entry_tf.atr_14 / entry_tf.average_atr_14
    if 0.6 <= ratio <= 1.6:
        return 10
    if 0.4 <= ratio <= 2.2:
        return 5
    return 0


def _risk_reward_points(setup: TradeSetup) -> int:
    if setup.risk_reward is None:
        return 0
    if setup.risk_reward >= 2.5:
        return 10
    if setup.risk_reward >= 2.0:
        return 8
    if setup.risk_reward >= 1.5:
        return 6
    if setup.risk_reward >= 1.0:
        return 3
    return 0


def _spread_points(spread_pips: Decimal | None, max_acceptable: Decimal) -> int:
    if spread_pips is None:
        return 3
    if spread_pips <= max_acceptable / 2:
        return 5
    if spread_pips <= max_acceptable:
        return 3
    return 0


def _session_points() -> int:
    # No live economic-calendar / session-overlap feed is wired up yet (see README
    # roadmap); a neutral score keeps this factor from silently biasing results
    # until that data source exists.
    return 3
