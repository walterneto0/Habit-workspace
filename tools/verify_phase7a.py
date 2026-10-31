"""Real pointer/keyboard planning journey in a disposable offline vault."""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from benchmark_gui import wait
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest
from verify_phase65b import Journey

from habit_workspace.application.vault import VaultSession
from habit_workspace.presentation.clock import ManualClock
from habit_workspace.presentation.controllers import WorkspaceController


def verify(reopen=None):
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication([])
    with TemporaryDirectory(prefix="hw-7a-") as temporary:
        base = Path(temporary)
        vault = Path(reopen) if reopen else base / "vault"
        if not reopen:
            VaultSession.create(vault, "Planning")
        controller = WorkspaceController(
            settings=QSettings(str(base / "prefs"), QSettings.IniFormat),
            clock=ManualClock(datetime(2026, 10, 29, 12).astimezone()),
        )
        ui = Journey(app, controller)
        try:
            controller.actions.openVault(str(vault))
            wait(app, lambda: controller.state["hasVault"] and not controller.actions.opening)
            ui.click("nav-week")
            if reopen:
                rows = controller.state["planning"]
                assert {r["title"] for r in rows} == {"Prepare outline", "Annual goal"}
                assert next(r for r in rows if r["kind"] == "task")["status"] == "completed"
                assert next(r for r in rows if r["kind"] == "goal")["progress"] == 37
                assert next(r for r in rows if r["kind"] == "goal")["status"] == "paused"
                assert not any(
                    d.document.metadata["hw"].get("checkins")
                    for d in controller.session.report.documents
                )
                print(json.dumps({"result": "PASS", "reopen": True, "qmlWarnings": ui.errors}))
                return
            ui.click("new-task")
            ui.text("planning-title", "Prepare outline")
            ui.text("planning-body", "Keep **Markdown**")
            ui.text("planning-due", "2026-11-04")
            ui.click("planning-save")
            wait(app, lambda: not controller.actions.busy, timeout=10)
            assert not controller.planning.form, controller.planning.form
            ui.dialog_closed("PlanningDialog")
            task = controller.state["planning"][0]["id"]
            assert controller.state["period"] == "week/2026-W44"
            ui.focus(ui.named("planning-complete-" + task))
            QTest.keyClick(ui.window, Qt.Key_Space)
            wait(
                app,
                lambda: (
                    not controller.actions.busy
                    and controller.state["planning"][0]["status"] == "completed"
                ),
            )
            ui.click("planning-complete-" + task)
            wait(
                app,
                lambda: (
                    not controller.actions.busy
                    and controller.state["planning"][0]["status"] == "pending"
                ),
            )
            ui.click("new-goal")
            ui.text("planning-title", "Annual goal")
            ui.text("planning-start", "2026-01-01")
            ui.text("planning-end", "2026-12-31")
            ui.text("planning-progress", "37")
            ui.click("planning-save")
            wait(app, lambda: not controller.actions.busy, timeout=10)
            assert not controller.planning.form, controller.planning.form
            ui.dialog_closed("PlanningDialog")
            goal = next(r["id"] for r in controller.state["planning"] if r["kind"] == "goal")
            ui.click("planning-edit-" + goal)
            ui.focus(ui.named("planning-status"))
            QTest.keyClick(ui.window, Qt.Key_Down)
            QTest.keyClick(ui.window, Qt.Key_Down)
            QTest.keyClick(ui.window, Qt.Key_Down)
            ui.click("planning-save")
            wait(app, lambda: not controller.actions.busy, timeout=10)
            assert not controller.planning.form, controller.planning.form
            ui.dialog_closed("PlanningDialog")
            ui.text("planning-search", "outline")
            assert len(controller.state["planning"]) == 1
            ui.text("planning-search", "")
            # Conflict after the editor opens: preserve external content and the draft.
            ui.click("planning-edit-" + task)
            path = next(
                d.path for d in controller.session.report.documents if str(d.document.id) == task
            )
            path.write_text(path.read_text().replace("Keep **Markdown**", "External **Markdown**"))
            ui.text("planning-body", "My unsaved draft")
            ui.click("planning-save")
            wait(
                app,
                lambda: not controller.actions.busy and bool(controller.planning.form.get("error")),
            )
            assert "External **Markdown**" in path.read_text()
            assert ui.named("planning-body").property("text") == "My unsaved draft"
            ui.click("planning-cancel")
            ui.dialog_closed("PlanningDialog")
            # Publish a task checklist through the real Studio controls.
            ui.click("open-layout-studio")
            ui.click("palette-checklist")
            ui.text("checklist-search", "Prepare outline")
            ui.click("checklist-add")
            ui.click("palette-list")
            ui.click("studio-bind")
            ui.click("studio-save")
            ui.click("studio-confirm-save")
            wait(app, lambda: not controller.studio.busy and not controller.studio.draft)
            ui.dialog_closed("StudioDialog")
            blocks = controller.state["composition"]["blocks"]
            assert any(any(r["id"] == task for r in b.get("planning", [])) for b in blocks)
            # Identify the layout row specifically, rather than the normal planning row.
            layout = ui.named("tracking-composition")
            candidates = [i for i in ui.walk() if i.objectName() == "planning-complete-" + task]

            def inside(item):
                while item:
                    if item == layout:
                        return True
                    item = item.parentItem()
                return False

            button = next(i for i in candidates if inside(i))
            ui.focus(button)
            QTest.keyClick(ui.window, Qt.Key_Space)
            wait(
                app,
                lambda: (
                    not controller.actions.busy
                    and next(r for r in controller.state["planning"] if r["id"] == task)["status"]
                    == "completed"
                ),
            )
            for route in ("day", "month", "year", "week"):
                ui.click("nav-" + route)
                assert task in {r["id"] for r in controller.state["planning"]}
            for width, height in ((640, 480), (1024, 768), (1440, 900)):
                ui.window.setWidth(width)
                ui.window.setHeight(height)
                ui.settle()
                ui.window.contentItem().forceActiveFocus()
                ui.settle()
                ui.click("planning-edit-" + task)
                ui.focus(ui.named("planning-title"))
                QTest.keyClick(ui.window, Qt.Key_Tab)
                assert ui.window.activeFocusItem() is not None
                ui.click("planning-cancel")
                ui.dialog_closed("PlanningDialog")
            controller.close()
            ui.window.hide()
            (vault / ".habit-workspace/index.sqlite").unlink()
            result = subprocess.run(
                [sys.executable, __file__, str(vault)], capture_output=True, text=True, timeout=30
            )
            assert result.returncode == 0, result.stdout + result.stderr
            assert not ui.errors, ui.errors
            print(
                json.dumps(
                    {
                        "result": "PASS",
                        "qmlWarnings": ui.errors,
                        "checks": [
                            "direct task/goal",
                            "keyboard completion/reopen",
                            "search",
                            "external conflict",
                            "Studio task capture",
                            "cross-period",
                            "resize",
                            "process reopen/index rebuild",
                        ],
                    }
                )
            )
        finally:
            ui.close()


if __name__ == "__main__":
    verify(sys.argv[1] if len(sys.argv) > 1 else None)
