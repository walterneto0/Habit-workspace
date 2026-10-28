"""Phase 2 virtual navigation contracts; no recurrence or layout resolver."""

from datetime import date

from habit_workspace.presentation.navigation import Navigation


def test_iso_week_identity_crosses_months_and_years():
    nav = Navigation(date(2027, 1, 1), "week")
    assert nav.period == "week/2026-W53"
    assert nav.start == date(2026, 12, 28)
    assert nav.end == date(2027, 1, 3)
    nav.move(1)
    assert nav.period == "week/2027-W01"
    nav = Navigation(date(2026, 10, 29), "week")
    assert nav.period == "week/2026-W44"
    assert nav.end == date(2026, 11, 1)


def test_month_clamping_leap_year_and_calendar_grid():
    nav = Navigation(date(2024, 1, 31), "month")
    nav.move(1)
    assert nav.anchor == date(2024, 2, 29)
    cells = nav.calendar()
    assert len(cells) == 42
    assert date.fromisoformat(cells[0]["date"]).weekday() == 0
    assert sum(c["inMonth"] for c in cells) == 29
    nav.move(12)
    assert nav.anchor == date(2025, 2, 28)


def test_drilldown_and_bounds():
    nav = Navigation(date(2026, 10, 29), "year")
    assert len(nav.children()) == 12
    nav.select("month", "2026-11-01")
    assert nav.period == "month/2026-11"
    nav.select("day", "2026-11-01")
    assert nav.period == "day/2026-11-01"
    assert nav.breadcrumbs()[-2]["period"] == "week/2026-W44"
