"""Repository layer: the only place that translates between SQLAlchemy rows
and domain dataclasses. Services/routes depend on these, never on the ORM
models directly (Repository Pattern, per project architecture rules).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.domain.market.models import Candle, Timeframe
from app.domain.strategies.base import TradeSetup
from app.infrastructure.database.models import CandleModel, TradeSetupModel


class CandleRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_many(self, candles: list[Candle], source: str = "simulated") -> None:
        if not candles:
            return
        rows = [
            {
                "symbol": c.symbol,
                "timeframe": c.timeframe.value,
                "timestamp": c.timestamp,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
                "source": source,
            }
            for c in candles
        ]
        stmt = pg_insert(CandleModel).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "timeframe", "timestamp"],
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
                "source": stmt.excluded.source,
            },
        )
        self._session.execute(stmt)
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
