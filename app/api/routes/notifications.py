from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_notification_repository
from app.infrastructure.database.repositories import NotificationRepository
from app.schemas.notifications import NotificationOut

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    unread_only: bool = Query(default=False),
    repo: NotificationRepository = Depends(get_notification_repository),
) -> list[NotificationOut]:
    return [NotificationOut.from_domain(n) for n in repo.list(unread_only=unread_only)]


@router.post("/{notification_id}/read", status_code=204)
def mark_notification_read(
    notification_id: str, repo: NotificationRepository = Depends(get_notification_repository)
) -> None:
    existing = repo.list()
    if not any(n.id == notification_id for n in existing):
        raise HTTPException(status_code=404, detail="Notification not found.")
    repo.mark_read(notification_id)


@router.post("/read-all", status_code=204)
def mark_all_notifications_read(repo: NotificationRepository = Depends(get_notification_repository)) -> None:
    repo.mark_all_read()
