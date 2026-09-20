"""Application configuration, loaded from environment variables / .env.

Centralizing settings here means secrets (broker API keys, DB credentials)
are read once from the environment and never hardcoded or passed to the LLM
layer — see README.md security notes.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Forex AI Market Scanner"
    environment: str = "development"

    database_url: str = "postgresql+psycopg://forex:forex@localhost:5432/forex_ai"

    market_data_provider: str = "simulated"  # "simulated" | "oanda"
    oanda_api_key: str | None = None
    oanda_use_practice: bool = True

    default_account_currency: str = "USD"
    default_risk_percent: float = 1.0

    cors_allowed_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
