from copy import deepcopy
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from habit_workspace.application.imports import ImportService
from habit_workspace.application.planning import PlanningService, query_report
from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.temporal import PeriodRef
from habit_workspace.vault.atomic_io import ConflictError


def test_roundtrip_completion_conflict_and_rebuild(tmp_path):
    session = VaultSession.create(tmp_path / "vault", "Test")
    service = PlanningService(session)
    task = service.create(
        kind="task",
        title="Read",
        period=PeriodRef("week/2026-W44"),
        body="Human **Markdown**",
        due_date=date(2026, 11, 4),
    )
    doc = deepcopy(task.document)
    doc.metadata["custom"] = {"keep": True}
    doc.metadata["hw"]["scope"]["custom"] = "keep"
    task = session.save(task, doc)
    done = service.complete(task, True, datetime.now(UTC))
    assert done.document.body == "Human **Markdown**"
    assert done.document.metadata["hw"]["scope"]["custom"] == "keep"
    assert not any(d.document.kind == "day_page" for d in session.report.documents)
    with pytest.raises(ConflictError):
        service.complete(task, False, datetime.now(UTC))
    reopened = service.complete(done, False, datetime.now(UTC))
    assert reopened.document.metadata["hw"].get("completed_at") is None
    session.index.path.unlink()
    other = VaultSession.open(session.root)
    assert other.load(task.document.id).document.metadata["custom"]["keep"]
    result = ImportService(VaultSession.create(tmp_path / "other", "Other")).import_files(
        [task.path]
    )
    assert len(result.imported) == 1
    duplicate = task.path.with_name("duplicate.md")
    duplicate.write_bytes(task.path.read_bytes())
    with pytest.raises(ConflictError):
        service.complete(reopened, True, datetime.now(UTC))


def test_visibility_and_goal_independence(tmp_path):
    session = VaultSession.create(tmp_path / "vault", "Test")
    service = PlanningService(session)
    service.create(kind="task", title="Old", period=PeriodRef("day/2026-10-20"))
    goal = service.create(
        kind="goal",
        title="Annual",
        period=PeriodRef("year/2026"),
        progress_percent=100,
        status="paused",
    )
    for period in ("day/2026-10-29", "week/2026-W44", "month/2026-10", "year/2026"):
        rows = query_report(session.report, PeriodRef(period), date(2026, 10, 29))
        assert len({r["id"] for r in rows}) == len(rows)
        assert str(goal.document.id) in {r["id"] for r in rows}
    assert query_report(session.report, PeriodRef("day/2026-10-29"), date(2026, 10, 29))[0]
    past = query_report(session.report, PeriodRef("day/2026-10-21"), date(2026, 10, 29))
    assert all(r["title"] != "Old" for r in past)
    assert goal.document.metadata["hw"]["status"] == "paused"
    with pytest.raises(ValueError):
        service.create(
            kind="goal", title="Bad", period=PeriodRef("year/2026"), progress_percent=True
        )


def test_external_edit_and_identity(tmp_path):
    session = VaultSession.create(tmp_path / "vault", "Test")
    service = PlanningService(session)
    task = service.create(kind="task", title="Original", period=PeriodRef("day/2026-10-29"))
    task.path.write_text(task.path.read_text().replace("Original", "External"))
    with pytest.raises(ConflictError):
        service.update(task, title="Mine")
    assert "External" in task.path.read_text()
    moved = task.path.with_name(str(uuid4()) + ".md")
    task.path.rename(moved)
    assert session.load(task.document.id).path == moved


def test_task_layout_binding_and_missing_reference(tmp_path):
    from habit_workspace.application.capture import CaptureSnapshot
    from habit_workspace.domain.layouts.components import Binding, ChecklistConfig, Component
    from habit_workspace.domain.layouts.models import LayoutTemplate
    from habit_workspace.presentation.layout_studio import composition
    from habit_workspace.vault.layouts import decode_layout, encode_layout

    session = VaultSession.create(tmp_path / "vault", "Test")
    task = PlanningService(session).create(
        kind="task", title="Task", period=PeriodRef("week/2026-W44")
    )
    block = Component(
        uuid4(), "checklist", "Tasks", ChecklistConfig(), binding=Binding(task.document.id, "task")
    )
    layout = LayoutTemplate(uuid4(), 1, "Plan", (block,))
    assert decode_layout(encode_layout(layout)).layout == layout
    capture = CaptureSnapshot(session.report, date(2026, 10, 29), date(2026, 10, 29))
    assert capture.block(block) == []
    rows = composition(layout, session.report, capture=capture, period=PeriodRef("week/2026-W44"))
    assert rows[0]["planning"][0]["id"] == str(task.document.id)
    task.path.unlink()
    session.scan()
    rows = composition(layout, session.report, capture=capture, period=PeriodRef("week/2026-W44"))
    assert rows[0]["planning"][0]["conflict"]


@pytest.mark.parametrize(
    "kind,fields",
    [
        ("task", {"due_date": "2026-02-30"}),
        ("task", {"completed_at": "2026-10-29T12:00:00+00:00"}),
        ("task", {"status": "missed"}),
        ("goal", {"progress_percent": -1}),
        ("goal", {"progress_percent": 101}),
        ("goal", {"progress_percent": 2.5}),
        ("goal", {"status": "completed"}),
    ],
)
def test_invalid_schema_preserves_files(tmp_path, kind, fields):
    from habit_workspace.domain.documents import DocumentError

    session = VaultSession.create(tmp_path / "vault", "Test")
    with pytest.raises(DocumentError):
        PlanningService(session).create(
            kind=kind, title="Invalid", period=PeriodRef("day/2026-10-29"), **fields
        )
    assert not session.scan().documents


def test_malformed_scope_import_is_recoverable(tmp_path):
    session = VaultSession.create(tmp_path / "vault", "Test")
    task = PlanningService(session).create(
        kind="task", title="Bad", period=PeriodRef("day/2026-10-29")
    )
    raw = task.path.read_bytes().replace(b"2026-10-30", b"2026-10-20")
    task.path.write_bytes(raw)
    report = session.scan()
    assert report.invalid and task.path.read_bytes() == raw
    result = ImportService(VaultSession.create(tmp_path / "other", "Other")).import_files(
        [task.path]
    )
    assert result.invalid and task.path.read_bytes() == raw


def test_deadline_carryover_and_historical_visibility(tmp_path):
    session = VaultSession.create(tmp_path / "vault", "Test")
    service = PlanningService(session)
    old = service.create(kind="task", title="Prior scope", period=PeriodRef("week/2026-W42"))
    due = service.create(
        kind="task",
        title="Due outside scope",
        period=PeriodRef("year/2025"),
        due_date=date(2026, 10, 29),
    )
    broad = service.create(kind="task", title="Annual", period=PeriodRef("year/2026"))
    rows = query_report(session.report, PeriodRef("week/2026-W44"), date(2026, 10, 29))
    by_id = {r["id"]: r for r in rows}
    assert by_id[str(old.document.id)]["category"] == "Pendente de período anterior"
    assert by_id[str(due.document.id)]["category"] == "Prazo neste período"
    assert by_id[str(broad.document.id)]["category"].startswith("Contextual")
    assert (
        session.load(old.document.id).document.metadata["hw"]["scope"]["end_exclusive"]
        == "2026-10-19"
    )
    # ISO week crossing a year has one record in each relevant view.
    edge = service.create(kind="task", title="Boundary", period=PeriodRef("week/2026-W53"))
    for period in ("year/2026", "year/2027", "month/2027-01"):
        assert (
            sum(
                r["id"] == str(edge.document.id)
                for r in query_report(session.report, PeriodRef(period), date(2026, 10, 29))
            )
            == 1
        )


def test_goal_roundtrip_and_independent_progress(tmp_path):
    session = VaultSession.create(tmp_path / "vault", "Test")
    service = PlanningService(session)
    goal = service.create(
        kind="goal", title="Goal", period=PeriodRef("year/2026"), body="Original", tags=("Work",)
    )
    goal = service.update(goal, progress_percent=100, tags=("work",))
    assert goal.document.metadata["hw"]["status"] == "not_started"
    goal = service.update(goal, status="achieved", progress_percent=12)
    assert goal.document.metadata["hw"]["progress_percent"] == 12
    assert goal.document.body == "Original"
    target = VaultSession.create(tmp_path / "target", "Target")
    assert len(ImportService(target).import_files([goal.path]).imported) == 1
    assert len(ImportService(target).import_files([goal.path]).skipped) == 1
    goal = service.update(goal, title="Changed")
    assert len(ImportService(target).import_files([goal.path]).conflicting) == 1
