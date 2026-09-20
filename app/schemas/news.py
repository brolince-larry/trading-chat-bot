from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.domain.news.provider import NewsItem


class NewsItemOut(BaseModel):
    headline: str
    source: str
    published_at: datetime
    url: str | None
    symbols: list[str]
    impact: str | None

    @classmethod
    def from_domain(cls, item: NewsItem) -> NewsItemOut:
        return cls(
            headline=item.headline,
            source=item.source,
            published_at=item.published_at,
            url=item.url,
            symbols=item.symbols,
            impact=item.impact,
        )


class NewsFeedOut(BaseModel):
    connected: bool
    message: str
    items: list[NewsItemOut]
