"""SQLAlchemy ORM models mirroring the persistence schema in the project
spec (symbols, candles, market_analysis, trade_setups, risk_rules,
trade_journal). Domain logic never depends on these directly — they exist
for persistence/history, while live analysis runs on the plain dataclasses
in ``app.domain``.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


class SymbolModel(Base):
    __tablename__ = "symbols"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    base_currency: Mapped[str] = mapped_column(String(3))
    quote_currency: Mapped[str] = mapped_column(String(3))
    pip_size: Mapped[Decimal] = mapped_column(Numeric(12, 8))
    contract_size: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal(100000))
    min_lot: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.01"))
    max_lot: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal(100))
    lot_step: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.01"))
    is_active: Mapped[bool] = mapped_column(default=True)


class CandleModel(Base):
    __tablename__ = "candles"
    __table_args__ = (UniqueConstraint("symbol", "timeframe", "timestamp", name="uq_candle_identity"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    timeframe: Mapped[str] = mapped_column(String(4), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    open: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    high: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    low: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    close: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    volume: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal(0))
    source: Mapped[str] = mapped_column(String(32), default="simulated")


class MarketAnalysisModel(Base):
    __tablename__ = "market_analysis"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    timeframe: Mapped[str] = mapped_column(String(4), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    trend: Mapped[str] = mapped_column(String(16))
    market_regime: Mapped[str] = mapped_column(String(16))
    rsi_14: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    atr_14: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    ema_20: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    ema_50: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    ema_200: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    support_levels: Mapped[list] = mapped_column(JSON, default=list)
    resistance_levels: Mapped[list] = mapped_column(JSON, default=list)


class TradeSetupModel(Base):
    __tablename__ = "trade_setups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    strategy: Mapped[str] = mapped_column(String(32))
    direction: Mapped[str] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(16), index=True)
    quality_score: Mapped[int] = mapped_column(default=0)
    entry_type: Mapped[str] = mapped_column(String(16), default="conditional")
    entry_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    take_profit_1: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    take_profit_2: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    risk_reward: Mapped[Decimal | None] = mapped_column(Numeric(8, 3), nullable=True)
    invalidation_reason: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    journal_entries: Mapped[list[TradeJournalModel]] = relationship(back_populates="setup")


class RiskLimitsModel(Base):
    """Single-row settings table: the account's configured risk limits."""

    __tablename__ = "risk_limits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    max_risk_per_trade_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("1.0"))
    max_daily_loss_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("3.0"))
    max_open_positions: Mapped[int] = mapped_column(default=5)
    max_spread_pips: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("3.0"))
    max_correlated_exposure: Mapped[str] = mapped_column(String(16), default="medium")
    min_risk_reward: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True, default=Decimal("1.5"))
    max_drawdown_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True, default=Decimal("10.0")
    )


class AccountSettingsModel(Base):
    """Single-row settings table: the paper account's starting balance."""

    __tablename__ = "account_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    starting_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal(10000))


class BotSettingsModel(Base):
    """Single-row settings table: which pairs/strategies the background
    scanner watches, and whether it is running at all.
    """

    __tablename__ = "bot_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    enabled: Mapped[bool] = mapped_column(default=True)
    active_symbols: Mapped[list] = mapped_column(JSON, default=list)
    active_strategies: Mapped[list] = mapped_column(JSON, default=list)


class TradeAutomationSettingsModel(Base):
    """Single-row settings table: breakeven/trailing-stop automation rules
    applied to already-open positions by the background loop.
    """

    __tablename__ = "trade_automation_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    breakeven_enabled: Mapped[bool] = mapped_column(default=False)
    breakeven_at_r: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("1.0"))
    trailing_stop_enabled: Mapped[bool] = mapped_column(default=False)
    trailing_stop_pips: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal(20))


class NotificationModel(Base):
    """A real event generated by the background loop — never a fabricated
    or scheduled "demo" notification.
    """

    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    type: Mapped[str] = mapped_column(String(24), index=True)
    message: Mapped[str] = mapped_column(String(500))
    symbol: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    read: Mapped[bool] = mapped_column(default=False, index=True)


class TradeJournalModel(Base):
    """A paper (simulated) position: opened from a scanner candidate,
    tracked live against the market, and closed automatically on
    stop-loss/take-profit or manually by the user.
    """

    __tablename__ = "trade_journal"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    setup_id: Mapped[str | None] = mapped_column(ForeignKey("trade_setups.id"), nullable=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    strategy: Mapped[str] = mapped_column(String(32))
    direction: Mapped[str] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(24), index=True, default="open")
    entry_price: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    stop_loss: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    take_profit: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    lots: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    units: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    account_currency: Mapped[str] = mapped_column(String(3))
    pip_value_per_unit: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    profit_loss: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    risk_multiple: Mapped[Decimal | None] = mapped_column(Numeric(8, 3), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    setup: Mapped[TradeSetupModel | None] = relationship(back_populates="journal_entries")
