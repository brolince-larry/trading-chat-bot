"""Paper-trading service: open/close simulated positions and monitor them
against live prices, exactly like a real execution/position-monitoring
service would — except no order ever reaches a broker.
"""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

from app.domain.market.data_provider import MarketDataProvider
from app.domain.market.symbols import get_symbol
from app.domain.risk.decimal_utils import to_plain
from app.domain.strategies.base import Direction
from app.domain.trading.models import PaperPosition, PerformanceStats, PositionStatus
from app.domain.trading.repository import PaperPositionRepository


class PaperTradingError(Exception):
    pass


class PaperTradingService:
    def __init__(
        self, repository: PaperPositionRepository, market_data_provider: MarketDataProvider
    ) -> None:
        self._repo = repository
        self._provider = market_data_provider

    def open_position(
        self,
        *,
        symbol: str,
        strategy: str,
        direction: Direction,
        entry_price: Decimal,
        stop_loss: Decimal,
        take_profit: Decimal | None,
        lots: Decimal,
        units: Decimal,
        account_currency: str,
        pip_value_per_unit: Decimal,
    ) -> PaperPosition:
        if direction is Direction.NONE:
            raise PaperTradingError("Cannot open a position with no direction.")
        if lots <= 0 or units <= 0:
            raise PaperTradingError("Position size must be positive.")

        # The entry/stop levels usually come from a scan snapshot that can be
        # a few seconds old. If the live price has already moved past the
        # stop (or target) by the time the user clicks "Open", opening
        # anyway would just create a position that closes on the very next
        # background tick with no chance to actually track it — reject it
        # instead, the same way a broker would refuse a stop that's already
        # through the market.
        current_price = self._entry_side_price(symbol, direction)
        sign = Decimal(1) if direction is Direction.LONG else Decimal(-1)
        if (current_price - stop_loss) * sign <= 0:
            raise PaperTradingError(
                "Cannot open: the live price has already moved past this setup's stop-loss. "
                "Re-scan for a current setup instead."
            )
        if take_profit is not None and (take_profit - current_price) * sign <= 0:
            raise PaperTradingError(
                "Cannot open: the live price has already reached this setup's take-profit. "
                "Re-scan for a current setup instead."
            )

        position = PaperPosition(
            id=str(uuid.uuid4()),
            symbol=symbol,
            strategy=strategy,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            lots=lots,
            units=units,
            account_currency=account_currency,
            pip_value_per_unit=pip_value_per_unit,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(UTC),
        )
        return self._repo.add(position)

    def close_position(
        self,
        position_id: str,
        *,
        close_price: Decimal | None = None,
        reason: PositionStatus = PositionStatus.CLOSED_MANUAL,
    ) -> PaperPosition:
        position = self._repo.get(position_id)
        if position is None:
            raise PaperTradingError(f"No position found with id {position_id}.")
        if not position.status.is_open:
            raise PaperTradingError(f"Position {position_id} is already closed.")

        resolved_close_price = close_price if close_price is not None else self._exit_price(position)
        realized_pnl = self.unrealized_pnl(position, resolved_close_price)
        risk = abs(position.entry_price - position.stop_loss)
        sign = Decimal(1) if position.direction is Direction.LONG else Decimal(-1)
        risk_multiple = (
            to_plain((resolved_close_price - position.entry_price) * sign / risk) if risk > 0 else None
        )

        updated = replace(
            position,
            status=reason,
            closed_at=datetime.now(UTC),
            close_price=resolved_close_price,
            realized_pnl=realized_pnl,
            risk_multiple=risk_multiple,
        )
        return self._repo.update(updated)

    def update_stops(
        self,
        position_id: str,
        *,
        stop_loss: Decimal | None = None,
        take_profit: Decimal | None = None,
    ) -> PaperPosition:
        """Adjust an open position's stop-loss and/or take-profit — e.g. to
        move a stop to break-even, or set a target that wasn't set at open.
        At least one of the two must be provided. The new levels are
        validated against the live price the same way ``open_position``
        validates the initial ones, so a stop can't be moved to a price the
        market has already passed.
        """
        if stop_loss is None and take_profit is None:
            raise PaperTradingError("Provide at least one of stop_loss or take_profit to update.")

        position = self._repo.get(position_id)
        if position is None:
            raise PaperTradingError(f"No position found with id {position_id}.")
        if not position.status.is_open:
            raise PaperTradingError(f"Position {position_id} is already closed.")

        new_stop = stop_loss if stop_loss is not None else position.stop_loss
        new_target = take_profit if take_profit is not None else position.take_profit

        current_price = self._entry_side_price(position.symbol, position.direction)
        sign = Decimal(1) if position.direction is Direction.LONG else Decimal(-1)
        if (current_price - new_stop) * sign <= 0:
            raise PaperTradingError(
                "Cannot set stop-loss: the live price is already past that level."
            )
        if new_target is not None and (new_target - current_price) * sign <= 0:
            raise PaperTradingError(
                "Cannot set take-profit: the live price has already reached that level."
            )

        updated = replace(position, stop_loss=new_stop, take_profit=new_target)
        return self._repo.update(updated)

    def check_and_close_triggered(self) -> list[PaperPosition]:
        """Check every open position against the current price and close
        any that have hit their stop-loss or take-profit — the "tracking"
        half of paper trading, not just a static journal entry.
        """
        closed: list[PaperPosition] = []
        for position in self._repo.list_open():
            current = self._exit_price(position)
            hit_stop = (
                position.direction is Direction.LONG and current <= position.stop_loss
            ) or (position.direction is Direction.SHORT and current >= position.stop_loss)
            hit_target = position.take_profit is not None and (
                (position.direction is Direction.LONG and current >= position.take_profit)
                or (position.direction is Direction.SHORT and current <= position.take_profit)
            )

            if hit_stop:
                closed.append(
                    self.close_position(
                        position.id, close_price=position.stop_loss, reason=PositionStatus.CLOSED_STOP_LOSS
                    )
                )
            elif hit_target:
                closed.append(
                    self.close_position(
                        position.id,
                        close_price=position.take_profit,
                        reason=PositionStatus.CLOSED_TAKE_PROFIT,
                    )
                )
        return closed

    def unrealized_pnl(self, position: PaperPosition, current_price: Decimal) -> Decimal:
        pip_size = get_symbol(position.symbol).pip_size
        sign = Decimal(1) if position.direction is Direction.LONG else Decimal(-1)
        price_change_pips = (current_price - position.entry_price) / pip_size
        return to_plain(price_change_pips * sign * position.pip_value_per_unit * position.units)

    def list_open_with_pnl(self) -> list[tuple[PaperPosition, Decimal]]:
        return [
            (position, self.unrealized_pnl(position, self._exit_price(position)))
            for position in self._repo.list_open()
        ]

    def list_closed(self) -> list[PaperPosition]:
        return self._repo.list_closed()

    def performance_stats(self) -> PerformanceStats:
        closed = self._repo.list_closed()
        wins = [p for p in closed if p.realized_pnl is not None and p.realized_pnl > 0]
        losses = [p for p in closed if p.realized_pnl is not None and p.realized_pnl <= 0]
        r_multiples = [float(p.risk_multiple) for p in closed if p.risk_multiple is not None]

        total_pnl = sum((p.realized_pnl or Decimal(0) for p in closed), Decimal(0))
        gross_profit = sum((p.realized_pnl for p in wins), Decimal(0))
        gross_loss = abs(sum((p.realized_pnl for p in losses), Decimal(0)))

        win_rate = len(wins) / len(closed) if closed else None
        average_r = sum(r_multiples) / len(r_multiples) if r_multiples else None
        expectancy_r = average_r
        profit_factor = float(gross_profit / gross_loss) if gross_loss > 0 else None

        return PerformanceStats(
            closed_count=len(closed),
            win_count=len(wins),
            loss_count=len(losses),
            win_rate=win_rate,
            total_realized_pnl=to_plain(total_pnl),
            average_r_multiple=average_r,
            expectancy_r=expectancy_r,
            profit_factor=profit_factor,
        )

    def _exit_price(self, position: PaperPosition) -> Decimal:
        """The price at which this position could be closed right now:
        selling a long hits the bid, buying back a short hits the ask.
        """
        return self._entry_side_price(position.symbol, position.direction, opposite=True)

    def _entry_side_price(
        self, symbol: str, direction: Direction, *, opposite: bool = False
    ) -> Decimal:
        """The price at which a position in ``direction`` would transact
        right now: buying a long (or closing a short) hits the ask, selling
        a short (or closing a long) hits the bid. ``opposite=True`` gives
        the closing-side price instead of the opening-side price.
        """
        price = self._provider.get_price(symbol)
        is_long = direction is Direction.LONG
        wants_ask = is_long != opposite
        return price.ask if wants_ask else price.bid
