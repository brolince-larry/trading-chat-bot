"""Background loops that make the dashboard "live": periodic re-scanning,
price ticks, and position monitoring (auto-closing paper positions on
stop-loss/take-profit, applying breakeven/trailing-stop automation, and
raising real notifications), each broadcast over its WebSocket channel.
Started from ``app.main``'s lifespan and cancelled on shutdown.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, date, datetime
from decimal import Decimal

from app.api.deps import get_market_data_provider
from app.api.websocket_manager import (
    notification_manager,
    position_manager,
    price_manager,
    scanner_manager,
)
from app.config import get_settings
from app.domain.market.data_provider import MarketDataProvider
from app.domain.market.symbols import list_symbols
from app.domain.notifications.models import NotificationType
from app.domain.risk.validation import RiskLimits
from app.domain.scanner.pair_scanner import PairScanner
from app.domain.strategies import ALL_STRATEGIES
from app.domain.trading.paper_trading_service import PaperTradingService
from app.infrastructure.database.repositories import (
    AccountSettingsRepository,
    BotSettingsRepository,
    NotificationRepository,
    RiskLimitsRepository,
    SqlAlchemyPaperPositionRepository,
    TradeAutomationSettingsRepository,
)
from app.infrastructure.database.session import get_session_factory
from app.schemas.market import PriceOut
from app.schemas.notifications import NotificationOut
from app.schemas.positions import PositionOut
from app.schemas.scanner import ScanResultOut

logger = logging.getLogger(__name__)

# Tracks (symbol, strategy) pairs already confirmed as of the last scan, so a
# "new signal" notification fires only the first time a setup is confirmed —
# not on every re-scan while it remains confirmed.
_seen_confirmed_setups: set[tuple[str, str]] = set()

# The UTC calendar date a daily-loss risk alert was last raised, so it fires
# at most once per day instead of on every price-loop tick.
_last_risk_alert_date: date | None = None


async def run_scan_loop() -> None:
    settings = get_settings()

    while True:
        try:
            await _run_scan_iteration()
        except Exception:
            logger.exception("Background scan loop iteration failed")
        await asyncio.sleep(settings.background_scan_interval_seconds)


async def _run_scan_iteration() -> None:
    session = get_session_factory()()
    try:
        bot_settings = await asyncio.to_thread(BotSettingsRepository(session).get)
        if not bot_settings.enabled:
            return

        provider = get_market_data_provider()
        strategies = [s for s in ALL_STRATEGIES if s.name in bot_settings.active_strategies] or ALL_STRATEGIES
        all_symbols = {s.name for s in list_symbols()}
        symbols = [s for s in bot_settings.active_symbols if s in all_symbols] or [s.name for s in list_symbols()]

        scanner = PairScanner(market_data_provider=provider, strategies=strategies)
        result = await asyncio.to_thread(scanner.scan, symbols)

        if scanner_manager.connection_count > 0:
            payload = ScanResultOut.from_domain(result).model_dump(mode="json")
            await scanner_manager.broadcast(payload)

        await _raise_new_signal_notifications(session, result)
    finally:
        session.close()


async def _raise_new_signal_notifications(session, result) -> None:
    from app.domain.strategies.base import SetupStatus

    notifications = NotificationRepository(session)
    confirmed_now = {
        (c.setup.symbol, c.setup.strategy_name)
        for c in result.candidates
        if c.setup.status is SetupStatus.CONFIRMED
    }
    newly_confirmed = confirmed_now - _seen_confirmed_setups
    _seen_confirmed_setups.clear()
    _seen_confirmed_setups.update(confirmed_now)

    if not newly_confirmed:
        return
    new_events = []
    for symbol, strategy in newly_confirmed:
        candidate = next(
            c for c in result.candidates if c.setup.symbol == symbol and c.setup.strategy_name == strategy
        )
        message = (
            f"New signal: {symbol} confirmed {candidate.setup.direction.value} setup "
            f"({strategy.replace('_', ' ')}), quality score {candidate.quality_score}."
        )
        event = await asyncio.to_thread(notifications.add, NotificationType.NEW_SIGNAL, message, symbol)
        new_events.append(event)
    if notification_manager.connection_count > 0:
        for event in new_events:
            await notification_manager.broadcast(NotificationOut.from_domain(event).model_dump(mode="json"))


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

            # Position monitoring (auto-close, automation, risk alerts) runs
            # every tick regardless of whether anyone is watching — the bot
            # manages open trades whether or not the dashboard is open.
            await _manage_positions(provider)
        except Exception:
            logger.exception("Background price/position loop iteration failed")
        await asyncio.sleep(settings.background_price_interval_seconds)


async def _manage_positions(provider: MarketDataProvider) -> None:
    session = get_session_factory()()
    try:
        service = PaperTradingService(SqlAlchemyPaperPositionRepository(session), provider)
        notifications = NotificationRepository(session)

        automation_settings = await asyncio.to_thread(TradeAutomationSettingsRepository(session).get)
        await asyncio.to_thread(service.apply_trade_automation, automation_settings)

        closed = await asyncio.to_thread(service.check_and_close_triggered)
        new_events = []
        for position in closed:
            pnl = position.realized_pnl or Decimal(0)
            message = (
                f"Trade closed: {position.symbol} {position.direction.value} closed "
                f"({position.status.value.replace('closed_', '').replace('_', ' ')}) — "
                f"P&L {'+' if pnl >= 0 else ''}{pnl}."
            )
            event = await asyncio.to_thread(
                notifications.add, NotificationType.TRADE_CLOSED, message, position.symbol
            )
            new_events.append(event)

        new_events.extend(await _check_daily_loss_alert(session, service, notifications))

        open_positions = await asyncio.to_thread(service.list_open_with_pnl)
        if position_manager.connection_count > 0:
            payload = [PositionOut.from_domain(p, pnl).model_dump(mode="json") for p, pnl in open_positions]
            await position_manager.broadcast(payload)

        if new_events and notification_manager.connection_count > 0:
            for event in new_events:
                await notification_manager.broadcast(NotificationOut.from_domain(event).model_dump(mode="json"))
    finally:
        session.close()


async def _check_daily_loss_alert(session, service: PaperTradingService, notifications: NotificationRepository):
    global _last_risk_alert_date
    today = datetime.now(UTC).date()
    if _last_risk_alert_date == today:
        return []

    limits: RiskLimits = await asyncio.to_thread(RiskLimitsRepository(session).get)
    starting_balance = (await asyncio.to_thread(AccountSettingsRepository(session).get)).starting_balance

    closed_today = [
        p for p in await asyncio.to_thread(service.list_closed) if p.closed_at is not None and p.closed_at.date() == today
    ]
    realized_today = sum((p.realized_pnl or Decimal(0) for p in closed_today), Decimal(0))
    if realized_today >= 0:
        return []

    max_daily_loss_amount = starting_balance * (limits.max_daily_loss_percent / Decimal(100))
    if abs(realized_today) < max_daily_loss_amount:
        return []

    _last_risk_alert_date = today
    message = (
        f"Risk alert: today's realized loss ({realized_today}) has reached the daily "
        f"limit of {limits.max_daily_loss_percent}% ({-max_daily_loss_amount})."
    )
    event = await asyncio.to_thread(notifications.add, NotificationType.RISK_ALERT, message, None)
    return [event]
