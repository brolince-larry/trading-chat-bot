"""Real trading-session and world-clock math.

No external API is needed for this: session open/close hours are fixed
market conventions, and converting "now" into each exchange's local time
(DST-aware) is pure `zoneinfo` arithmetic. This deliberately does not
attempt to score which session is "best" for a given pair — that judgment
belongs to the scanner's setup-quality scoring, which has actual price
structure to reason about; this module only answers "which sessions are
open right now, and what time is it around the world."
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

# (session id, display label, IANA zone, local open time, local close time).
# Hours are the conventional exchange-floor hours for each financial centre;
# none of them cross local midnight, which keeps the open/close arithmetic
# below simple.
_SESSION_DEFINITIONS: tuple[tuple[str, str, str, time, time], ...] = (
    ("sydney", "Sydney", "Australia/Sydney", time(8, 0), time(17, 0)),
    ("tokyo", "Tokyo", "Asia/Tokyo", time(9, 0), time(18, 0)),
    ("london", "London", "Europe/London", time(8, 0), time(17, 0)),
    ("new_york", "New York", "America/New_York", time(8, 0), time(17, 0)),
)

# World-clock cities, per the request to show NY / London / "Africa time" /
# Tokyo alongside each other. Africa/Lagos (WAT, UTC+1, no DST) is used as
# the representative "Africa time" zone.
_WORLD_CLOCK_ZONES: tuple[tuple[str, str], ...] = (
    ("New York", "America/New_York"),
    ("London", "Europe/London"),
    ("Lagos (Africa/WAT)", "Africa/Lagos"),
    ("Tokyo", "Asia/Tokyo"),
    ("Sydney", "Australia/Sydney"),
)

# Well-known high-liquidity session overlaps, in UTC hour-of-day terms. Used
# only to label an overlap window for the UI — not a trading signal.
_OVERLAPS: tuple[tuple[str, tuple[str, str]], ...] = (
    ("london_new_york", ("london", "new_york")),
    ("tokyo_london", ("tokyo", "london")),
    ("sydney_tokyo", ("sydney", "tokyo")),
)


@dataclass(frozen=True, slots=True)
class SessionStatus:
    id: str
    label: str
    timezone: str
    is_open: bool
    local_time: datetime
    next_open_utc: datetime
    next_close_utc: datetime


@dataclass(frozen=True, slots=True)
class WorldClockEntry:
    label: str
    timezone: str
    local_time: datetime
    utc_offset: str


@dataclass(frozen=True, slots=True)
class MarketSessionSnapshot:
    generated_at: datetime
    sessions: list[SessionStatus]
    world_clock: list[WorldClockEntry]
    active_overlaps: list[str]


def get_session_snapshot(now_utc: datetime | None = None) -> MarketSessionSnapshot:
    now_utc = (now_utc or datetime.now(ZoneInfo("UTC"))).astimezone(ZoneInfo("UTC"))

    sessions = [_session_status(session_id, label, zone_name, opens, closes, now_utc)
                for session_id, label, zone_name, opens, closes in _SESSION_DEFINITIONS]
    open_ids = {s.id for s in sessions if s.is_open}

    active_overlaps = [
        overlap_id for overlap_id, (a, b) in _OVERLAPS if a in open_ids and b in open_ids
    ]

    world_clock = [_world_clock_entry(label, zone_name, now_utc) for label, zone_name in _WORLD_CLOCK_ZONES]

    return MarketSessionSnapshot(
        generated_at=now_utc,
        sessions=sessions,
        world_clock=world_clock,
        active_overlaps=active_overlaps,
    )


def _session_status(
    session_id: str,
    label: str,
    zone_name: str,
    opens: time,
    closes: time,
    now_utc: datetime,
) -> SessionStatus:
    zone = ZoneInfo(zone_name)
    local_now = now_utc.astimezone(zone)
    local_time_of_day = local_now.time()
    is_open = opens <= local_time_of_day < closes

    today_open = local_now.replace(hour=opens.hour, minute=opens.minute, second=0, microsecond=0)
    today_close = local_now.replace(hour=closes.hour, minute=closes.minute, second=0, microsecond=0)

    if is_open:
        next_close = today_close
        next_open = today_open + timedelta(days=1)
    elif local_time_of_day < opens:
        next_open = today_open
        next_close = today_close
    else:
        next_open = today_open + timedelta(days=1)
        next_close = today_close + timedelta(days=1)

    return SessionStatus(
        id=session_id,
        label=label,
        timezone=zone_name,
        is_open=is_open,
        local_time=local_now,
        next_open_utc=next_open.astimezone(ZoneInfo("UTC")),
        next_close_utc=next_close.astimezone(ZoneInfo("UTC")),
    )


def _world_clock_entry(label: str, zone_name: str, now_utc: datetime) -> WorldClockEntry:
    zone = ZoneInfo(zone_name)
    local_now = now_utc.astimezone(zone)
    offset = local_now.utcoffset() or timedelta(0)
    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    hours, minutes = divmod(abs(total_minutes), 60)
    return WorldClockEntry(
        label=label,
        timezone=zone_name,
        local_time=local_now,
        utc_offset=f"UTC{sign}{hours:02d}:{minutes:02d}",
    )
