from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_bot_settings_repository, get_notification_repository
from app.domain.notifications.models import NotificationType
from app.infrastructure.database.repositories import (
    BotSettingsRepository,
    NotificationRepository,
)
from app.schemas.bot import BotSettingsOut, BotSettingsUpdateRequest

router = APIRouter(prefix="/bot", tags=["bot"])


@router.get("/settings", response_model=BotSettingsOut)
def get_bot_settings(repo: BotSettingsRepository = Depends(get_bot_settings_repository)) -> BotSettingsOut:
    return BotSettingsOut.from_domain(repo.get())


@router.put("/settings", response_model=BotSettingsOut)
def update_bot_settings(
    request: BotSettingsUpdateRequest,
    repo: BotSettingsRepository = Depends(get_bot_settings_repository),
    notifications: NotificationRepository = Depends(get_notification_repository),
) -> BotSettingsOut:
    saved = repo.save(request.to_domain())
    status_text = "started" if saved.enabled else "paused"
    notifications.add(
        NotificationType.BOT_UPDATE,
        f"Bot {status_text} — watching {len(saved.active_symbols)} pair(s) with "
        f"{len(saved.active_strategies)} strategy(ies).",
    )
    return BotSettingsOut.from_domain(saved)
