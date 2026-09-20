from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_trade_automation_settings_repository
from app.infrastructure.database.repositories import TradeAutomationSettingsRepository
from app.schemas.automations import (
    TradeAutomationSettingsOut,
    TradeAutomationSettingsUpdateRequest,
)

router = APIRouter(prefix="/automations", tags=["automations"])


@router.get("/settings", response_model=TradeAutomationSettingsOut)
def get_automation_settings(
    repo: TradeAutomationSettingsRepository = Depends(get_trade_automation_settings_repository),
) -> TradeAutomationSettingsOut:
    return TradeAutomationSettingsOut.from_domain(repo.get())


@router.put("/settings", response_model=TradeAutomationSettingsOut)
def update_automation_settings(
    request: TradeAutomationSettingsUpdateRequest,
    repo: TradeAutomationSettingsRepository = Depends(get_trade_automation_settings_repository),
) -> TradeAutomationSettingsOut:
    saved = repo.save(request.to_domain())
    return TradeAutomationSettingsOut.from_domain(saved)
