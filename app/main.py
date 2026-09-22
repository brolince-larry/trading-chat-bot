"""FastAPI application entrypoint.

Wires together config, routes, CORS, and startup/shutdown hooks. All
business logic lives in ``app.domain``; this module is intentionally thin.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.background import run_price_and_position_loop, run_scan_loop
from app.api.routes import api_router
from app.api.routes.websocket import router as websocket_router
from app.config import get_settings
from app.infrastructure.database.session import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    background_tasks = [
        asyncio.create_task(run_scan_loop()),
        asyncio.create_task(run_price_and_position_loop()),
    ]
    yield
    for task in background_tasks:
        task.cancel()
    await asyncio.gather(*background_tasks, return_exceptions=True)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        description=(
            "Deterministic forex market analysis, strategy, and risk-management API. "
            "Produces conditional, explainable trade setups — never guaranteed signals."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "An unexpected error occurred."})

    app.include_router(api_router)
    app.include_router(websocket_router)

    return app


app = create_app()
