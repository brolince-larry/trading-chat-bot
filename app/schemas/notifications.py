from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.domain.notifications.models import Notification, NotificationType


class NotificationOut(BaseModel):
    id: str
    type: NotificationType
    message: str
    symbol: str | None
    created_at: datetime
    read: bool

    @classmethod
    def from_domain(cls, notification: Notification) -> NotificationOut:
        return cls(
            id=notification.id,
            type=notification.type,
            message=notification.message,
            symbol=notification.symbol,
            created_at=notification.created_at,
            read=notification.read,
        )
