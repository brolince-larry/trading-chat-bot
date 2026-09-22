"""SQLAlchemy engine/session wiring."""

from __future__ import annotations

import logging
from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.infrastructure.database.models import Base

logger = logging.getLogger(__name__)

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = get_settings().database_url
        # SQLite connections are single-thread by default; FastAPI's sync
        # routes and the background asyncio loop each touch the DB from
        # different threads, so this needs relaxing. Safe here because each
        # request/task still gets its own Session from the factory below.
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, pool_pre_ping=True, connect_args=connect_args)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)
    return _session_factory


def get_db() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def reset_engine() -> None:
    """Drop the cached engine/session factory so the next call to
    :func:`get_engine` re-reads settings.database_url. Used by tests that
    need an isolated database; not called in normal operation.
    """
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None


def init_db() -> bool:
    """Create tables if they don't exist. Returns False (without raising) if
    the database is unreachable, so the API can still serve the parts of the
    system (analysis, scanning, risk math) that don't need persistence.
    """
    try:
        Base.metadata.create_all(bind=get_engine())
        return True
    except Exception:
        logger.warning("Database unavailable at startup; persistence endpoints will be degraded.", exc_info=True)
        return False
