"""Phase 6.5A: the local civil date follows midnight, suspend/resume and clock changes.

A ManualClock replaces waiting: tests jump it explicitly and call the controller's
date check, which the GUI runs from a timer and before each capture action.
"""

from datetime import date, datetime, timedelta

import pytest
from PySide6.QtCore import QCoreApplication, QSettings

from habit_workspace.application.habits import HabitService
from habit_workspace.domain.temporal import PeriodRef, TemporalScope
from habit_workspace.presentation.clock import ManualClock
from habit_workspace.presentation.controllers import WorkspaceController
from habit_workspace.vault.scanner import scan

DAY = date(2026, 10, 29)  # Thursday, ISO week 2026-W44.


def local(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute).astimezone()


@pytest.fixture
def clock():
    return ManualClock(local(DAY, 23, 59))


@pytest.fixture
def desktop(tmp_path, clock):
    app = QCoreApplication.instance() or QCoreApplication([])
    settings = QSettings(str(tmp_path / "prefs.ini"), QSettings.Format.IniFormat)
    controller = WorkspaceController(settings=settings, clock=clock)
    assert controller.createVault(str(tmp_path / "vault"), "Virada")
    HabitService(controller.session).create(
        name="Estudar Python",
        period=PeriodRef.containing("day", DAY),
        scope=TemporalScope(date(2026, 10, 1), None),
    )
    controller.session.scan()
    yield controller
    controller.close()
    app.processEvents()


def checkins(desktop):
    return {
        (r["date"], r["state"])
        for d in scan(desktop.session.root).documents
        for r in d.document.metadata["hw"].get("checkins", ())
    }


def test_date_check_is_scheduled_and_noop_without_change(desktop):
    assert desktop.date_timer.isActive()
    assert desktop.date_timer.interval() <= 60_000
    before = desktop.state
    assert not desktop.refreshDate()
    assert desktop.state is before


def test_midnight_moves_a_person_following_today(desktop, clock):
    desktop.navigate("day", DAY.isoformat())
    assert desktop.state["tracking"]["isToday"]
    assert [r["stateLabel"] for r in desktop.state["habits"]["rows"]] == [
        "Pendente hoje · sem registro"
    ]
    clock.set(local(DAY + timedelta(days=1), 0, 0))
    assert desktop.refreshDate()
    assert desktop.state["today"] == "2026-10-30"
    assert desktop.state["period"] == "day/2026-10-30"
    assert desktop.state["tracking"]["isToday"]
    assert not desktop.state["noticeError"]


def test_next_day_checkin_after_midnight_is_written_to_the_new_day(desktop, clock):
    desktop.navigate("day", DAY.isoformat())
    habit = desktop.state["habits"]["rows"][0]["id"]
    assert desktop.setCheckin(habit, "done", "null")
    clock.set(local(DAY + timedelta(days=1), 7, 30))
    desktop.refreshDate()
    assert desktop.setCheckin(habit, "done", "null"), desktop.state["notice"]
    assert checkins(desktop) == {("2026-10-29", "done"), ("2026-10-30", "done")}
    # The previous day remains intact and is no longer "today".
    desktop.navigate("day", DAY.isoformat())
    assert not desktop.state["tracking"]["isToday"]
    assert desktop.state["habits"]["rows"][0]["stateLabel"] == "Concluído"


def test_week_view_default_capture_day_follows_but_explicit_choice_is_kept(desktop, clock):
    desktop.navigate("week", DAY.isoformat())
    assert desktop.state["tracking"]["date"] == "2026-10-29"
    clock.set(local(DAY + timedelta(days=1), 0, 1))
    desktop.refreshDate()
    assert desktop.state["period"] == "week/2026-W44"
    assert desktop.state["tracking"]["date"] == "2026-10-30"
    desktop.setCaptureDate("2026-10-28")
    clock.set(local(DAY + timedelta(days=2), 0, 1))
    desktop.refreshDate()
    assert desktop.state["today"] == "2026-10-31"
    assert desktop.state["tracking"]["date"] == "2026-10-28"


def test_following_today_crosses_the_iso_week_boundary(desktop, clock):
    sunday = date(2026, 11, 1)
    clock.set(local(sunday, 23, 59))
    desktop.goToday()
    desktop.navigate("week")
    assert desktop.state["period"] == "week/2026-W44"
    clock.set(local(sunday + timedelta(days=1), 0, 0))
    desktop.refreshDate()
    assert desktop.state["period"] == "week/2026-W45"
    assert desktop.state["tracking"]["date"] == "2026-11-02"


def test_manual_historical_selection_is_not_navigated_away(desktop, clock):
    desktop.navigate("day", "2026-10-27")
    desktop.selectDocument(desktop.state["habits"]["rows"][0]["id"])
    clock.set(local(DAY + timedelta(days=1), 0, 0))
    assert desktop.refreshDate()
    assert desktop.state["period"] == "day/2026-10-27"
    assert desktop.state["selected"]
    assert "30 de outubro de 2026" in desktop.state["notice"]
    assert "Hoje" in desktop.state["notice"]
    assert desktop.state["habits"]["rows"][0]["stateLabel"] == "Sem registro (não é falha)"
    desktop.goToday()
    assert desktop.state["period"] == "day/2026-10-30"


def test_open_habit_form_keeps_its_period(desktop, clock):
    desktop.navigate("day", DAY.isoformat())
    desktop.newHabit()
    clock.set(local(DAY + timedelta(days=1), 0, 0))
    desktop.refreshDate()
    assert desktop.state["period"] == "day/2026-10-29"
    assert desktop.state["habitForm"]["start"] == "2026-10-29"
    assert desktop.state["today"] == "2026-10-30"


def test_resume_after_suspend_then_immediate_click_keeps_the_displayed_day(desktop, clock):
    desktop.navigate("day", DAY.isoformat())
    habit = desktop.state["habits"]["rows"][0]["id"]
    # Suspended overnight; the 30 s timer has not fired yet when the person clicks.
    clock.set(local(DAY + timedelta(days=2), 8, 0))
    assert desktop.setCheckin(habit, "done", "null"), desktop.state["notice"]
    assert checkins(desktop) == {("2026-10-29", "done")}
    assert "29 de outubro" in desktop.state["notice"]
    assert desktop.state["today"] == "2026-10-31"
    assert desktop.state["period"] == "day/2026-10-29"
    # The intermediate day is unrecorded, never inferred as missed.
    desktop.navigate("day", "2026-10-30")
    assert desktop.state["habits"]["rows"][0]["stateLabel"] == "Sem registro (não é falha)"


def test_resume_after_suspend_when_timer_fires_first_follows_today(desktop, clock):
    desktop.navigate("day", DAY.isoformat())
    clock.set(local(DAY + timedelta(days=3), 9, 0))
    desktop.refreshDate()
    assert desktop.state["period"] == "day/2026-11-01"
    assert desktop.state["habits"]["rows"][0]["stateLabel"] == "Pendente hoje · sem registro"


def test_clock_moving_backwards_is_handled_like_any_date_change(desktop, clock):
    desktop.navigate("day", DAY.isoformat())
    clock.set(local(DAY - timedelta(days=1), 22, 0))  # e.g. time-zone change westwards
    assert desktop.refreshDate()
    assert desktop.state["period"] == "day/2026-10-28"
    habit = desktop.state["habits"]["rows"][0]["id"]
    desktop.navigate("day", DAY.isoformat())
    assert not desktop.setCheckin(habit, "done", "null")
    assert "futuras" in desktop.state["notice"]
    assert checkins(desktop) == set()


def test_date_change_does_not_rescan_the_vault(desktop, clock, monkeypatch):
    desktop.navigate("day", DAY.isoformat())
    monkeypatch.setattr(desktop.session, "scan", lambda: pytest.fail("Unexpected rescan"))
    clock.set(local(DAY + timedelta(days=1), 0, 0))
    assert desktop.refreshDate()
    assert desktop.state["today"] == "2026-10-30"
