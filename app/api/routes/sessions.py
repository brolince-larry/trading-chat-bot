from __future__ import annotations

from fastapi import APIRouter

from app.domain.market.sessions import get_session_snapshot
from app.schemas.sessions import MarketSessionSnapshotOut

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=MarketSessionSnapshotOut)
def get_sessions() -> MarketSessionSnapshotOut:
    return MarketSessionSnapshotOut.from_domain(get_session_snapshot())
