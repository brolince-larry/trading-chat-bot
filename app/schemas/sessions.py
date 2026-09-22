from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.domain.market.sessions import (
    MarketSessionSnapshot,
    SessionStatus,
    WorldClockEntry,
)


class SessionStatusOut(BaseModel):
    id: str
    label: str
    timezone: str
    is_open: bool
    local_time: datetime
    next_open_utc: datetime
    next_close_utc: datetime

    @classmethod
    def from_domain(cls, status: SessionStatus) -> SessionStatusOut:
        return cls(
            id=status.id,
            label=status.label,
            timezone=status.timezone,
            is_open=status.is_open,
            local_time=status.local_time,
            next_open_utc=status.next_open_utc,
            next_close_utc=status.next_close_utc,
        )


class WorldClockEntryOut(BaseModel):
    label: str
    timezone: str
    local_time: datetime
    utc_offset: str

    @classmethod
    def from_domain(cls, entry: WorldClockEntry) -> WorldClockEntryOut:
        return cls(
            label=entry.label,
            timezone=entry.timezone,
            local_time=entry.local_time,
            utc_offset=entry.utc_offset,
        )


class MarketSessionSnapshotOut(BaseModel):
    generated_at: datetime
    sessions: list[SessionStatusOut]
    world_clock: list[WorldClockEntryOut]
    active_overlaps: list[str]

    @classmethod
    def from_domain(cls, snapshot: MarketSessionSnapshot) -> MarketSessionSnapshotOut:
        return cls(
            generated_at=snapshot.generated_at,
            sessions=[SessionStatusOut.from_domain(s) for s in snapshot.sessions],
            world_clock=[WorldClockEntryOut.from_domain(w) for w in snapshot.world_clock],
            active_overlaps=snapshot.active_overlaps,
        )
