from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.domain.bot.models import BotSettings
from app.domain.market.symbols import SUPPORTED_SYMBOLS
from app.domain.strategies import ALL_STRATEGIES

_VALID_STRATEGIES = {s.name for s in ALL_STRATEGIES}


class BotSettingsOut(BaseModel):
    enabled: bool
    active_symbols: list[str]
    active_strategies: list[str]

    @classmethod
    def from_domain(cls, settings: BotSettings) -> BotSettingsOut:
        return cls(
            enabled=settings.enabled,
            active_symbols=settings.active_symbols,
            active_strategies=settings.active_strategies,
        )


class BotSettingsUpdateRequest(BaseModel):
    enabled: bool
    active_symbols: list[str] = Field(..., min_length=1)
    active_strategies: list[str] = Field(..., min_length=1)

    @field_validator("active_symbols")
    @classmethod
    def _validate_symbols(cls, value: list[str]) -> list[str]:
        normalized = [s.strip().upper() for s in value]
        unknown = [s for s in normalized if s not in SUPPORTED_SYMBOLS]
        if unknown:
            raise ValueError(f"Unsupported symbols: {', '.join(unknown)}")
        return normalized

    @field_validator("active_strategies")
    @classmethod
    def _validate_strategies(cls, value: list[str]) -> list[str]:
        unknown = [s for s in value if s not in _VALID_STRATEGIES]
        if unknown:
            raise ValueError(f"Unknown strategies: {', '.join(unknown)}")
        return value

    def to_domain(self) -> BotSettings:
        return BotSettings(
            enabled=self.enabled,
            active_symbols=self.active_symbols,
            active_strategies=self.active_strategies,
        )
