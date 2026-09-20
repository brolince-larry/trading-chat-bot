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

    # SQLite by default: zero infrastructure to run locally. Set to a
    # postgresql+psycopg:// URL (see docker-compose.yml) for production.
    database_url: str = "sqlite:///./forex_ai.db"

    market_data_provider: str = "simulated"  # "simulated" | "oanda"
    oanda_api_key: str | None = None
    oanda_use_practice: bool = True

    default_account_currency: str = "USD"
    default_risk_percent: float = 1.0

    cors_allowed_origins: list[str] = ["http://localhost:5173"]

    # How often the background loop re-scans the market and re-checks open
    # paper positions against live prices, in seconds.
    background_scan_interval_seconds: float = 5.0
    background_price_interval_seconds: float = 2.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
