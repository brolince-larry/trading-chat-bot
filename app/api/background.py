"""Background loops that make the dashboard "live": periodic re-scanning,
price ticks, and position monitoring (including auto-closing paper
positions on stop-loss/take-profit), each broadcast over its WebSocket
channel. Started from ``app.main``'s lifespan and cancelled on shutdown.
"""

from __future__ import annotations

import asyncio
import logging

from app.api.deps import get_market_data_provider, get_pair_scanner
from app.api.websocket_manager import position_manager, price_manager, scanner_manager
from app.config import get_settings
from app.domain.market.data_provider import MarketDataProvider
from app.domain.market.symbols import list_symbols
from app.domain.trading.paper_trading_service import PaperTradingService
from app.infrastructure.database.repositories import SqlAlchemyPaperPositionRepository
from app.infrastructure.database.session import get_session_factory
from app.schemas.market import PriceOut
from app.schemas.positions import PositionOut
from app.schemas.scanner import ScanResultOut

logger = logging.getLogger(__name__)


async def run_scan_loop() -> None:
    settings = get_settings()
    scanner = get_pair_scanner()
    symbols = [s.name for s in list_symbols()]

    while True:
        try:
            if scanner_manager.connection_count > 0:
                result = await asyncio.to_thread(scanner.scan, symbols)
                payload = ScanResultOut.from_domain(result).model_dump(mode="json")
                await scanner_manager.broadcast(payload)
        except Exception:
            logger.exception("Background scan loop iteration failed")
        await asyncio.sleep(settings.background_scan_interval_seconds)


async def run_price_and_position_loop() -> None:
    settings = get_settings()
    provider = get_market_data_provider()
    symbols = list_symbols()

    while True:
        try:
            if price_manager.connection_count > 0:
                prices = {}
                for spec in symbols:
                    price = await asyncio.to_thread(provider.get_price, spec.name)
                    prices[spec.name] = PriceOut.from_domain(price, spec.pip_size).model_dump(mode="json")
                await price_manager.broadcast(prices)

            if position_manager.connection_count > 0:
                await _check_and_broadcast_positions(provider)
        except Exception:
            logger.exception("Background price/position loop iteration failed")
        await asyncio.sleep(settings.background_price_interval_seconds)


async def _check_and_broadcast_positions(provider: MarketDataProvider) -> None:
    session = get_session_factory()()
    try:
        service = PaperTradingService(SqlAlchemyPaperPositionRepository(session), provider)
        await asyncio.to_thread(service.check_and_close_triggered)
        open_positions = await asyncio.to_thread(service.list_open_with_pnl)
        payload = [PositionOut.from_domain(p, pnl).model_dump(mode="json") for p, pnl in open_positions]
        await position_manager.broadcast(payload)
    finally:
        session.close()
