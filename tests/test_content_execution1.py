from copy import deepcopy
from datetime import date

import pytest

from habit_workspace.application.content import ContentService, regions, replace_region
from habit_workspace.application.planning import PlanningService, query_report
from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.temporal import PeriodRef
from habit_workspace.vault.atomic_io import ConflictError

A = "4484184e-42fd-4624-a23a-e19606c08955"
B = "5484184e-42fd-4624-a23a-e19606c08955"


def test_regions_preserve_surroundings():
    body = (
        f'Before\n<!-- hw:content id="{A}" -->one<!-- /hw:content -->\n'
        f'<!-- hw:content id="{B}" -->two<!-- /hw:content -->End'
    )
    assert regions(body)[A][2] == "one"
    assert replace_region(body, A, "NEW") == body.replace(">one<", ">NEW<")
    for bad in (
        body + "<!-- /hw:content -->",
        body + f'<!-- hw:content id="{A}" -->x<!-- /hw:content -->',
        "<!-- hw:content broken -->",
        (
            f'<!-- hw:content id="{A}" --><!-- hw:content id="{B}" -->'
            "<!-- /hw:content --><!-- /hw:content -->"
        ),
    ):
        with pytest.raises(ValueError):
            replace_region(bad, A, "unsafe")
    with pytest.raises(ValueError):
        replace_region("", A, "missing")


def test_large_note_roundtrip_conflict_rebuild(tmp_path):
    s = VaultSession.create(tmp_path / "vault", "Test")
    service = ContentService(s)
    note = service.create("Note", "a" * 9000, "week/2026-W53")
    doc = deepcopy(note.document)
    doc.bom, doc.newline = True, "\r\n"
    doc.metadata["custom"] = {"keep": True}
    note = s.save(note, doc)
    note = service.save(note, "Edited", "b" * 12000, "week/2026-W53")
    assert note.path.read_bytes().startswith(b"\xef\xbb\xbf")
    assert b"\r\n" in note.path.read_bytes()
    s.index.path.unlink()
    reopened = VaultSession.open(s.root).load(note.document.id)
    assert reopened.document.body == "b" * 12000
    assert reopened.document.metadata["custom"] == {"keep": True}
    note.path.write_bytes(note.path.read_bytes() + b"external")
    with pytest.raises(ConflictError):
        service.save(note, "Mine", "draft", "")


@pytest.mark.parametrize("cadence", ["month", "week", "day"])
def test_followups(tmp_path, cadence):
    s = VaultSession.create(tmp_path / "vault", "Test")
    service = PlanningService(s)
    goal = service.create(
        kind="goal",
        title="Annual",
        period=PeriodRef("year/2026"),
        tracking={"mode": "periodic", "granularity": cadence},
    )
    period = PeriodRef.containing(cadence, date(2026, 10, 29))
    rows = query_report(s.report, period, date(2026, 10, 29))
    assert rows[0]["followup_period"] == str(period)
    goal = service.followup(goal, period, "Historical commentary")
    identifier = goal.document.metadata["hw"]["followups"][0]["id"]
    goal = service.update(goal, tracking={"mode": "home_only"})
    goal = service.followup(goal, period, "Corrected history")
    assert goal.document.metadata["hw"]["followups"][0]["id"] == identifier
    assert goal.document.metadata["hw"].get("progress_percent") is None
    assert len(s.report.documents) == 1
    s.index.path.unlink()
    assert (
        VaultSession.open(s.root)
        .load(goal.document.id)
        .document.metadata["hw"]["followups"][0]["commentary"]
        == "Corrected history"
    )


@pytest.mark.parametrize(
    "home,cadence",
    [("day/2026-10-29", "day"), ("week/2026-W44", "month"), ("month/2026-10", "month")],
)
def test_invalid_cadence(tmp_path, home, cadence):
    s = VaultSession.create(tmp_path / "vault", "Test")
    with pytest.raises(ValueError):
        PlanningService(s).create(
            kind="goal",
            title="Invalid",
            period=PeriodRef(home),
            tracking={"mode": "periodic", "granularity": cadence},
        )
    assert not s.scan().documents


def test_note_async_draft_conflict_and_region(tmp_path):
    from PySide6.QtCore import QCoreApplication, QSettings
    from test_vault_tasks import wait

    from habit_workspace.presentation.controllers import WorkspaceController

    QCoreApplication.instance() or QCoreApplication([])
    w = WorkspaceController(settings=QSettings(str(tmp_path / "prefs"), QSettings.IniFormat))
    assert w.createVault(str(tmp_path / "vault"), "Content")
    try:
        w.content.create()
        w.content.save(dict(title="", body="keep draft"))
        wait(lambda: not w.actions.busy)
        assert w.content.form["body"] == "keep draft" and w.content.form["error"]
        w.content.save(dict(title="Saved"))
        wait(lambda: not w.actions.busy)
        note = next(d for d in w.session.report.documents if d.document.kind == "note")
        w.content.edit(str(note.document.id))
        note.path.write_bytes(note.path.read_bytes() + b"external")
        w.content.save(dict(body="my unsaved draft"))
        wait(lambda: not w.actions.busy)
        assert w.content.form["body"] == "my unsaved draft"
        assert w.content.form["error"] and b"external" in note.path.read_bytes()
    finally:
        w.close()


@pytest.mark.parametrize(
    "home,cadences",
    [
        ("year/2026", ("month", "week", "day")),
        ("month/2026-10", ("week", "day")),
        ("week/2026-W44", ("day",)),
    ],
)
def test_valid_cadences_only_project_selected_scale(tmp_path, home, cadences):
    for i, cadence in enumerate(cadences):
        s = VaultSession.create(tmp_path / str(i), "Cadence")
        service = PlanningService(s)
        goal = service.create(
            kind="goal",
            title="Goal",
            period=PeriodRef(home),
            tracking={"mode": "periodic", "granularity": cadence},
        )
        for scale in ("month", "week", "day"):
            period = PeriodRef.containing(scale, date(2026, 10, 29))
            rows = query_report(s.report, period, date(2026, 10, 29))
            assert bool(rows) == (str(period) == home or scale == cadence)
        outside = PeriodRef.containing(cadence, date(2027, 3, 1))
        with pytest.raises(ValueError):
            service.followup(goal, outside, "Outside")
        before = goal.path.read_bytes()
        saved = service.followup(goal, PeriodRef.containing(cadence, date(2026, 10, 29)), "Saved")
        with pytest.raises(ConflictError):
            service.followup(goal, PeriodRef.containing(cadence, date(2026, 10, 29)), "Stale")
        assert saved.path.read_bytes() != before


def test_region_save_and_conflict_preserve_other_regions(tmp_path):
    from uuid import uuid4

    from habit_workspace.domain.documents import Document

    s = VaultSession.create(tmp_path / "vault", "Regions")
    body = (
        f'Before\r\n<!-- hw:content id="{A}" -->one<!-- /hw:content -->'
        f'\r\n<!-- hw:content id="{B}" -->two<!-- /hw:content -->After'
    )
    doc = Document.from_metadata(
        {
            "hw": {
                "schema_version": 4,
                "kind": "week_page",
                "id": str(uuid4()),
                "period": "week/2026-W44",
            },
            "custom": True,
        },
        body,
    )
    doc.bom, doc.newline = True, "\r\n"
    page = s.create_document("Pages/test.md", doc)
    saved = ContentService(s).save(page, "", "NEW\nLINE", region=A)
    assert saved.document.body == body.replace("one", "NEW\r\nLINE")
    assert saved.document.metadata["custom"]
    with pytest.raises(ConflictError):
        ContentService(s).save(page, "", "stale", region=A)


def test_week_boundary_and_unknown_tracking_extensions(tmp_path):
    s = VaultSession.create(tmp_path / "vault", "Boundary")
    service = PlanningService(s)
    goal = service.create(
        kind="goal",
        title="Monthly",
        period=PeriodRef("month/2026-10"),
        tracking={"mode": "periodic", "granularity": "week", "custom": "keep"},
    )
    week = PeriodRef("week/2026-W44")
    row = query_report(s.report, week, date(2026, 10, 29))[0]
    assert row["scope"] == "2026-10-26 → 2026-10-31 (inclusivo)"
    goal = service.followup(goal, week, "Week crosses month boundary")
    goal = service.update(goal, tracking={"mode": "home_only"})
    assert goal.document.metadata["hw"]["tracking"] == {"mode": "home_only", "custom": "keep"}
    assert len(goal.document.metadata["hw"]["followups"]) == 1
