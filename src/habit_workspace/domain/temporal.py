"""Civil calendar identities and half-open validity intervals, independent of Qt/paths."""

import calendar
import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum
from functools import total_ordering


class PeriodScale(StrEnum):
    YEAR = "year"
    MONTH = "month"
    WEEK = "week"
    DAY = "day"


def _date(value: date) -> None:
    if type(value) is not date:
        raise ValueError("Expected a civil date, not a timestamp or string")


def _next_day(value: date) -> date:
    try:
        return value + timedelta(days=1)
    except OverflowError as error:
        raise ValueError("Exclusive boundary exceeds Python's civil date range") from error


@total_ordering
@dataclass(frozen=True)
class PeriodRef:
    """Canonical identifier. Ordering is by start, end, then identifier (not nesting)."""

    identifier: str

    def __post_init__(self) -> None:
        value = self.identifier
        if not isinstance(value, str) or not re.fullmatch(
            r"(?:year/[0-9]{4}|month/[0-9]{4}-[0-9]{2}|"
            r"week/[0-9]{4}-W[0-9]{2}|day/[0-9]{4}-[0-9]{2}-[0-9]{2})",
            value,
        ):
            raise ValueError(f"Invalid period identifier: {value!r}")
        # The calendar validates leap days and the actual week count of the ISO year.
        _ = self.start

    @classmethod
    def parse(cls, identifier: str) -> PeriodRef:
        return cls(identifier)

    @classmethod
    def containing(cls, scale: PeriodScale | str, value: date) -> PeriodRef:
        _date(value)
        match PeriodScale(scale):
            case PeriodScale.YEAR:
                identifier = f"year/{value.year:04}"
            case PeriodScale.MONTH:
                identifier = f"month/{value.year:04}-{value.month:02}"
            case PeriodScale.WEEK:
                year, week, _ = value.isocalendar()
                identifier = f"week/{year:04}-W{week:02}"
            case PeriodScale.DAY:
                identifier = f"day/{value.isoformat()}"
        return cls(identifier)

    def __str__(self) -> str:
        return self.identifier

    @property
    def scale(self) -> PeriodScale:
        return PeriodScale(self.identifier.split("/", 1)[0])

    @property
    def start(self) -> date:
        value = self.identifier.split("/", 1)[1]
        match self.scale:
            case PeriodScale.YEAR:
                return date(int(value), 1, 1)
            case PeriodScale.MONTH:
                return date(int(value[:4]), int(value[-2:]), 1)
            case PeriodScale.WEEK:
                return date.fromisocalendar(int(value[:4]), int(value[-2:]), 1)
            case PeriodScale.DAY:
                return date.fromisoformat(value)

    @property
    def end(self) -> date:
        """Inclusive boundary for display; domain intervals use end_exclusive."""
        start = self.start
        match self.scale:
            case PeriodScale.YEAR:
                return date(start.year, 12, 31)
            case PeriodScale.MONTH:
                return start.replace(day=calendar.monthrange(start.year, start.month)[1])
            case PeriodScale.WEEK:
                try:
                    return start + timedelta(days=6)
                except OverflowError as error:
                    raise ValueError("Week exceeds Python's civil date range") from error
            case PeriodScale.DAY:
                return start

    @property
    def end_exclusive(self) -> date:
        return _next_day(self.end)

    @property
    def scope(self) -> TemporalScope:
        return TemporalScope.from_period(self)

    def intersects(self, other: PeriodRef) -> bool:
        return self.intersection(other) is not None

    def intersection(self, other: PeriodRef) -> TemporalScope | None:
        return self.scope.intersection(other.scope)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, PeriodRef):
            return NotImplemented
        return (self.start, self.end, self.identifier) < (other.start, other.end, other.identifier)


@dataclass(frozen=True)
class TemporalScope:
    """[start, end_exclusive); None is open-ended. Empty intervals are invalid."""

    start: date
    end_exclusive: date | None = None

    def __post_init__(self) -> None:
        _date(self.start)
        if self.end_exclusive is not None:
            _date(self.end_exclusive)
            if self.end_exclusive <= self.start:
                raise ValueError("end_exclusive must follow start")

    @classmethod
    def from_period(cls, period: PeriodRef) -> TemporalScope:
        return cls(period.start, period.end_exclusive)

    @classmethod
    def from_inclusive(cls, start: date, end: date) -> TemporalScope:
        _date(end)
        return cls(start, _next_day(end))

    def contains(self, value: date) -> bool:
        _date(value)
        return self.start <= value and (self.end_exclusive is None or value < self.end_exclusive)

    def intersection(self, other: TemporalScope) -> TemporalScope | None:
        start = max(self.start, other.start)
        ends = [end for end in (self.end_exclusive, other.end_exclusive) if end is not None]
        end = min(ends) if ends else None
        return None if end is not None and end <= start else TemporalScope(start, end)

    def intersects(self, other: TemporalScope) -> bool:
        return self.intersection(other) is not None


class RecurrenceKind(StrEnum):
    DAILY = "daily"
    WEEKDAYS = "weekdays"


@dataclass(frozen=True)
class Recurrence:
    kind: RecurrenceKind
    days: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", RecurrenceKind(self.kind))
        if not isinstance(self.days, tuple):
            raise ValueError("Recurrence days must be an immutable tuple")
        if self.kind == RecurrenceKind.DAILY:
            if self.days:
                raise ValueError("Daily recurrence does not select weekdays")
        elif (
            not self.days
            or any(type(day) is not int or not 1 <= day <= 7 for day in self.days)
            or len(set(self.days)) != len(self.days)
        ):
            raise ValueError("Weekdays must be unique integers 1–7")
        object.__setattr__(self, "days", tuple(sorted(self.days)))

    @classmethod
    def daily(cls) -> Recurrence:
        return cls(RecurrenceKind.DAILY)

    @classmethod
    def weekdays(cls, days: tuple[int, ...]) -> Recurrence:
        return cls(RecurrenceKind.WEEKDAYS, days)

    def matches(self, value: date) -> bool:
        _date(value)
        return self.kind == RecurrenceKind.DAILY or value.isoweekday() in self.days

    def occurrences(self, interval: TemporalScope, scope: TemporalScope) -> Iterator[date]:
        """Require a finite query, clip first, then lazily jump to matching weekdays."""
        if interval.end_exclusive is None:
            raise ValueError("Occurrence queries require a bounded interval")
        clipped = interval.intersection(scope)
        if clipped is None:
            return iter(())
        return self._dates(clipped)

    def _dates(self, interval: TemporalScope) -> Iterator[date]:
        current = interval.start.toordinal()
        stop = interval.end_exclusive.toordinal()
        while current < stop:
            value = date.fromordinal(current)
            if self.kind == RecurrenceKind.WEEKDAYS:
                current += min((day - value.isoweekday()) % 7 for day in self.days)
                if current >= stop:
                    break
            yield date.fromordinal(current)
            current += 1
