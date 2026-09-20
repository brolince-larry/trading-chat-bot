"""Breakout-and-retest strategy.

Identifies a prior consolidation range, requires a decisive breakout (body
large enough relative to ATR to rule out a single noisy wick), then waits
for price to retest the broken level and print a rejection candle before
confirming a setup.
"""

from __future__ import annotations

from app.domain.analysis.timeframe_analysis import TimeframeAnalysis
from app.domain.market.models import Candle
from app.domain.strategies.base import Direction, SetupStatus, Strategy, TradeSetup

RANGE_LOOKBACK = 30
BREAKOUT_WINDOW = 6
MIN_BREAKOUT_BODY_ATR_MULTIPLE = 0.5
RETEST_TOLERANCE_ATR_MULTIPLE = 0.4
STOP_BUFFER_ATR_MULTIPLE = 0.5


class BreakoutRetestStrategy(Strategy):
    name = "breakout_retest"

    def analyze(self, higher_tf: TimeframeAnalysis, entry_tf: TimeframeAnalysis) -> TradeSetup:
        candles = entry_tf.candles
        atr = entry_tf.atr_14
        if atr is None or len(candles) < RANGE_LOOKBACK + BREAKOUT_WINDOW + 1:
            return TradeSetup.rejected(
                entry_tf.symbol, self.name, "Insufficient candle history to identify a range."
            )

        range_slice = candles[-(RANGE_LOOKBACK + BREAKOUT_WINDOW) : -BREAKOUT_WINDOW]
        range_high = max(float(c.high) for c in range_slice)
        range_low = min(float(c.low) for c in range_slice)

        recent = candles[-BREAKOUT_WINDOW:]
        breakout = self._find_breakout(recent, range_high, range_low, atr)

        if breakout is None:
            return TradeSetup.rejected(
                entry_tf.symbol, self.name, "No valid breakout of the prior range has occurred."
            )

        direction, level, breakout_index = breakout
        post_breakout = recent[breakout_index + 1 :]

        retested, rejection_confirmed = self._check_retest(post_breakout, level, direction, atr)

        invalidation_text = (
            f"Setup invalidated if price closes back inside the range beyond "
            f"{level:.5f}."
        )

        if not retested:
            return TradeSetup(
                symbol=entry_tf.symbol,
                strategy_name=self.name,
                direction=direction,
                status=SetupStatus.WATCHING,
                reason=f"Breakout of the prior range detected at {level:.5f}; awaiting a retest.",
                invalidation=invalidation_text,
                entry_trigger="Wait for price to return to the breakout level and hold.",
                warnings=["No live news or spread check has been applied to this setup."],
            )

        if not rejection_confirmed:
            return TradeSetup(
                symbol=entry_tf.symbol,
                strategy_name=self.name,
                direction=direction,
                status=SetupStatus.WATCHING,
                reason="Price has retested the breakout level; awaiting a rejection candle.",
                invalidation=invalidation_text,
                entry_trigger="Wait for a confirmation candle rejecting the retest level.",
                warnings=["No live news or spread check has been applied to this setup."],
            )

        entry_price = entry_tf.last_close
        buffer = STOP_BUFFER_ATR_MULTIPLE * atr
        stop_loss = level - buffer if direction is Direction.LONG else level + buffer
        risk = abs(entry_price - stop_loss)

        if risk <= 0:
            return TradeSetup.rejected(entry_tf.symbol, self.name, "Invalid risk geometry after retest.")

        take_profits = self.build_take_profits(entry_price, stop_loss, direction)

        return TradeSetup(
            symbol=entry_tf.symbol,
            strategy_name=self.name,
            direction=direction,
            status=SetupStatus.CONFIRMED,
            reason=(
                f"Breakout of {level:.5f} was retested and rejected in the breakout direction. "
                "No trade is guaranteed to be profitable."
            ),
            invalidation=invalidation_text,
            entry_price=entry_price,
            entry_trigger="Retest rejection candle closed in the breakout direction.",
            stop_loss=stop_loss,
            take_profits=take_profits,
            risk_reward=take_profits[-1].r_multiple if take_profits else None,
            warnings=["No live news or spread check has been applied to this setup."],
        )

    @staticmethod
    def _find_breakout(
        candles: list[Candle], range_high: float, range_low: float, atr: float
    ) -> tuple[Direction, float, int] | None:
        min_body = MIN_BREAKOUT_BODY_ATR_MULTIPLE * atr
        for i, candle in enumerate(candles):
            if float(candle.close) > range_high and float(candle.body) >= min_body:
                return Direction.LONG, range_high, i
            if float(candle.close) < range_low and float(candle.body) >= min_body:
                return Direction.SHORT, range_low, i
        return None

    @staticmethod
    def _check_retest(
        candles: list[Candle], level: float, direction: Direction, atr: float
    ) -> tuple[bool, bool]:
        tolerance = RETEST_TOLERANCE_ATR_MULTIPLE * atr
        retested = False
        for i, candle in enumerate(candles):
            near_level = abs(float(candle.low if direction is Direction.LONG else candle.high) - level) <= tolerance
            if not near_level:
                continue
            retested = True
            is_last = i == len(candles) - 1
            if not is_last:
                continue
            if direction is Direction.LONG:
                rejection_confirmed = candle.is_bullish and float(candle.close) > level
            else:
                rejection_confirmed = candle.is_bearish and float(candle.close) < level
            return retested, rejection_confirmed
        return retested, False
