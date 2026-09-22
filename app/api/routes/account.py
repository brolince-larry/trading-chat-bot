from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_account_service, get_account_settings_repository
from app.domain.account.service import DEFAULT_RANGE
from app.domain.account.service import AccountService as AccountServiceType
from app.infrastructure.database.repositories import AccountSettingsRepository
from app.schemas.account import (
    AccountSettingsOut,
    AccountSettingsUpdateRequest,
    AccountSummaryOut,
)

router = APIRouter(prefix="/account", tags=["account"])


@router.get("/summary", response_model=AccountSummaryOut)
def get_account_summary(
    period: str = Query(default=DEFAULT_RANGE, pattern="^(1d|1w|1m|3m|6m|1y|all)$"),
    service: AccountServiceType = Depends(get_account_service),
) -> AccountSummaryOut:
    return AccountSummaryOut.from_domain(service.compute_summary(period))


@router.get("/settings", response_model=AccountSettingsOut)
def get_account_settings(
    repo: AccountSettingsRepository = Depends(get_account_settings_repository),
) -> AccountSettingsOut:
    return AccountSettingsOut.from_domain(repo.get())


@router.put("/settings", response_model=AccountSettingsOut)
def update_account_settings(
    request: AccountSettingsUpdateRequest,
    repo: AccountSettingsRepository = Depends(get_account_settings_repository),
) -> AccountSettingsOut:
    saved = repo.save(request.to_domain())
    return AccountSettingsOut.from_domain(saved)
