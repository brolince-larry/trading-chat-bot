"""Repository layer: the only place that translates between SQLAlchemy rows
and domain dataclasses. Services/routes depend on these, never on the ORM
models directly (Repository Pattern, per project architecture rules).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.market.models import Candle, Timeframe
from app.domain.risk.exposure import ExposureLevel
from app.domain.risk.validation import RiskLimits
from app.domain.strategies.base import Direction, TradeSetup
from app.domain.trading.models import PaperPosition, PositionStatus
from app.infrastructure.database.models import (
    CandleModel,
    RiskLimitsModel,
    TradeJournalModel,
    TradeSetupModel,
)


class CandleRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_many(self, candles: list[Candle], source: str = "simulated") -> None:
        """Dialect-agnostic upsert (works with SQLite in dev and Postgres in
        production) via a per-row select-then-write. Not on any current hot
        path, so simplicity wins over a dialect-specific bulk upsert.
        """
        if not candles:
            return
        for c in candles:
            existing = self._session.execute(
                select(CandleModel).where(
                    CandleModel.symbol == c.symbol,
                    CandleModel.timeframe == c.timeframe.value,
                    CandleModel.timestamp == c.timestamp,
                )
            ).scalar_one_or_none()
            if existing is not None:
                existing.open = c.open
                existing.high = c.high
                existing.low = c.low
                existing.close = c.close
                existing.volume = c.volume
                existing.source = source
            else:
                self._session.add(
                    CandleModel(
                        symbol=c.symbol,
                        timeframe=c.timeframe.value,
                        timestamp=c.timestamp,
                        open=c.open,
                        high=c.high,
                        low=c.low,
                        close=c.close,
                        volume=c.volume,
                        source=source,
                    )
                )
        self._session.commit()

    def get_recent(self, symbol: str, timeframe: Timeframe, count: int) -> list[Candle]:
        stmt = (
            select(CandleModel)
            .where(CandleModel.symbol == symbol, CandleModel.timeframe == timeframe.value)
            .order_by(CandleModel.timestamp.desc())
            .limit(count)
        )
        rows = list(self._session.execute(stmt).scalars())
        rows.reverse()
        return [
            Candle(
                symbol=row.symbol,
                timeframe=Timeframe(row.timeframe),
                timestamp=row.timestamp,
                open=row.open,
                high=row.high,
                low=row.low,
                close=row.close,
                volume=row.volume,
            )
            for row in rows
        ]


class TradeSetupRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(
        self,
        setup: TradeSetup,
        quality_score: int,
    ) -> TradeSetupModel:
        take_profits = setup.take_profits
        model = TradeSetupModel(
            symbol=setup.symbol,
            strategy=setup.strategy_name,
            direction=setup.direction.value,
            status=setup.status.value,
            quality_score=quality_score,
            entry_type="conditional" if setup.entry_price is None else "market",
            entry_price=_to_decimal(setup.entry_price),
            stop_loss=_to_decimal(setup.stop_loss),
            take_profit_1=_to_decimal(take_profits[0].price) if len(take_profits) > 0 else None,
            take_profit_2=_to_decimal(take_profits[1].price) if len(take_profits) > 1 else None,
            risk_reward=_to_decimal(setup.risk_reward),
            invalidation_reason=setup.invalidation,
            created_at=datetime.now(UTC),
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return model


def _to_decimal(value: float | None) -> Decimal | None:
    return None if value is None else Decimal(str(value))


class SqlAlchemyPaperPositionRepository:
    """Implements :class:`app.domain.trading.repository.PaperPositionRepository`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, position: PaperPosition) -> PaperPosition:
        model = TradeJournalModel(
            id=position.id,
            symbol=position.symbol,
            strategy=position.strategy,
            direction=position.direction.value,
            status=position.status.value,
            entry_price=position.entry_price,
            stop_loss=position.stop_loss,
            take_profit=position.take_profit,
            lots=position.lots,
            units=position.units,
            account_currency=position.account_currency,
            pip_value_per_unit=position.pip_value_per_unit,
            opened_at=position.opened_at,
        )
        self._session.add(model)
        self._session.commit()
        return position

    def get(self, position_id: str) -> PaperPosition | None:
        model = self._session.get(TradeJournalModel, position_id)
        return _to_domain(model) if model is not None else None

    def list_open(self) -> list[PaperPosition]:
        stmt = select(TradeJournalModel).where(TradeJournalModel.status == PositionStatus.OPEN.value)
        return [_to_domain(m) for m in self._session.execute(stmt).scalars()]

    def list_closed(self) -> list[PaperPosition]:
        stmt = (
            select(TradeJournalModel)
            .where(TradeJournalModel.status != PositionStatus.OPEN.value)
            .order_by(TradeJournalModel.closed_at.desc())
        )
        return [_to_domain(m) for m in self._session.execute(stmt).scalars()]

    def update(self, position: PaperPosition) -> PaperPosition:
        model = self._session.get(TradeJournalModel, position.id)
        if model is None:
            raise ValueError(f"No persisted position with id {position.id}")
        model.status = position.status.value
        model.exit_price = position.close_price
        model.profit_loss = position.realized_pnl
        model.risk_multiple = position.risk_multiple
        model.closed_at = position.closed_at
        self._session.commit()
        return position


def _to_domain(model: TradeJournalModel) -> PaperPosition:
    return PaperPosition(
        id=model.id,
        symbol=model.symbol,
        strategy=model.strategy,
        direction=Direction(model.direction),
        entry_price=model.entry_price,
        stop_loss=model.stop_loss,
        take_profit=model.take_profit,
        lots=model.lots,
        units=model.units,
        account_currency=model.account_currency,
        pip_value_per_unit=model.pip_value_per_unit,
        status=PositionStatus(model.status),
        opened_at=model.opened_at,
        closed_at=model.closed_at,
        close_price=model.exit_price,
        realized_pnl=model.profit_loss,
        risk_multiple=model.risk_multiple,
    )


class RiskLimitsRepository:
    """Single-row settings table for the account's configured risk limits."""

    _SINGLETON_ID = "default"

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self) -> RiskLimits:
        model = self._session.get(RiskLimitsModel, self._SINGLETON_ID)
        if model is None:
            return RiskLimits()
        return RiskLimits(
            max_risk_per_trade_percent=model.max_risk_per_trade_percent,
            max_daily_loss_percent=model.max_daily_loss_percent,
            max_open_positions=model.max_open_positions,
            max_spread_pips=model.max_spread_pips,
            max_correlated_exposure=ExposureLevel(model.max_correlated_exposure),
            min_risk_reward=model.min_risk_reward,
        )

    def save(self, limits: RiskLimits) -> RiskLimits:
        model = self._session.get(RiskLimitsModel, self._SINGLETON_ID)
        if model is None:
            model = RiskLimitsModel(id=self._SINGLETON_ID)
            self._session.add(model)
        model.max_risk_per_trade_percent = limits.max_risk_per_trade_percent
        model.max_daily_loss_percent = limits.max_daily_loss_percent
        model.max_open_positions = limits.max_open_positions
        model.max_spread_pips = limits.max_spread_pips
        model.max_correlated_exposure = limits.max_correlated_exposure.value
        model.min_risk_reward = limits.min_risk_reward
        self._session.commit()
        return limits
