from fastapi import APIRouter

from app.api.routes import analysis, health, market, risk, scanner

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(market.router)
api_router.include_router(analysis.router)
api_router.include_router(scanner.router)
api_router.include_router(risk.router)

__all__ = ["api_router"]
