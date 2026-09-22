"""Repository layer: the only place that translates between SQLAlchemy rows
and domain dataclasses. Services/routes depend on these, never on the ORM
models directly (Repository Pattern, per project architecture rules).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.account.models import AccountSettings
from app.domain.automation.models import TradeAutomationSettings
from app.domain.bot.models import BotSettings
from app.domain.market.models import Candle, Timeframe
from app.domain.notifications.models import Notification, NotificationType
from app.domain.risk.exposure import ExposureLevel
from app.domain.risk.validation import RiskLimits
from app.domain.strategies.base import Direction, TradeSetup
from app.domain.trading.models import PaperPosition, PositionStatus
from app.infrastructure.database.models import (
    AccountSettingsModel,
    BotSettingsModel,
    CandleModel,
    NotificationModel,
    RiskLimitsModel,
    TradeAutomationSettingsModel,
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
            max_drawdown_percent=model.max_drawdown_percent,
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
        model.max_drawdown_percent = limits.max_drawdown_percent
        self._session.commit()
        return limits


class AccountSettingsRepository:
    """Single-row settings table: the paper account's starting balance."""

    _SINGLETON_ID = "default"

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self) -> AccountSettings:
        model = self._session.get(AccountSettingsModel, self._SINGLETON_ID)
        if model is None:
            return AccountSettings()
        return AccountSettings(starting_balance=model.starting_balance)

    def save(self, settings: AccountSettings) -> AccountSettings:
        model = self._session.get(AccountSettingsModel, self._SINGLETON_ID)
        if model is None:
            model = AccountSettingsModel(id=self._SINGLETON_ID)
            self._session.add(model)
        model.starting_balance = settings.starting_balance
        self._session.commit()
        return settings


class BotSettingsRepository:
    """Single-row settings table: which pairs/strategies the background
    scanner watches, and whether it is running.
    """

    _SINGLETON_ID = "default"

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self) -> BotSettings:
        model = self._session.get(BotSettingsModel, self._SINGLETON_ID)
        if model is None:
            return BotSettings()
        return BotSettings(
            enabled=model.enabled,
            active_symbols=list(model.active_symbols) or BotSettings().active_symbols,
            active_strategies=list(model.active_strategies) or BotSettings().active_strategies,
        )

    def save(self, settings: BotSettings) -> BotSettings:
        model = self._session.get(BotSettingsModel, self._SINGLETON_ID)
        if model is None:
            model = BotSettingsModel(id=self._SINGLETON_ID)
            self._session.add(model)
        model.enabled = settings.enabled
        model.active_symbols = list(settings.active_symbols)
        model.active_strategies = list(settings.active_strategies)
        self._session.commit()
        return settings


class TradeAutomationSettingsRepository:
    """Single-row settings table: breakeven/trailing-stop automation rules."""

    _SINGLETON_ID = "default"

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self) -> TradeAutomationSettings:
        model = self._session.get(TradeAutomationSettingsModel, self._SINGLETON_ID)
        if model is None:
            return TradeAutomationSettings()
        return TradeAutomationSettings(
            breakeven_enabled=model.breakeven_enabled,
            breakeven_at_r=model.breakeven_at_r,
            trailing_stop_enabled=model.trailing_stop_enabled,
            trailing_stop_pips=model.trailing_stop_pips,
        )

    def save(self, settings: TradeAutomationSettings) -> TradeAutomationSettings:
        model = self._session.get(TradeAutomationSettingsModel, self._SINGLETON_ID)
        if model is None:
            model = TradeAutomationSettingsModel(id=self._SINGLETON_ID)
            self._session.add(model)
        model.breakeven_enabled = settings.breakeven_enabled
        model.breakeven_at_r = settings.breakeven_at_r
        model.trailing_stop_enabled = settings.trailing_stop_enabled
        model.trailing_stop_pips = settings.trailing_stop_pips
        self._session.commit()
        return settings


class NotificationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, type_: NotificationType, message: str, symbol: str | None = None) -> Notification:
        model = NotificationModel(
            id=str(uuid.uuid4()),
            type=type_.value,
            message=message,
            symbol=symbol,
            created_at=datetime.now(UTC),
            read=False,
        )
        self._session.add(model)
        self._session.commit()
        return _notification_to_domain(model)

    def list(self, unread_only: bool = False, limit: int = 50) -> list[Notification]:
        stmt = select(NotificationModel).order_by(NotificationModel.created_at.desc()).limit(limit)
        if unread_only:
            stmt = stmt.where(NotificationModel.read.is_(False))
        return [_notification_to_domain(m) for m in self._session.execute(stmt).scalars()]

    def mark_read(self, notification_id: str) -> None:
        model = self._session.get(NotificationModel, notification_id)
        if model is not None:
            model.read = True
            self._session.commit()

    def mark_all_read(self) -> None:
        for model in self._session.execute(select(NotificationModel).where(NotificationModel.read.is_(False))).scalars():
            model.read = True
        self._session.commit()


def _notification_to_domain(model: NotificationModel) -> Notification:
    return Notification(
        id=model.id,
        type=NotificationType(model.type),
        message=model.message,
        symbol=model.symbol,
        created_at=model.created_at,
        read=model.read,
    )
