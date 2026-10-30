"""Serialized background file work: truthful completion, bounded queue and epochs."""

import threading
import time
from copy import deepcopy
from datetime import date, datetime
from uuid import UUID

from PySide6.QtCore import QCoreApplication, QSettings

from habit_workspace.application.capture import CaptureService
from habit_workspace.application.habits import HabitService
from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.documents import Document
from habit_workspace.domain.temporal import PeriodRef
from habit_workspace.presentation.controllers import WorkspaceController
from habit_workspace.presentation.vault_tasks import VaultTasks
from habit_workspace.vault.atomic_io import ConflictError


def wait(predicate):
    app = QCoreApplication.instance()
    deadline = time.monotonic() + 5
    while not predicate() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.001)
    assert predicate()


def checkins(root):
    report = VaultSession.open(root).report
    return [
        record
        for loaded in report.documents
        for record in loaded.document.metadata["hw"].get("checkins", [])
    ]


def capture_request(habit_id, state="done", expected=None):
    return dict(
        habit_id=habit_id,
        day=date(2026, 10, 29),
        state=state,
        today=date(2026, 10, 29),
        recorded_at=datetime.now().astimezone(),
        expected=expected,
    )


def test_serial_capture_conflict_and_stale_refresh(tmp_path):
    QCoreApplication.instance() or QCoreApplication([])
    session = VaultSession.create(tmp_path / "vault", "Tasks")
    habit = HabitService(session).create(name="Ler", period=PeriodRef("day/2026-10-29")).habit
    tasks = VaultTasks(session.root)
    results = []
    tasks.completed.connect(lambda *args: results.append(args))
    request = dict(
        habit_id=habit.id,
        day=date(2026, 10, 29),
        state="done",
        today=date(2026, 10, 29),
        recorded_at=datetime.now().astimezone(),
        expected=None,
    )
    try:
        assert tasks.capture("checkin", request)
        assert not tasks.capture("checkin", request), "never queue repeated stale tokens"
        wait(lambda: not tasks.saving)
        assert results[-1][0] == "checkin" and results[-1][-1] is None
        assert tasks.capture("checkin", request | {"state": "skipped"})
        wait(lambda: not tasks.saving)
        assert results[-1][-1] is not None, "stale expected value must conflict"
        report = session.scan()
        records = [
            r for d in report.documents for r in d.document.metadata["hw"].get("checkins", [])
        ]
        assert [(UUID(r["habit_id"]), r["state"]) for r in records] == [(habit.id, "done")]
    finally:
        tasks.close()


def test_capture_queued_behind_refresh_is_idempotent_and_reopens(tmp_path, monkeypatch):
    QCoreApplication.instance() or QCoreApplication([])
    session = VaultSession.create(tmp_path / "vault", "Queued capture")
    habit = HabitService(session).create(name="Ler", period=PeriodRef("day/2026-10-29")).habit
    entered, release = threading.Event(), threading.Event()
    original = VaultSession.open

    def blocked(root):
        entered.set()
        assert release.wait(5)
        return original(root)

    monkeypatch.setattr(VaultSession, "open", blocked)
    tasks = VaultTasks(session.root)
    results = []
    tasks.completed.connect(lambda *args: results.append(args))
    try:
        tasks.refresh()
        assert entered.wait(2)
        request = capture_request(habit.id)
        assert tasks.capture("checkin", request)
        assert not tasks.capture("checkin", request), (
            "an in-flight capture must not be queued twice"
        )
        release.set()
        wait(lambda: not tasks.active and not tasks.saving)
        assert [result[0] for result in results] == ["refresh", "checkin"]
        assert results[-1][-1] is None

        assert tasks.capture("checkin", request | {"expected": "done"})
        wait(lambda: not tasks.active and not tasks.saving)
        assert results[-1][1].action == "unchanged"
        records = checkins(session.root)
        assert len(records) == 1 and records[0]["state"] == "done"
    finally:
        release.set()
        tasks.close()


def test_close_waits_for_accepted_capture_queued_behind_refresh(tmp_path, monkeypatch):
    QCoreApplication.instance() or QCoreApplication([])
    session = VaultSession.create(tmp_path / "vault", "Shutdown capture")
    habit = HabitService(session).create(name="Ler", period=PeriodRef("day/2026-10-29")).habit
    entered, release = threading.Event(), threading.Event()
    original = VaultSession.open

    def blocked(root):
        entered.set()
        assert release.wait(5)
        return original(root)

    monkeypatch.setattr(VaultSession, "open", blocked)
    tasks = VaultTasks(session.root)
    tasks.refresh()
    assert entered.wait(2)
    assert tasks.capture("checkin", capture_request(habit.id))
    releaser = threading.Thread(target=lambda: (time.sleep(0.02), release.set()), daemon=True)
    releaser.start()
    try:
        tasks.close()
        releaser.join(timeout=2)
        assert not releaser.is_alive()
        records = checkins(session.root)
        assert len(records) == 1 and records[0]["state"] == "done"
    finally:
        release.set()
        tasks.close()


def test_external_checkin_edit_conflicts_with_async_capture(tmp_path):
    QCoreApplication.instance() or QCoreApplication([])
    session = VaultSession.create(tmp_path / "vault", "External edit")
    habit = HabitService(session).create(name="Ler", period=PeriodRef("day/2026-10-29")).habit
    tasks = VaultTasks(session.root)
    results = []
    tasks.completed.connect(lambda *args: results.append(args))
    try:
        assert tasks.capture("checkin", capture_request(habit.id))
        wait(lambda: not tasks.active and not tasks.saving)

        external = VaultSession.open(session.root)
        day_page = next(
            loaded
            for loaded in external.report.documents
            if loaded.document.metadata["hw"].get("date") == "2026-10-29"
        )
        edited = deepcopy(day_page.document)
        edited.metadata["hw"]["checkins"][0]["state"] = "skipped"
        external.repository.save(day_page, edited)

        assert tasks.capture("checkin", capture_request(habit.id, state="missed", expected="done"))
        wait(lambda: not tasks.active and not tasks.saving)
        assert isinstance(results[-1][-1], ConflictError)
        records = checkins(session.root)
        assert len(records) == 1 and records[0]["state"] == "skipped"
    finally:
        tasks.close()


def test_async_write_failure_is_published_as_error_not_success(tmp_path, monkeypatch):
    QCoreApplication.instance() or QCoreApplication([])
    workspace = WorkspaceController(
        settings=QSettings(str(tmp_path / "prefs"), QSettings.IniFormat),
        today=date(2026, 10, 29),
    )
    assert workspace.createVault(str(tmp_path / "vault"), "Failed write")
    workspace.navigate("day", "2026-10-29")
    habit = (
        HabitService(workspace.session).create(name="Ler", period=PeriodRef("day/2026-10-29")).habit
    )

    def fail_write(*_args, **_kwargs):
        raise OSError("simulated disk write failure")

    monkeypatch.setattr(CaptureService, "set_checkin", fail_write)
    try:
        assert workspace.actions.setCheckin(str(habit.id), "done", "null")
        wait(lambda: not workspace.actions.busy)
        feedback = workspace.state["tracking"]["feedback"]
        assert feedback["error"] and not feedback["saving"]
        assert "Não foi possível salvar" in feedback["text"]
        assert "Salvo" not in feedback["text"]
        assert workspace.state["noticeError"]
        assert checkins(workspace.session.root) == []
    finally:
        workspace.close()


def test_refresh_coalescing_invalidation_and_close(tmp_path, monkeypatch):
    QCoreApplication.instance() or QCoreApplication([])
    session = VaultSession.create(tmp_path / "vault", "Tasks")
    document = Document.from_metadata(
        {"hw": {"schema_version": 4, "kind": "note", "id": "935a4e7a-4b14-44b3-baf1-52d5ae8f39dd"}},
        "original",
    )
    session.create_document("Notes/external.md", document)
    entered, release = threading.Event(), threading.Event()
    original = VaultSession.open
    calls = []

    def blocked(root):
        calls.append(root)
        opened_session = original(root)
        entered.set()
        assert release.wait(5)
        return opened_session

    monkeypatch.setattr(VaultSession, "open", blocked)
    tasks = VaultTasks(session.root)
    results = []
    tasks.completed.connect(lambda *args: results.append(args))
    tasks.refresh()
    assert entered.wait(2)
    external = original(session.root)
    current = next(
        loaded for loaded in external.report.documents if loaded.document.id == document.id
    )
    edited = deepcopy(current.document)
    edited.body = "newer external content"
    external.repository.save(current, edited)
    for _ in range(100):
        tasks.refresh()
    tasks.invalidate()
    release.set()
    wait(lambda: not tasks.active)
    assert len(results) == 1, "discard old epoch; publish only reconciled scan"
    assert len(calls) == 1, "worker owns and reuses a single private session"
    newest = next(loaded for loaded in results[0][2].documents if loaded.document.id == document.id)
    assert newest.document.body == "newer external content"
    tasks.close()
    tasks.refresh()
    assert not tasks.active
