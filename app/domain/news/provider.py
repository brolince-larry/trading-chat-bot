"""News/economic-event data port.

Mirrors the ``MarketDataProvider`` pattern: the domain defines a
``Protocol`` and never fabricates data itself. Until a real provider (a
news wire or economic-calendar API, configured with its own credentials)
is wired in via ``app.config``, ``NoOpNewsProvider`` is used and reports
itself as not connected — the API and UI must show that honestly rather
than inventing headlines.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class NewsItem:
    headline: str
    source: str
    published_at: datetime
    url: str | None
    symbols: list[str]
    impact: str | None  # "high" | "medium" | "low", when the feed provides one


class NewsProvider(Protocol):
    @property
    def is_connected(self) -> bool: ...

    def get_latest(self, symbols: list[str] | None = None, limit: int = 20) -> list[NewsItem]: ...


class NoOpNewsProvider:
    """Default provider: no external news source is configured.

    Always returns an empty result and reports ``is_connected = False`` so
    callers can render an honest "no live news feed connected" state
    instead of silently showing nothing or, worse, fabricated headlines.
    """

    is_connected = False

    def get_latest(self, symbols: list[str] | None = None, limit: int = 20) -> list[NewsItem]:
        return []
