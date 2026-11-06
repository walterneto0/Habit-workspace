from copy import deepcopy
from datetime import date

import pytest

from habit_workspace.application.agenda import agenda_rows
from habit_workspace.application.events import EventService
from habit_workspace.application.planning import PlanningService
from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.documents import DocumentError
from habit_workspace.domain.events import event_from_mapping
from habit_workspace.domain.temporal import PeriodRef
from habit_workspace.vault.atomic_io import ConflictError


def timed(**changes):
    return (
        dict(
            kind="timed",
            timezone="America/New_York",
            starts_at="2026-11-01T01:45:00-04:00",
            ends_at="2026-11-01T01:15:00-05:00",
        )
        | changes
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"timezone": "Invalid/Zone"},
        {"starts_at": "2026-03-08T02:30:00-05:00"},
        {"starts_at": "2026-11-01T01:45:00"},
        {"ends_at": "2026-11-01T00:00:00-04:00"},
        {"start_date": "2026-11-01"},
        {"kind": "weekly"},
        {"recurrence": {}},
        {"starts_at": "bad"},
        {"timezone": None},
    ],
)
def test_invalid_timing(tmp_path, changes):
    s = EventService(VaultSession.create(tmp_path / "v", "Test"))
    with pytest.raises(DocumentError):
        s.create(title="Event", timing=timed(**changes))


def test_dst_roundtrip_revisions_rebuild(tmp_path):
    session = VaultSession.create(tmp_path / "v", "Test")
    service = EventService(session)
    event = service.create(title="DST", timing=timed(), body="Human notes", tags=(" Test ",))
    assert service.open(event.document.id).document.body == "Human notes"
    assert len(service.search("test")) == 1
    changed = deepcopy(event.document)
    changed.metadata["custom"] = {"keep": True}
    changed.metadata["hw"]["timing"]["custom"] = "keep"
    event = session.save(event, changed)
    updated = service.update(event, title="Edited", timing=timed(), body="New", tags=())
    assert updated.document.metadata["hw"]["timing"]["custom"] == "keep"
    with pytest.raises(ConflictError):
        service.update(event, title="stale", timing=timed(), body="", tags=())
    updated.path.write_bytes(updated.path.read_bytes() + b"\nexternal")
    with pytest.raises(ConflictError):
        service.update(updated, title="external", timing=timed(), body="", tags=())
    session.index.path.unlink()
    reopened = VaultSession.open(session.root)
    assert reopened.load(event.document.id).document.body.endswith("external")
    duplicate = updated.path.with_name("duplicate.md")
    duplicate.write_bytes(updated.path.read_bytes())
    with pytest.raises(ConflictError):
        EventService(reopened).open(event.document.id)


def test_midnight_all_day_and_cross_year(tmp_path):
    session = VaultSession.create(tmp_path / "v", "Test")
    service = EventService(session)
    event = service.create(
        title="Midnight",
        timing=timed(
            timezone="America/Recife",
            starts_at="2026-12-31T23:00:00-03:00",
            ends_at="2027-01-01T00:00:00-03:00",
        ),
    )
    obj = event_from_mapping(event.document.metadata["hw"])
    assert obj.intersects_day(date(2026, 12, 31))
    assert not obj.intersects_day(date(2027, 1, 1))
    service.create(
        title="All day",
        timing=dict(
            kind="all_day",
            timezone="America/Recife",
            start_date="2026-12-31",
            end_date_exclusive="2027-01-02",
        ),
    )
    PlanningService(session).create(
        kind="task", title="Deadline", period=PeriodRef("year/2025"), due_date=date(2027, 1, 1)
    )
    rows = agenda_rows(session.report, PeriodRef("week/2026-W53"), date(2027, 1, 2))
    assert len(rows) == 4
    assert sum(r["source_kind"] == "task" for r in rows) == 1
    assert len({r["source_id"] for r in rows}) == 3
    before = rows
    session.index.path.unlink()
    session = VaultSession.open(session.root)
    assert agenda_rows(session.report, PeriodRef("week/2026-W53"), date(2027, 1, 2)) == before


@pytest.mark.parametrize(
    "start,end",
    [("2026-02-29", "2026-03-01"), ("2026-01-01", "2026-01-01"), ("2026-01-02", "2026-01-01")],
)
def test_invalid_all_day(tmp_path, start, end):
    service = EventService(VaultSession.create(tmp_path / "v", "Test"))
    with pytest.raises(DocumentError):
        service.create(
            title="Invalid",
            timing=dict(kind="all_day", timezone="UTC", start_date=start, end_date_exclusive=end),
        )


def test_scheduled_habits_never_infer_missed(tmp_path):
    from habit_workspace.application.habits import HabitService
    from habit_workspace.domain.temporal import Recurrence, TemporalScope

    session = VaultSession.create(tmp_path / "v", "Test")
    HabitService(session).create(
        name="Read",
        period=PeriodRef("year/2026"),
        scope=TemporalScope(date(2026, 11, 2), date(2026, 11, 5)),
        recurrence=Recurrence.weekdays((1, 3)),
    )
    rows = agenda_rows(session.report, PeriodRef("month/2026-11"), date(2026, 11, 3))
    assert [(r["display_day"], r["status"]) for r in rows] == [
        ("2026-11-02", "unrecorded"),
        ("2026-11-04", "future"),
    ]
    assert len(session.report.documents) == 1
    with pytest.raises(ValueError):
        agenda_rows(session.report, PeriodRef("year/2026"), date(2026, 11, 3), window_days=366)
