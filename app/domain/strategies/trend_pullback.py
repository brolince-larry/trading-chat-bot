"""Trend continuation / pullback strategy.

Trades in the direction of an established higher-timeframe trend after price
retraces into a defined pullback zone (near the entry-timeframe 20 EMA) and
prints a confirmation candle. See ``docs`` in the module docstring of
``app.domain.strategies.base`` for the general contract.
"""

from __future__ import annotations

from app.domain.analysis.structure import SwingKind, TrendDirection
from app.domain.analysis.timeframe_analysis import TimeframeAnalysis
from app.domain.strategies.base import Direction, SetupStatus, Strategy, TradeSetup

MAX_RISK_ATR_MULTIPLE = 3.0
PULLBACK_ZONE_ATR_MULTIPLE = 1.0
STRUCTURE_BUFFER_ATR_MULTIPLE = 0.25
MIN_STOP_ATR_MULTIPLE = 1.0


class TrendPullbackStrategy(Strategy):
    name = "trend_pullback"

    def analyze(self, higher_tf: TimeframeAnalysis, entry_tf: TimeframeAnalysis) -> TradeSetup:
        bullish_alignment = (
            higher_tf.trend is TrendDirection.BULLISH and higher_tf.bullish_ema_alignment
        )
        bearish_alignment = (
            higher_tf.trend is TrendDirection.BEARISH and higher_tf.bearish_ema_alignment
        )

        if not bullish_alignment and not bearish_alignment:
            return TradeSetup.rejected(
                entry_tf.symbol,
                self.name,
                "Higher-timeframe trend and EMA alignment are not both present.",
            )

        direction = Direction.LONG if bullish_alignment else Direction.SHORT

        if entry_tf.ema_20 is None or entry_tf.atr_14 is None:
            return TradeSetup.rejected(
                entry_tf.symbol, self.name, "Insufficient entry-timeframe data to evaluate a pullback."
            )

        # Judge "is/was this a pullback" from the bar before the potential
        # confirmation candle: the confirmation candle's whole job is to
        # break back out of the pullback zone, so testing the zone against
        # the post-confirmation close would almost always fail.
        reference_close = (
            float(entry_tf.candles[-2].close) if len(entry_tf.candles) >= 2 else entry_tf.last_close
        )
        distance_to_ema20 = abs(reference_close - entry_tf.ema_20)
        in_pullback_zone = distance_to_ema20 <= PULLBACK_ZONE_ATR_MULTIPLE * entry_tf.atr_14

        invalidation_level = self._invalidation_level(entry_tf, direction)
        invalidation_text = self._invalidation_text(direction, invalidation_level)

        if not in_pullback_zone:
            return TradeSetup(
                symbol=entry_tf.symbol,
                strategy_name=self.name,
                direction=direction,
                status=SetupStatus.WATCHING,
                reason=(
                    f"Higher-timeframe trend is {higher_tf.trend.value}; price has not yet "
                    "pulled back into the entry-timeframe 20 EMA zone."
                ),
                invalidation=invalidation_text,
                entry_trigger="Wait for price to retrace toward the 20 EMA on the entry timeframe.",
                warnings=["No live news or spread check has been applied to this setup."],
            )

        confirmed, confirmation_reason = self._check_confirmation(entry_tf, direction)
        if not confirmed:
            return TradeSetup(
                symbol=entry_tf.symbol,
                strategy_name=self.name,
                direction=direction,
                status=SetupStatus.WATCHING,
                reason=(
                    "Price is inside the pullback zone; awaiting a confirmation candle "
                    "before any entry is considered valid."
                ),
                invalidation=invalidation_text,
                entry_trigger=confirmation_reason,
                warnings=["No live news or spread check has been applied to this setup."],
            )

        entry_price = entry_tf.last_close
        stop_loss = self._build_stop_loss(entry_tf, direction, invalidation_level)
        risk = abs(entry_price - stop_loss)

        if risk <= 0 or risk > MAX_RISK_ATR_MULTIPLE * entry_tf.atr_14:
            return TradeSetup.rejected(
                entry_tf.symbol,
                self.name,
                "Stop-loss distance is invalid or excessively wide relative to current volatility.",
            )

        take_profits = self.build_take_profits(entry_price, stop_loss, direction)

        return TradeSetup(
            symbol=entry_tf.symbol,
            strategy_name=self.name,
            direction=direction,
            status=SetupStatus.CONFIRMED,
            reason=(
                f"{higher_tf.trend.value.capitalize()} higher-timeframe alignment with a "
                "confirmed pullback entry trigger. No trade is guaranteed to be profitable."
            ),
            invalidation=invalidation_text,
            entry_price=entry_price,
            entry_trigger="Confirmation candle closed beyond the prior bar's range.",
            stop_loss=stop_loss,
            take_profits=take_profits,
            risk_reward=take_profits[-1].r_multiple if take_profits else None,
            warnings=["No live news or spread check has been applied to this setup."],
        )

    @staticmethod
    def _check_confirmation(entry_tf: TimeframeAnalysis, direction: Direction) -> tuple[bool, str]:
        if len(entry_tf.candles) < 2:
            return False, "Insufficient candle history for confirmation."
        last, prev = entry_tf.candles[-1], entry_tf.candles[-2]
        if direction is Direction.LONG:
            confirmed = last.is_bullish and last.close > prev.high
            return confirmed, "Break and close above the prior candle's high."
        confirmed = last.is_bearish and last.close < prev.low
        return confirmed, "Break and close below the prior candle's low."

    @staticmethod
    def _invalidation_level(entry_tf: TimeframeAnalysis, direction: Direction) -> float | None:
        kind = SwingKind.LOW if direction is Direction.LONG else SwingKind.HIGH
        matching = [s for s in reversed(entry_tf.swings) if s.kind is kind]
        if matching:
            return matching[0].price
        levels = entry_tf.support_levels if direction is Direction.LONG else entry_tf.resistance_levels
        return levels[0] if levels else None

    @staticmethod
    def _invalidation_text(direction: Direction, level: float | None) -> str:
        if level is None:
            return "Setup invalidated if the higher-timeframe trend or EMA alignment breaks down."
        comparison = "closes below" if direction is Direction.LONG else "closes above"
        return f"Setup invalidated if price {comparison} {level:.5f}."

    @staticmethod
    def _build_stop_loss(
        entry_tf: TimeframeAnalysis, direction: Direction, invalidation_level: float | None
    ) -> float:
        atr = entry_tf.atr_14 or 0.0
        buffer = STRUCTURE_BUFFER_ATR_MULTIPLE * atr
        min_volatility_distance = MIN_STOP_ATR_MULTIPLE * atr

        if direction is Direction.LONG:
            structure_sl = (invalidation_level - buffer) if invalidation_level is not None else None
            volatility_sl = entry_tf.last_close - min_volatility_distance
            candidates = [c for c in (structure_sl, volatility_sl) if c is not None]
            return min(candidates)

        structure_sl = (invalidation_level + buffer) if invalidation_level is not None else None
        volatility_sl = entry_tf.last_close + min_volatility_distance
        candidates = [c for c in (structure_sl, volatility_sl) if c is not None]
        return max(candidates)
