"""Port (interface) for paper-position persistence, owned by the domain
layer. Concrete storage (SQLAlchemy, in-memory for tests) lives in
``app.infrastructure`` and implements this Protocol.
"""

from __future__ import annotations

from typing import Protocol

from app.domain.trading.models import PaperPosition


class PaperPositionRepository(Protocol):
    def add(self, position: PaperPosition) -> PaperPosition: ...

    def get(self, position_id: str) -> PaperPosition | None: ...

    def list_open(self) -> list[PaperPosition]: ...

    def list_closed(self) -> list[PaperPosition]: ...

    def update(self, position: PaperPosition) -> PaperPosition: ...
