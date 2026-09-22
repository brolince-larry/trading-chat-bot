from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_news_provider
from app.domain.market.symbols import SUPPORTED_SYMBOLS
from app.domain.news.provider import NewsProvider
from app.schemas.news import NewsFeedOut, NewsItemOut

router = APIRouter(prefix="/news", tags=["news"])

_MAX_LIMIT = 50


@router.get("", response_model=NewsFeedOut)
def get_news(
    symbol: str | None = Query(default=None, min_length=3, max_length=16),
    limit: int = Query(default=20, ge=1, le=_MAX_LIMIT),
    provider: NewsProvider = Depends(get_news_provider),
) -> NewsFeedOut:
    symbols = None
    if symbol is not None:
        normalized = symbol.strip().upper()
        if normalized not in SUPPORTED_SYMBOLS:
            return NewsFeedOut(connected=provider.is_connected, message="Unsupported symbol.", items=[])
        symbols = [normalized]

    if not provider.is_connected:
        return NewsFeedOut(
            connected=False,
            message=(
                "No live news feed is connected. Configure a news/economic-calendar "
                "provider to see real market-moving headlines here."
            ),
            items=[],
        )

    items = provider.get_latest(symbols=symbols, limit=limit)
    return NewsFeedOut(connected=True, message="", items=[NewsItemOut.from_domain(i) for i in items])
