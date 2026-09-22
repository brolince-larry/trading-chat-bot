from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

from app.domain.automation.models import TradeAutomationSettings


class TradeAutomationSettingsOut(BaseModel):
    breakeven_enabled: bool
    breakeven_at_r: Decimal
    trailing_stop_enabled: bool
    trailing_stop_pips: Decimal

    @classmethod
    def from_domain(cls, settings: TradeAutomationSettings) -> TradeAutomationSettingsOut:
        return cls(
            breakeven_enabled=settings.breakeven_enabled,
            breakeven_at_r=settings.breakeven_at_r,
            trailing_stop_enabled=settings.trailing_stop_enabled,
            trailing_stop_pips=settings.trailing_stop_pips,
        )


class TradeAutomationSettingsUpdateRequest(BaseModel):
    breakeven_enabled: bool
    breakeven_at_r: Decimal = Field(..., gt=0, le=Decimal(50))
    trailing_stop_enabled: bool
    trailing_stop_pips: Decimal = Field(..., gt=0, le=Decimal(1000))

    def to_domain(self) -> TradeAutomationSettings:
        return TradeAutomationSettings(
            breakeven_enabled=self.breakeven_enabled,
            breakeven_at_r=self.breakeven_at_r,
            trailing_stop_enabled=self.trailing_stop_enabled,
            trailing_stop_pips=self.trailing_stop_pips,
        )
