"""Dependency-injection wiring for FastAPI routes.

Keeping provider construction here (rather than inside routes) is what lets
routes stay thin and lets tests substitute a different provider/scanner
without touching route code.
"""

from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain.market.data_provider import MarketDataProvider
from app.domain.scanner.pair_scanner import PairScanner
from app.domain.trading.paper_trading_service import PaperTradingService
from app.infrastructure.database.repositories import (
    RiskLimitsRepository,
    SqlAlchemyPaperPositionRepository,
)
from app.infrastructure.database.session import get_db
from app.infrastructure.market_data.oanda import OandaMarketDataProvider
from app.infrastructure.market_data.simulated import SimulatedMarketDataProvider


@lru_cache
def get_market_data_provider() -> MarketDataProvider:
    settings = get_settings()
    if settings.market_data_provider == "oanda":
        if not settings.oanda_api_key:
            raise RuntimeError(
                "MARKET_DATA_PROVIDER=oanda requires OANDA_API_KEY to be set."
            )
        return OandaMarketDataProvider(
            api_key=settings.oanda_api_key, use_practice=settings.oanda_use_practice
        )
    return SimulatedMarketDataProvider()


@lru_cache
def get_pair_scanner() -> PairScanner:
    return PairScanner(market_data_provider=get_market_data_provider())


def get_db_session() -> Generator[Session, None, None]:
    yield from get_db()


def get_paper_trading_service(session: Session = Depends(get_db_session)) -> PaperTradingService:
    repository = SqlAlchemyPaperPositionRepository(session)
    return PaperTradingService(repository, get_market_data_provider())


def get_risk_limits_repository(session: Session = Depends(get_db_session)) -> RiskLimitsRepository:
    return RiskLimitsRepository(session)
