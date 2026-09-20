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
    contract_size: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("100000"))
    min_lot: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.01"))
    max_lot: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("100"))
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
    volume: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
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

    journal_entries: Mapped[list["TradeJournalModel"]] = relationship(back_populates="setup")


class RiskRuleModel(Base):
    __tablename__ = "risk_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    account_id: Mapped[str] = mapped_column(String(36), index=True)
    max_risk_per_trade_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("1.0"))
    max_daily_loss_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("3.0"))
    max_open_risk_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("6.0"))
    max_positions: Mapped[int] = mapped_column(default=5)
    max_correlated_exposure: Mapped[str] = mapped_column(String(16), default="medium")


class TradeJournalModel(Base):
    __tablename__ = "trade_journal"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    setup_id: Mapped[str | None] = mapped_column(ForeignKey("trade_setups.id"), nullable=True)
    entry_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    take_profit: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    result: Mapped[str | None] = mapped_column(String(16), nullable=True)
    profit_loss: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    risk_multiple: Mapped[Decimal | None] = mapped_column(Numeric(8, 3), nullable=True)
    reason_for_entry: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reason_for_exit: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    setup: Mapped[TradeSetupModel | None] = relationship(back_populates="journal_entries")
