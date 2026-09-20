"""Computes the account summary shown on the Dashboard: balance, P&L,
win rate, and an equity curve — all walked from real closed/open paper
positions ordered by time, never fabricated.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.domain.account.models import AccountSummary, EquityPoint, PairPerformance
from app.domain.risk.decimal_utils import to_plain
from app.domain.trading.paper_trading_service import PaperTradingService

_RANGE_WINDOWS: dict[str, timedelta | None] = {
    "1d": timedelta(days=1),
    "1w": timedelta(days=7),
    "1m": timedelta(days=30),
    "3m": timedelta(days=90),
    "6m": timedelta(days=180),
    "1y": timedelta(days=365),
    "all": None,
}
DEFAULT_RANGE = "1m"


class AccountService:
    def __init__(self, trading_service: PaperTradingService, starting_balance: Decimal) -> None:
        self._trading = trading_service
        self._starting_balance = starting_balance

    def compute_summary(self, range_key: str = DEFAULT_RANGE) -> AccountSummary:
        window = _RANGE_WINDOWS.get(range_key, _RANGE_WINDOWS[DEFAULT_RANGE])
        closed = sorted(self._trading.list_closed(), key=lambda p: p.closed_at or datetime.min.replace(tzinfo=UTC))
        open_with_pnl = self._trading.list_open_with_pnl()

        total_realized = sum((p.realized_pnl or Decimal(0) for p in closed), Decimal(0))
        total_unrealized = sum((pnl for _, pnl in open_with_pnl), Decimal(0))
        balance = to_plain(self._starting_balance + total_realized)
        balance_with_open = to_plain(balance + total_unrealized)

        total_pnl_percent = (
            float(to_plain((total_realized + total_unrealized) / self._starting_balance * 100))
            if self._starting_balance > 0
            else 0.0
        )

        wins = [p for p in closed if p.realized_pnl is not None and p.realized_pnl > 0]
        win_rate = len(wins) / len(closed) if closed else None

        equity_curve = self._build_equity_curve(closed)
        if window is not None:
            cutoff = datetime.now(UTC) - window
            equity_curve = [point for point in equity_curve if point.timestamp >= cutoff] or equity_curve[-1:]

        top_pairs = self._top_pairs(closed)

        return AccountSummary(
            starting_balance=self._starting_balance,
            balance=balance_with_open,
            total_realized_pnl=to_plain(total_realized),
            total_unrealized_pnl=to_plain(total_unrealized),
            total_pnl_percent=total_pnl_percent,
            active_trades=len(open_with_pnl),
            win_rate=win_rate,
            equity_curve=equity_curve,
            top_pairs=top_pairs,
        )

    def _build_equity_curve(self, closed_sorted) -> list[EquityPoint]:
        curve = [EquityPoint(timestamp=self._first_timestamp(closed_sorted), balance=self._starting_balance)]
        running = self._starting_balance
        for position in closed_sorted:
            running = to_plain(running + (position.realized_pnl or Decimal(0)))
            curve.append(EquityPoint(timestamp=position.closed_at or datetime.now(UTC), balance=running))
        return curve

    def _first_timestamp(self, closed_sorted) -> datetime:
        if closed_sorted and closed_sorted[0].opened_at is not None:
            return closed_sorted[0].opened_at
        return datetime.now(UTC)

    def _top_pairs(self, closed, limit: int = 5) -> list[PairPerformance]:
        totals: dict[str, Decimal] = {}
        counts: dict[str, int] = {}
        for position in closed:
            totals[position.symbol] = totals.get(position.symbol, Decimal(0)) + (position.realized_pnl or Decimal(0))
            counts[position.symbol] = counts.get(position.symbol, 0) + 1
        ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)[:limit]
        return [
            PairPerformance(symbol=symbol, realized_pnl=to_plain(pnl), trade_count=counts[symbol])
            for symbol, pnl in ranked
        ]
