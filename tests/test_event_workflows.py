"""Event wall-time resolution and canonical agenda/navigation acceptance."""

from datetime import UTC, date, datetime
from time import monotonic

import pytest
from PySide6.QtCore import QCoreApplication, QSettings
from PySide6.QtTest import QTest

from habit_workspace.application.agenda import agenda_groups, agenda_rows
from habit_workspace.application.events import EventService
from habit_workspace.application.habits import HabitService
from habit_workspace.application.planning import PlanningService
from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.events import local_candidates, resolve_local
from habit_workspace.domain.temporal import PeriodRef
from habit_workspace.presentation.controllers import WorkspaceController


def test_gap_fold_and_normal_wall_times():
    assert not local_candidates(datetime(2026, 3, 8, 2, 30), "America/New_York")
    with pytest.raises(ValueError, match="não existe"):
        resolve_local(datetime(2026, 3, 8, 2, 30), "America/New_York")
    values = local_candidates(datetime(2026, 11, 1, 1, 30), "America/New_York")
    assert [v.astimezone(UTC).hour for v in values] == [5, 6]
    with pytest.raises(ValueError, match="duas vezes"):
        resolve_local(datetime(2026, 11, 1, 1, 30), "America/New_York")
    assert (
        resolve_local(datetime(2026, 11, 1, 1, 30), "America/New_York", values[1].isoformat())
        == values[1]
    )
    assert len(local_candidates(datetime(2026, 11, 2, 12), "America/New_York")) == 1
    with pytest.raises(ValueError):
        resolve_local(datetime(2026, 11, 2, 12), "Invalid/Zone")
    with pytest.raises(ValueError):
        resolve_local(datetime(2026, 11, 1, 1, 30), "America/New_York", "stale choice")


def test_half_hour_fold_and_skipped_civil_day():
    values = local_candidates(datetime(2026, 4, 5, 1, 45), "Australia/Lord_Howe")
    assert len(values) == 2
    assert (values[1].astimezone(UTC) - values[0].astimezone(UTC)).total_seconds() == 1800
    assert not local_candidates(datetime(2011, 12, 30, 12), "Pacific/Apia")


@pytest.fixture
def workspace(tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    w = WorkspaceController(
        today=date(2026, 11, 3), settings=QSettings(str(tmp_path / "prefs"), QSettings.IniFormat)
    )
    w.createVault(str(tmp_path / "vault"), "Events")
    yield w
    w.close()
    app.processEvents()


def saved(w):
    deadline = monotonic() + 10
    while w.actions.busy and monotonic() < deadline:
        QCoreApplication.processEvents()
        QTest.qWait(5)
    QCoreApplication.processEvents()
    assert not w.actions.busy


def test_timezone_draft_fold_persistence_and_conflicts(workspace):
    w = workspace
    w.events.create()
    w.events.save(
        dict(
            title="DST draft",
            timezone="America/New_York",
            start="08/03/2026",
            end="08/03/2026",
            startTime="02:30",
            endTime="04:00",
        )
    )
    assert w.events.form["title"] == "DST draft"
    assert "não existe" in w.events.form["error"]
    assert not w.session.report.documents
    w.events.save(dict(start="01/11/2026", end="01/11/2026", startTime="01:30", endTime="02:30"))
    assert "duas vezes" in w.events.form["error"]
    choices = w.events.wallOptions("01/11/2026", "01:30", "America/New_York")
    assert len(choices) == 2
    w.events.save(dict(startChoice=choices[1]["value"]))
    saved(w)
    assert not w.events.form
    loaded = w.session.report.documents[0]
    assert loaded.document.metadata["hw"]["timing"]["starts_at"].endswith("-05:00")
    w.events.open("event", str(loaded.document.id))
    assert w.events.form["timezone"] == "America/New_York"
    assert w.events.form["startChoice"] == choices[1]["value"]
    loaded.path.write_bytes(loaded.path.read_bytes() + b"\nExternal")
    external = loaded.path.read_bytes()
    w.events.save(dict(title="My conflict draft"))
    saved(w)
    assert w.events.form["title"] == "My conflict draft"
    assert "rascunho preservado" in w.events.form["error"]
    assert loaded.path.read_bytes() == external


def test_agenda_group_order_multiday_and_navigation(workspace):
    w = workspace
    s = w.session
    event = EventService(s).create(
        title="Overnight",
        timing=dict(
            kind="timed",
            timezone="America/Recife",
            starts_at="2026-12-31T23:00:00-03:00",
            ends_at="2027-01-01T02:00:00-03:00",
        ),
    )
    EventService(s).create(
        title="Conference",
        timing=dict(
            kind="all_day",
            timezone="America/Recife",
            start_date="2026-12-31",
            end_date_exclusive="2027-01-02",
        ),
    )
    task = PlanningService(s).create(
        kind="task", title="Deadline", period=PeriodRef("year/2025"), due_date=date(2027, 1, 1)
    )
    habit = HabitService(s).create(name="Read", period=PeriodRef("week/2026-W53"))
    rows = agenda_rows(s.report, PeriodRef("week/2026-W53"), date(2027, 1, 2))
    day = [r for r in rows if r["display_day"] == "2027-01-01"]
    assert [r["source_kind"] for r in day] == ["event", "event", "task", "habit"]
    assert day[0]["all_day"]
    assert "Continuação" in day[1]["time_label"]
    assert day[1]["end_time"] == "02:00"
    groups = agenda_groups(rows)
    assert "2027" in groups[-1]["label"]
    assert sum(len(g["rows"]) for g in groups) == len(rows)
    before = {d.path: d.path.read_bytes() for d in s.report.documents}
    w.events.openOccurrence("habit", str(habit.habit.id), "2027-01-01")
    assert w.state["period"] == "day/2027-01-01"
    assert w.capture_day == date(2027, 1, 1)
    assert w.state["selected"]["id"] == str(habit.habit.id)
    assert w.state["selected"]["habit"]["date"] == "2027-01-01"
    w.events.openOccurrence("task", str(task.document.id), "2027-01-01")
    assert w.planning.loaded.document.id == task.document.id
    w.planning.cancel()
    w.events.openOccurrence("event", str(event.document.id), "2026-12-31")
    assert w.events.loaded.document.id == event.document.id
    w.events.cancel()
    assert all(p.read_bytes() == data for p, data in before.items())
    s.index.path.unlink()
    reopened = VaultSession.open(s.root)
    assert agenda_rows(reopened.report, PeriodRef("week/2026-W53"), date(2027, 1, 2)) == rows


def test_missing_and_ambiguous_navigation(workspace):
    from uuid import uuid4

    w = workspace
    w.events.openOccurrence("habit", str(uuid4()), "2026-11-03")
    assert w.state["noticeError"]
    assert not w.session.report.documents
    item = EventService(w.session).create(
        title="One",
        timing=dict(
            kind="all_day", timezone="UTC", start_date="2026-11-03", end_date_exclusive="2026-11-04"
        ),
    )
    item.path.with_name("duplicate.md").write_bytes(item.path.read_bytes())
    w.session.scan()
    w.events.open("event", str(item.document.id))
    assert not w.events.form
    assert w.state["noticeError"]


def test_default_zone_correction_and_existing_zone_never_changes(workspace, monkeypatch):
    from types import SimpleNamespace

    import habit_workspace.presentation.events as events

    monkeypatch.setattr(
        events, "QTimeZone", SimpleNamespace(systemTimeZoneId=lambda: b"Europe/Lisbon")
    )
    w = workspace
    w.navigate("year", "2026-11-03")
    w.events.create()
    assert w.events.form["timezone"] == "Europe/Lisbon"
    assert w.events.form["start"] == w.events.form["end"] == "01/01/2026"
    assert "America/Recife" in w.events.zoneOptions("Recife")
    w.events.save(
        dict(
            title="Civil dates",
            allDay=True,
            start="31/12/2026",
            end="02/01/2027",
            timezone="Pacific/Apia",
        )
    )
    saved(w)
    loaded = w.session.report.documents[0]
    assert loaded.document.metadata["hw"]["timing"] == dict(
        kind="all_day",
        timezone="Pacific/Apia",
        start_date="2026-12-31",
        end_date_exclusive="2027-01-03",
    )
    w.events.open("event", str(loaded.document.id))
    assert w.events.form["timezone"] == "Pacific/Apia"
    w.events.cancel()
    monkeypatch.setattr(
        events, "QTimeZone", SimpleNamespace(systemTimeZoneId=lambda: b"Invalid/Zone")
    )
    w.events.create()
    assert w.events.form["timezone"] == "UTC"
    assert "não identificado" in w.events.form["zoneNotice"]


def test_pagination_navigation_no_files(workspace):
    w = workspace
    w.navigate("year", "2026-11-03")
    w.events.page(1)
    assert w.events.window()["label"] == "01/02/2026 a 03/03/2026"
    assert w.events.window()["previous"]
    w.navigate("week", "2027-01-01")
    assert w.state["period"] == "week/2026-W53"
    assert w.events.offset == 0
    w.navigate("month", "2027-01-01")
    assert w.events.offset == 0
    assert not w.session.report.documents


def test_missing_snapshot_is_disclosed_not_scheduled(workspace):
    from uuid import uuid4

    from habit_workspace.domain.documents import Document

    w = workspace
    identifier = str(uuid4())
    w.session.create_document(
        "day.md",
        Document.from_metadata(
            {
                "hw": dict(
                    schema_version=4,
                    kind="day_page",
                    id=str(uuid4()),
                    date="2026-11-03",
                    checkins=[
                        dict(
                            id=str(uuid4()),
                            habit_id=identifier,
                            date="2026-11-03",
                            state="done",
                            label_snapshot="Missing read",
                            recorded_at="2026-11-03T12:00:00-03:00",
                        )
                    ],
                )
            },
            "Saved snapshot",
        ),
    )
    rows = agenda_rows(w.session.report, PeriodRef("week/2026-W45"), date(2026, 11, 3))
    assert len(rows) == 1
    assert rows[0]["missing"] and rows[0]["status"] == "done"
    assert rows[0]["title"] == "Missing read"
    w.events.openOccurrence("habit", identifier, "2026-11-03")
    assert w.state["noticeError"]
    assert len(w.session.report.documents) == 1


def test_timed_chronology_midnight_and_moved_identity(workspace):
    w = workspace
    service = EventService(w.session)

    def create(title, start, end):
        return service.create(
            title=title,
            timing=dict(kind="timed", timezone="America/New_York", starts_at=start, ends_at=end),
        )

    later = create("Second fold", "2026-11-01T01:30:00-05:00", "2026-11-01T02:30:00-05:00")
    first = create("First fold", "2026-11-01T01:30:00-04:00", "2026-11-01T01:45:00-04:00")
    create("Ends midnight", "2026-10-31T23:00:00-04:00", "2026-11-01T00:00:00-04:00")
    rows = agenda_rows(w.session.report, PeriodRef("day/2026-11-01"), date(2026, 11, 3))
    assert [r["source_id"] for r in rows] == [str(first.document.id), str(later.document.id)]
    new_path = first.path.with_name("renamed-event.md")
    first.path.rename(new_path)
    w.session.scan()
    assert service.open(first.document.id).path == new_path
    assert agenda_rows(w.session.report, PeriodRef("day/2026-11-01"), date(2026, 11, 3)) == rows


def test_explicit_missed_and_conflicting_checkins_are_not_inferred(workspace):
    from copy import deepcopy
    from datetime import UTC, datetime

    from habit_workspace.application.capture import CaptureService

    w = workspace
    habit = HabitService(w.session).create(name="Read", period=PeriodRef("day/2026-11-03"))
    CaptureService(w.session).set_checkin(
        habit_id=habit.habit.id,
        day=date(2026, 11, 3),
        state="missed",
        today=date(2026, 11, 3),
        recorded_at=datetime(2026, 11, 3, 12, tzinfo=UTC),
    )
    rows = agenda_rows(w.session.report, PeriodRef("day/2026-11-03"), date(2026, 11, 3))
    assert rows[0]["status"] == "missed"
    day_page = next(d for d in w.session.report.documents if d.document.kind == "day_page")
    copy = deepcopy(day_page.document)
    from uuid import uuid4

    copy.metadata["hw"]["id"] = str(uuid4())
    w.session.create_document("other-day.md", copy)
    rows = agenda_rows(w.session.report, PeriodRef("day/2026-11-03"), date(2026, 11, 3))
    assert len(rows) == 1 and rows[0]["conflict"]
    assert rows[0]["status"] == "conflict"
