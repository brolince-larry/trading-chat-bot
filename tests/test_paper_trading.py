from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.domain.market.models import Price
from app.domain.strategies.base import Direction
from app.domain.trading.models import PaperPosition, PositionStatus
from app.domain.trading.paper_trading_service import (
    PaperTradingError,
    PaperTradingService,
)


class FakePriceProvider:
    """Test double implementing MarketDataProvider with a settable, fixed price."""

    def __init__(self, bid: Decimal, ask: Decimal) -> None:
        self.bid = bid
        self.ask = ask

    def get_candles(self, symbol, timeframe, count):
        raise NotImplementedError("Not needed for paper-trading tests")

    def get_price(self, symbol: str) -> Price:
        return Price(symbol=symbol, bid=self.bid, ask=self.ask, timestamp=datetime.now(UTC))


class InMemoryPaperPositionRepository:
    """Test double implementing PaperPositionRepository."""

    def __init__(self) -> None:
        self._positions: dict[str, PaperPosition] = {}

    def add(self, position: PaperPosition) -> PaperPosition:
        self._positions[position.id] = position
        return position

    def get(self, position_id: str) -> PaperPosition | None:
        return self._positions.get(position_id)

    def list_open(self) -> list[PaperPosition]:
        return [p for p in self._positions.values() if p.status.is_open]

    def list_closed(self) -> list[PaperPosition]:
        return [p for p in self._positions.values() if not p.status.is_open]

    def update(self, position: PaperPosition) -> PaperPosition:
        self._positions[position.id] = position
        return position


@pytest.fixture
def repo() -> InMemoryPaperPositionRepository:
    return InMemoryPaperPositionRepository()


def _open_long(service: PaperTradingService, entry: str, stop: str, target: str) -> PaperPosition:
    return service.open_position(
        symbol="EUR_USD",
        strategy="trend_pullback",
        direction=Direction.LONG,
        entry_price=Decimal(entry),
        stop_loss=Decimal(stop),
        take_profit=Decimal(target),
        lots=Decimal("0.1"),
        units=Decimal(10000),
        account_currency="USD",
        pip_value_per_unit=Decimal("0.0001"),
    )


def test_open_position_rejects_no_direction(repo):
    provider = FakePriceProvider(Decimal("1.1000"), Decimal("1.1002"))
    service = PaperTradingService(repo, provider)
    with pytest.raises(PaperTradingError):
        service.open_position(
            symbol="EUR_USD",
            strategy="trend_pullback",
            direction=Direction.NONE,
            entry_price=Decimal("1.1000"),
            stop_loss=Decimal("1.0950"),
            take_profit=None,
            lots=Decimal("0.1"),
            units=Decimal(10000),
            account_currency="USD",
            pip_value_per_unit=Decimal("0.0001"),
        )


def test_open_position_rejects_non_positive_size(repo):
    provider = FakePriceProvider(Decimal("1.1000"), Decimal("1.1002"))
    service = PaperTradingService(repo, provider)
    with pytest.raises(PaperTradingError):
        service.open_position(
            symbol="EUR_USD",
            strategy="trend_pullback",
            direction=Direction.LONG,
            entry_price=Decimal("1.1000"),
            stop_loss=Decimal("1.0950"),
            take_profit=None,
            lots=Decimal(0),
            units=Decimal(0),
            account_currency="USD",
            pip_value_per_unit=Decimal("0.0001"),
        )


def test_open_position_rejects_when_price_already_past_stop_loss(repo):
    # Ask (the long-entry price) is already below the proposed stop-loss.
    provider = FakePriceProvider(Decimal("1.0938"), Decimal("1.0940"))
    service = PaperTradingService(repo, provider)
    with pytest.raises(PaperTradingError, match="stop-loss"):
        _open_long(service, "1.1000", "1.0950", "1.1100")
    assert repo.list_open() == []


def test_open_position_rejects_when_price_already_past_take_profit(repo):
    provider = FakePriceProvider(Decimal("1.1150"), Decimal("1.1152"))
    service = PaperTradingService(repo, provider)
    with pytest.raises(PaperTradingError, match="take-profit"):
        _open_long(service, "1.1000", "1.0950", "1.1100")
    assert repo.list_open() == []


def test_unrealized_pnl_positive_for_long_when_price_rises(repo):
    provider = FakePriceProvider(Decimal("1.1050"), Decimal("1.1052"))
    service = PaperTradingService(repo, provider)
    position = _open_long(service, "1.1000", "1.0950", "1.1100")

    # Selling a long exits at the bid.
    pnl = service.unrealized_pnl(position, provider.bid)
    assert pnl > 0


def test_unrealized_pnl_negative_for_long_when_price_falls(repo):
    provider = FakePriceProvider(Decimal("1.0950"), Decimal("1.0952"))
    service = PaperTradingService(repo, provider)
    position = _open_long(service, "1.1000", "1.0900", "1.1100")

    pnl = service.unrealized_pnl(position, provider.bid)
    assert pnl < 0


def test_check_and_close_triggered_closes_on_stop_loss_hit(repo):
    # Open at a price that hasn't touched the stop yet, then let the market
    # move against it — opening directly into an already-breached stop is
    # rejected by open_position itself (tested separately below).
    provider = FakePriceProvider(Decimal("1.1010"), Decimal("1.1012"))
    service = PaperTradingService(repo, provider)
    position = _open_long(service, "1.1000", "1.0950", "1.1100")

    provider.bid, provider.ask = Decimal("1.0940"), Decimal("1.0942")
    closed = service.check_and_close_triggered()

    assert len(closed) == 1
    assert closed[0].id == position.id
    assert closed[0].status is PositionStatus.CLOSED_STOP_LOSS
    assert closed[0].close_price == Decimal("1.0950")
    assert closed[0].realized_pnl is not None
    assert closed[0].realized_pnl < 0
    assert repo.list_open() == []


def test_check_and_close_triggered_closes_on_take_profit_hit(repo):
    provider = FakePriceProvider(Decimal("1.1010"), Decimal("1.1012"))
    service = PaperTradingService(repo, provider)
    position = _open_long(service, "1.1000", "1.0950", "1.1100")

    provider.bid, provider.ask = Decimal("1.1150"), Decimal("1.1152")
    closed = service.check_and_close_triggered()

    assert len(closed) == 1
    assert closed[0].id == position.id
    assert closed[0].status is PositionStatus.CLOSED_TAKE_PROFIT
    assert closed[0].close_price == Decimal("1.1100")
    assert closed[0].realized_pnl > 0


def test_check_and_close_triggered_leaves_position_open_when_untouched(repo):
    provider = FakePriceProvider(Decimal("1.1010"), Decimal("1.1012"))
    service = PaperTradingService(repo, provider)
    _open_long(service, "1.1000", "1.0950", "1.1100")

    closed = service.check_and_close_triggered()

    assert closed == []
    assert len(repo.list_open()) == 1


def test_close_position_manual_computes_risk_multiple(repo):
    provider = FakePriceProvider(Decimal("1.1048"), Decimal("1.1050"))
    service = PaperTradingService(repo, provider)
    position = _open_long(service, "1.1000", "1.0950", "1.1100")

    closed = service.close_position(position.id)

    # risk = 0.0050; move = 1.1048 - 1.1000 = 0.0048 -> ~0.96R
    assert closed.status is PositionStatus.CLOSED_MANUAL
    assert closed.risk_multiple == pytest.approx(Decimal("0.96"), abs=Decimal("0.01"))


def test_close_position_raises_for_unknown_id(repo):
    provider = FakePriceProvider(Decimal("1.1000"), Decimal("1.1002"))
    service = PaperTradingService(repo, provider)
    with pytest.raises(PaperTradingError):
        service.close_position("does-not-exist")


def test_close_position_raises_if_already_closed(repo):
    provider = FakePriceProvider(Decimal("1.1048"), Decimal("1.1050"))
    service = PaperTradingService(repo, provider)
    position = _open_long(service, "1.1000", "1.0950", "1.1100")
    service.close_position(position.id)

    with pytest.raises(PaperTradingError):
        service.close_position(position.id)


def test_update_stops_moves_stop_loss_and_take_profit(repo):
    provider = FakePriceProvider(Decimal("1.1010"), Decimal("1.1012"))
    service = PaperTradingService(repo, provider)
    position = _open_long(service, "1.1000", "1.0950", "1.1100")

    updated = service.update_stops(position.id, stop_loss=Decimal("1.0980"), take_profit=Decimal("1.1150"))

    assert updated.stop_loss == Decimal("1.0980")
    assert updated.take_profit == Decimal("1.1150")


def test_update_stops_rejects_stop_already_passed(repo):
    provider = FakePriceProvider(Decimal("1.1010"), Decimal("1.1012"))
    service = PaperTradingService(repo, provider)
    position = _open_long(service, "1.1000", "1.0950", "1.1100")

    with pytest.raises(PaperTradingError, match="stop-loss"):
        service.update_stops(position.id, stop_loss=Decimal("1.1050"))


def test_update_stops_rejects_no_fields(repo):
    provider = FakePriceProvider(Decimal("1.1010"), Decimal("1.1012"))
    service = PaperTradingService(repo, provider)
    position = _open_long(service, "1.1000", "1.0950", "1.1100")

    with pytest.raises(PaperTradingError):
        service.update_stops(position.id)


def test_update_stops_rejects_unknown_position(repo):
    provider = FakePriceProvider(Decimal("1.1010"), Decimal("1.1012"))
    service = PaperTradingService(repo, provider)

    with pytest.raises(PaperTradingError):
        service.update_stops("does-not-exist", stop_loss=Decimal("1.0980"))


def test_performance_stats_computes_win_rate_and_expectancy(repo):
    provider = FakePriceProvider(Decimal("1.1010"), Decimal("1.1012"))
    service = PaperTradingService(repo, provider)

    winner = _open_long(service, "1.1000", "1.0950", "1.1100")
    service.close_position(winner.id, close_price=Decimal("1.1100"), reason=PositionStatus.CLOSED_TAKE_PROFIT)

    loser = _open_long(service, "1.1000", "1.0950", "1.1100")
    service.close_position(loser.id, close_price=Decimal("1.0950"), reason=PositionStatus.CLOSED_STOP_LOSS)

    stats = service.performance_stats()

    assert stats.closed_count == 2
    assert stats.win_count == 1
    assert stats.loss_count == 1
    assert stats.win_rate == pytest.approx(0.5)
    assert stats.average_r_multiple == pytest.approx(0.5, abs=0.01)  # +2R and -1R average
    assert stats.profit_factor is not None and stats.profit_factor > 1


def test_performance_stats_with_no_closed_positions(repo):
    provider = FakePriceProvider(Decimal("1.1000"), Decimal("1.1002"))
    service = PaperTradingService(repo, provider)
    stats = service.performance_stats()

    assert stats.closed_count == 0
    assert stats.win_rate is None
    assert stats.average_r_multiple is None
    assert stats.profit_factor is None
    assert stats.total_realized_pnl == Decimal(0)
