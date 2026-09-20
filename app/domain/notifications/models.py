from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class NotificationType(str, Enum):
    TRADE_CLOSED = "trade_closed"
    NEW_SIGNAL = "new_signal"
    RISK_ALERT = "risk_alert"
    BOT_UPDATE = "bot_update"


@dataclass(frozen=True, slots=True)
class Notification:
    id: str
    type: NotificationType
    message: str
    symbol: str | None
    created_at: datetime
    read: bool
