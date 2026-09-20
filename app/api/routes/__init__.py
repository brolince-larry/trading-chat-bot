from fastapi import APIRouter

from app.api.routes import (
    analysis,
    health,
    market,
    news,
    positions,
    risk,
    scanner,
    sessions,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(market.router)
api_router.include_router(analysis.router)
api_router.include_router(scanner.router)
api_router.include_router(risk.router)
api_router.include_router(positions.router)
api_router.include_router(sessions.router)
api_router.include_router(news.router)

__all__ = ["api_router"]
