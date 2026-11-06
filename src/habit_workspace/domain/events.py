"""One authoritative event interval, interpreted in its saved IANA zone."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from habit_workspace.domain.documents import (
    DocumentError,
    civil_date,
    mapping,
    require,
    timestamp,
    uuid_value,
)
from habit_workspace.domain.habits import normalize_tags


@dataclass(frozen=True)
class Timed:
    timezone: str
    starts_at: datetime
    ends_at: datetime


@dataclass(frozen=True)
class AllDay:
    timezone: str
    start_date: date
    end_date_exclusive: date


@dataclass(frozen=True)
class Event:
    id: UUID
    title: str
    timing: Timed | AllDay
    tags: tuple[str, ...]
    origin_page_id: UUID | None

    def intersects_day(self, day: date) -> bool:
        t = self.timing
        if isinstance(t, AllDay):
            return t.start_date <= day < t.end_date_exclusive
        zone = ZoneInfo(t.timezone)
        start = datetime.combine(day, time(), zone).astimezone(UTC)
        end = datetime.combine(day + timedelta(days=1), time(), zone).astimezone(UTC)
        return (
            start < end and t.starts_at.astimezone(UTC) < end and t.ends_at.astimezone(UTC) > start
        )


def event_from_mapping(hw: dict) -> Event:
    require(hw.get("kind") == "event", "Expected event")
    require(isinstance(hw.get("title"), str) and bool(hw["title"].strip()), "Event needs title")
    require("recurrence" not in hw, "Event recurrence is unsupported")
    require(
        not {"starts_at", "ends_at", "start_date", "end_date_exclusive", "timezone", "all_day"}
        & hw.keys(),
        "Event timing belongs only in timing",
    )
    t = mapping(hw.get("timing"), "timing")
    zone_name = t.get("timezone")
    require(isinstance(zone_name, str) and bool(zone_name), "IANA timezone required")
    try:
        zone = ZoneInfo(zone_name)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise DocumentError("Unknown IANA timezone") from error
    require("recurrence" not in t, "Event recurrence is unsupported")
    if t.get("kind") == "timed":
        require(not {"start_date", "end_date_exclusive"} & t.keys(), "Mixed timing authorities")
        start, end = (timestamp(t.get(k), k) for k in ("starts_at", "ends_at"))
        for value in (start, end):
            local = value.astimezone(zone)
            require(
                local.replace(tzinfo=None) == value.replace(tzinfo=None)
                and local.utcoffset() == value.utcoffset(),
                "Offset or local time does not match IANA zone",
            )
        require(end.astimezone(UTC) > start.astimezone(UTC), "Event end must follow start instant")
        timing = Timed(zone_name, start, end)
    else:
        require(t.get("kind") == "all_day", "Unsupported timing kind")
        require(not {"starts_at", "ends_at"} & t.keys(), "Mixed timing authorities")
        start, end = (civil_date(t.get(k), k) for k in ("start_date", "end_date_exclusive"))
        require(end > start, "All-day end must follow start")
        timing = AllDay(zone_name, start, end)
    tags = hw.get("tags", [])
    require(isinstance(tags, list) and all(isinstance(tag, str) for tag in tags), "Invalid tags")
    return Event(
        uuid_value(hw.get("id"), "id"),
        hw["title"],
        timing,
        normalize_tags(tuple(tags)),
        uuid_value(hw["origin_page_id"], "origin_page_id") if hw.get("origin_page_id") else None,
    )


def local_candidates(wall: datetime, timezone: str) -> tuple[datetime, ...]:
    """Valid instants for a naive wall time, ordered by UTC, with folds explicit."""
    require(isinstance(wall, datetime) and wall.tzinfo is None, "Expected a local wall time")
    try:
        zone = ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError, TypeError) as error:
        raise DocumentError("Escolha um fuso IANA válido.") from error
    candidates = {}
    for fold in (0, 1):
        value = wall.replace(tzinfo=zone, fold=fold)
        instant = value.astimezone(UTC)
        if instant.astimezone(zone).replace(tzinfo=None) == wall:
            candidates[instant] = value
    return tuple(candidates[key] for key in sorted(candidates))


def resolve_local(wall: datetime, timezone: str, choice: str = "") -> datetime:
    """Never normalize a gap or silently pick a fold; choices are exact candidates."""
    candidates = local_candidates(wall, timezone)
    require(
        bool(candidates),
        "Este horário não existe neste fuso devido à mudança de horário. Escolha outro horário.",
    )
    if len(candidates) == 1:
        return candidates[0]
    for candidate in candidates:
        if candidate.isoformat() == choice:
            return candidate
    raise DocumentError(
        "Este horário ocorre duas vezes neste fuso. Escolha a primeira ou a segunda ocorrência."
    )
