"""Pure temporal contracts: identities, half-open scopes and bounded schedules."""

from datetime import date, datetime
from itertools import islice

import pytest

from habit_workspace.domain.temporal import PeriodRef, Recurrence, TemporalScope


@pytest.mark.parametrize(
    "identifier,start,end",
    [
        ("year/2026", "2026-01-01", "2027-01-01"),
        ("month/2024-02", "2024-02-01", "2024-03-01"),
        ("month/2026-12", "2026-12-01", "2027-01-01"),
        ("week/2026-W44", "2026-10-26", "2026-11-02"),
        ("week/2026-W53", "2026-12-28", "2027-01-04"),
        ("week/2020-W01", "2019-12-30", "2020-01-06"),
        ("day/2024-02-29", "2024-02-29", "2024-03-01"),
        ("day/2026-10-27", "2026-10-27", "2026-10-28"),
    ],
)
def test_period_boundaries_and_default_scopes(identifier, start, end):
    period = PeriodRef.parse(identifier)
    assert str(period) == identifier
    assert period.start == date.fromisoformat(start)
    assert period.end_exclusive == date.fromisoformat(end)
    assert TemporalScope.from_period(period) == TemporalScope(period.start, period.end_exclusive)
    assert PeriodRef.containing(period.scale, period.start) == period


@pytest.mark.parametrize(
    "identifier",
    [
        "year/0000",
        "year/26",
        "year/10000",
        "month/2026-13",
        "month/2026-1",
        "day/2026-02-29",
        "day/2026-04-31",
        "day/20261027",
        "day/2026-10-27T00:00:00",
        "week/2025-W53",
        "week/2026-W00",
        "week/2026-W54",
        "week/2026-W4",
        "week/2026-w44",
        "quarter/2026-01",
        "2026-10-27",
        " day/2026-10-27",
        None,
        2026,
    ],
)
def test_invalid_identifiers(identifier):
    with pytest.raises(ValueError):
        PeriodRef.parse(identifier)


def test_period_identity_order_and_intersection():
    week = PeriodRef.parse("week/2026-W44")
    october = PeriodRef.parse("month/2026-10")
    november = PeriodRef.parse("month/2026-11")
    assert week == PeriodRef.containing("week", date(2026, 11, 1))
    assert week.intersection(october) == TemporalScope(date(2026, 10, 26), date(2026, 11, 1))
    assert week.intersection(november) == TemporalScope(date(2026, 11, 1), date(2026, 11, 2))
    assert not october.intersects(november)
    assert october < november
    assert len({week, PeriodRef.containing("week", date(2026, 10, 29))}) == 1


def test_scope_intersections_and_inclusive_adapter():
    scope = TemporalScope.from_inclusive(date(2026, 10, 27), date(2026, 12, 31))
    assert scope.end_exclusive == date(2027, 1, 1)
    assert scope.contains(date(2026, 12, 31))
    assert not scope.contains(date(2027, 1, 1))
    opened = TemporalScope(date(2026, 11, 1))
    assert opened.contains(date(2099, 1, 1))
    assert scope.intersection(opened) == TemporalScope(date(2026, 11, 1), date(2027, 1, 1))
    assert opened.intersection(TemporalScope(date(2027, 1, 1))).end_exclusive is None
    assert not scope.intersects(TemporalScope(date(2027, 1, 1)))


@pytest.mark.parametrize(
    "start,end",
    [
        (date(2026, 1, 1), date(2026, 1, 1)),
        (date(2026, 2, 1), date(2026, 1, 1)),
        ("2026-01-01", None),
        (datetime(2026, 1, 1), None),
    ],
)
def test_invalid_scope(start, end):
    with pytest.raises(ValueError):
        TemporalScope(start, end)


def test_daily_and_selected_weekdays_clipped_to_scope():
    period = PeriodRef.parse("week/2026-W44")
    scope = TemporalScope.from_inclusive(date(2026, 10, 27), date(2026, 12, 31))
    assert list(Recurrence.daily().occurrences(period.scope, scope)) == [
        date(2026, 10, d) for d in range(27, 32)
    ] + [date(2026, 11, 1)]
    weekdays = Recurrence.weekdays((1, 2, 3, 4, 5))
    assert list(weekdays.occurrences(period.scope, scope)) == [
        date(2026, 10, d) for d in range(27, 31)
    ]
    assert list(Recurrence.weekdays((7,)).occurrences(period.scope, scope)) == [date(2026, 11, 1)]
    assert list(weekdays.occurrences(PeriodRef.parse("month/2027-01").scope, scope)) == []


def test_finite_lazy_queries_for_open_scope():
    recurrence = Recurrence.daily()
    scope = TemporalScope(date(1, 1, 1))
    with pytest.raises(ValueError, match="bounded"):
        recurrence.occurrences(scope, scope)
    large = TemporalScope(date(1, 1, 1), date(9999, 12, 31))
    assert list(islice(recurrence.occurrences(large, scope), 2)) == [date(1, 1, 1), date(1, 1, 2)]


@pytest.mark.parametrize("days", [(), (0,), (8,), (True,), (1, 1), ("1",)])
def test_invalid_weekdays(days):
    with pytest.raises(ValueError):
        Recurrence.weekdays(days)


@pytest.mark.parametrize("identifier", ["year/2024", "month/2024-02", "week/2026-W53"])
def test_recurrence_counts_for_leap_and_iso_boundaries(identifier):
    period = PeriodRef.parse(identifier)
    dates = list(Recurrence.daily().occurrences(period.scope, period.scope))
    assert len(dates) == (period.end_exclusive - period.start).days
    assert dates[0] == period.start and dates[-1] == period.end
    assert len(dates) == {"year/2024": 366, "month/2024-02": 29, "week/2026-W53": 7}[identifier]


def test_representable_date_limits_are_explicit():
    assert PeriodRef.parse("year/0001").start == date.min
    # These valid existing documents stay readable; a year-10000 boundary cannot
    # be represented by Python date or serialized in the established file format.
    period = PeriodRef.parse("day/9999-12-31")
    assert period.start == date.max
    with pytest.raises(ValueError, match="boundary"):
        _ = period.scope
    with pytest.raises(ValueError, match="boundary"):
        TemporalScope.from_inclusive(date.max, date.max)
