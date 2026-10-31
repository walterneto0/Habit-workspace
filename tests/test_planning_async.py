"""Planning shares the serialized queue, conflict and orderly shutdown contract."""

import threading
from datetime import date, datetime

from PySide6.QtCore import QCoreApplication, QSettings
from test_vault_tasks import wait

from habit_workspace.application.planning import PlanningService
from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.temporal import PeriodRef
from habit_workspace.presentation.controllers import WorkspaceController
from habit_workspace.presentation.vault_tasks import VaultTasks


def test_queued_planning_save_drains_on_shutdown(tmp_path, monkeypatch):
    QCoreApplication.instance() or QCoreApplication([])
    session = VaultSession.create(tmp_path / "vault", "Plan")
    entered, release = threading.Event(), threading.Event()
    original = VaultSession.open

    def blocked(root):
        entered.set()
        assert release.wait(5)
        return original(root)

    monkeypatch.setattr(VaultSession, "open", blocked)
    tasks = VaultTasks(session.root)
    try:
        tasks.refresh()
        assert entered.wait(2)
        args = dict(
            loaded=None,
            fields=dict(title="Queued"),
            kind="task",
            period=PeriodRef("day/2026-10-29"),
        )
        assert tasks.capture("planning_save", args)
        assert not tasks.capture("planning_save", args)
        tasks.close(wait=False)
        release.set()
        tasks.close()
        docs = original(session.root).report.documents
        assert len(docs) == 1 and docs[0].document.title == "Queued"
    finally:
        release.set()
        tasks.close()


def test_async_form_error_keeps_draft_and_completion_is_canonical(tmp_path, monkeypatch):
    QCoreApplication.instance() or QCoreApplication([])
    w = WorkspaceController(
        settings=QSettings(str(tmp_path / "prefs"), QSettings.IniFormat), today=date(2026, 10, 29)
    )
    assert w.createVault(str(tmp_path / "vault"), "Plan")
    w.navigate("week", "2026-10-29")
    try:
        w.planning.create("task")

        def fail(*args, **kwargs):
            raise OSError("disk failure")

        with monkeypatch.context() as m:
            m.setattr(PlanningService, "create", fail)
            w.planning.save(dict(title="Keep draft", body="Personal text"))
            wait(lambda: not w.actions.busy)
            assert w.planning.form["body"] == "Personal text"
            assert w.planning.form["error"] and w.state["noticeError"]
            assert not w.session.report.documents
        w.planning.save({})
        wait(lambda: not w.actions.busy)
        assert not w.planning.form
        row = w.state["planning"][0]
        w.planning.complete(row["id"], True, row["token"])
        wait(lambda: not w.actions.busy)
        assert w.state["planning"][0]["status"] == "completed"
        assert all(d.document.kind != "day_page" for d in w.session.report.documents)
        # UI rejects a token from before completion.
        w.planning.complete(row["id"], False, row["token"])
        assert w.state["noticeError"] and w.state["planning"][0]["status"] == "completed"
    finally:
        w.close()


def test_completion_noop_and_unknown_worker_operation(tmp_path):
    QCoreApplication.instance() or QCoreApplication([])
    session = VaultSession.create(tmp_path / "vault", "Plan")
    service = PlanningService(session)
    task = service.create(kind="task", title="Task", period=PeriodRef("day/2026-10-29"))
    done = service.complete(task, True, datetime.now().astimezone())
    raw = done.path.read_bytes()
    service.complete(done, True, datetime.now().astimezone())
    assert done.path.read_bytes() == raw
    tasks = VaultTasks(session.root)
    results = []
    tasks.completed.connect(lambda *args: results.append(args))
    try:
        assert tasks.capture("unknown", {})
        wait(lambda: not tasks.saving)
        assert isinstance(results[-1][-1], ValueError)
    finally:
        tasks.close()
