from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.domain.market.sessions import get_session_snapshot


def _at(hour: int, minute: int = 0) -> datetime:
    # A fixed Wednesday (no DST-transition edge cases) at the given UTC hour.
    return datetime(2026, 1, 14, hour, minute, tzinfo=ZoneInfo("UTC"))


def test_london_session_open_during_london_business_hours():
    # 10:00 UTC in January is 10:00 London time (GMT, no DST) — within 08:00-17:00.
    snapshot = get_session_snapshot(_at(10))
    london = next(s for s in snapshot.sessions if s.id == "london")
    assert london.is_open is True


def test_london_session_closed_overnight():
    snapshot = get_session_snapshot(_at(2))
    london = next(s for s in snapshot.sessions if s.id == "london")
    assert london.is_open is False
    assert london.next_open_utc > _at(2)


def test_all_four_sessions_present():
    snapshot = get_session_snapshot(_at(12))
    ids = {s.id for s in snapshot.sessions}
    assert ids == {"sydney", "tokyo", "london", "new_york"}


def test_world_clock_covers_expected_cities():
    snapshot = get_session_snapshot(_at(12))
    labels = {w.label for w in snapshot.world_clock}
    assert "New York" in labels
    assert "London" in labels
    assert "Tokyo" in labels
    assert "Sydney" in labels
    assert any("Lagos" in label for label in labels)


def test_london_new_york_overlap_detected():
    # 14:00 UTC: London (08-17 local, GMT) and New York (08-17 local, EST=UTC-5,
    # so 08:00-17:00 EST is 13:00-22:00 UTC in January) are both open.
    snapshot = get_session_snapshot(_at(14))
    assert "london_new_york" in snapshot.active_overlaps


def test_snapshot_is_deterministic_for_same_instant():
    a = get_session_snapshot(_at(9, 30))
    b = get_session_snapshot(_at(9, 30))
    assert [s.is_open for s in a.sessions] == [s.is_open for s in b.sessions]
