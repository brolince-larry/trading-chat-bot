"""Range / mean-reversion strategy.

Only applies while the entry timeframe is classified as ranging (low ADX).
Looks for price approaching a range boundary with an RSI extreme, then
requires a rejection candle back into the range before confirming.
"""

from __future__ import annotations

from app.domain.analysis.structure import MarketRegime
from app.domain.analysis.timeframe_analysis import TimeframeAnalysis
from app.domain.strategies.base import Direction, SetupStatus, Strategy, TakeProfitLevel, TradeSetup

BOUNDARY_TOLERANCE_ATR_MULTIPLE = 0.4
RSI_OVERBOUGHT = 65.0
RSI_OVERSOLD = 35.0
STOP_BUFFER_ATR_MULTIPLE = 0.5


class RangeReversionStrategy(Strategy):
    name = "range_reversion"

    def analyze(self, higher_tf: TimeframeAnalysis, entry_tf: TimeframeAnalysis) -> TradeSetup:
        if entry_tf.regime is not MarketRegime.RANGING:
            return TradeSetup.rejected(
                entry_tf.symbol,
                self.name,
                "Market is not classified as ranging; mean-reversion rules do not apply.",
            )

        if not entry_tf.support_levels or not entry_tf.resistance_levels:
            return TradeSetup.rejected(
                entry_tf.symbol, self.name, "No clear range boundaries could be identified."
            )
        if entry_tf.atr_14 is None or entry_tf.rsi_14 is None:
            return TradeSetup.rejected(entry_tf.symbol, self.name, "Insufficient data to evaluate the range.")

        support = entry_tf.support_levels[0]
        resistance = entry_tf.resistance_levels[0]
        tolerance = BOUNDARY_TOLERANCE_ATR_MULTIPLE * entry_tf.atr_14
        price = entry_tf.last_close

        near_resistance = abs(price - resistance) <= tolerance and entry_tf.rsi_14 >= RSI_OVERBOUGHT
        near_support = abs(price - support) <= tolerance and entry_tf.rsi_14 <= RSI_OVERSOLD

        if not near_resistance and not near_support:
            return TradeSetup.rejected(
                entry_tf.symbol,
                self.name,
                "Price is not currently near a range boundary with a momentum extreme.",
            )

        direction = Direction.SHORT if near_resistance else Direction.LONG
        boundary = resistance if near_resistance else support
        target = support if near_resistance else resistance

        confirmed = self._check_rejection(entry_tf, direction)
        invalidation_text = (
            f"Setup invalidated if price closes beyond {boundary:.5f}, signaling the range has broken."
        )

        if not confirmed:
            return TradeSetup(
                symbol=entry_tf.symbol,
                strategy_name=self.name,
                direction=direction,
                status=SetupStatus.WATCHING,
                reason=(
                    f"Price is testing the range boundary near {boundary:.5f} with an RSI extreme; "
                    "awaiting a rejection candle."
                ),
                invalidation=invalidation_text,
                entry_trigger="Wait for a rejection candle closing back inside the range.",
                warnings=["No live news or spread check has been applied to this setup."],
            )

        entry_price = price
        buffer = STOP_BUFFER_ATR_MULTIPLE * entry_tf.atr_14
        stop_loss = boundary + buffer if direction is Direction.SHORT else boundary - buffer
        risk = abs(entry_price - stop_loss)

        if risk <= 0:
            return TradeSetup.rejected(entry_tf.symbol, self.name, "Invalid risk geometry at the range boundary.")

        reward = abs(target - entry_price)
        risk_reward = reward / risk if risk > 0 else None

        return TradeSetup(
            symbol=entry_tf.symbol,
            strategy_name=self.name,
            direction=direction,
            status=SetupStatus.CONFIRMED,
            reason=(
                f"Range-bound market with a rejection at the {'resistance' if near_resistance else 'support'} "
                "boundary. No trade is guaranteed to be profitable."
            ),
            invalidation=invalidation_text,
            entry_price=entry_price,
            entry_trigger="Rejection candle closed back inside the range.",
            stop_loss=stop_loss,
            take_profits=[TakeProfitLevel(price=target, r_multiple=risk_reward or 0.0)],
            risk_reward=risk_reward,
            warnings=["No live news or spread check has been applied to this setup."],
        )

    @staticmethod
    def _check_rejection(entry_tf: TimeframeAnalysis, direction: Direction) -> bool:
        if not entry_tf.candles:
            return False
        last = entry_tf.candles[-1]
        if direction is Direction.LONG:
            return last.is_bullish
        return last.is_bearish
