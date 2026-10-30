"""Phase 6.5B pointer/keyboard journey; disposable vault, deterministic civil date."""

import argparse
import json
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from benchmark_gui import wait
from PySide6.QtCore import QObject, QPointF, QSettings, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest
from verify_phase6 import records
from verify_phase6_refinements import Interface

from habit_workspace.application.capture import CaptureService
from habit_workspace.application.vault import VaultSession
from habit_workspace.presentation.clock import ManualClock
from habit_workspace.presentation.controllers import WorkspaceController


class Journey(Interface):
    def settle(self):
        # Wait for an actual frame, including layout polish and modal transitions.
        frames = []

        def rendered():
            frames.append(True)

        self.window.frameSwapped.connect(rendered)
        self.window.update()
        wait(self.app, lambda: bool(frames))
        self.window.frameSwapped.disconnect(rendered)
        assert not self.errors, self.errors

    def dialog_closed(self, filename):
        from PySide6.QtCore import QObject

        wait(
            self.app,
            lambda: all(
                not obj.property("visible")
                for obj in self.window.findChildren(QObject)
                if filename in obj.metaObject().className()
            ),
        )

    def click_without_settle(self, name):
        item = self.named(name)
        assert item.isEnabled(), name
        self.focus(item)
        point = item.mapToScene(QPointF(item.width() / 2, item.height() / 2)).toPoint()
        assert 0 <= point.x() < self.window.width() and 0 <= point.y() < self.window.height()
        QTest.mouseClick(self.window, Qt.LeftButton, Qt.NoModifier, point)
        return item


def verify(audit=False, reopen=None):
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication([])
    with TemporaryDirectory(prefix="hw-65b-") as temporary:
        base = Path(temporary)
        vault = Path(reopen[0]) if reopen else base / "vault"
        if not reopen:
            VaultSession.create(vault, "Rotina de teste")
        controller = WorkspaceController(
            settings=QSettings(str(base / "prefs"), QSettings.IniFormat),
            clock=ManualClock(datetime(2026, 10, 29, 12).astimezone()),
        )
        ui = Journey(app, controller)
        try:
            QTest.keyClick(ui.window, Qt.Key_O, Qt.ControlModifier)
            ui.settle()
            ui.text("vault-directory", str(base / "missing-vault"))
            ui.click("vault-submit")
            wait(
                app,
                lambda: not controller.state["openingVault"] and controller.state["noticeError"],
                timeout=10,
            )
            dialog = ui.window.findChild(QObject, "vault-dialog")
            assert dialog is not None
            assert dialog.property("visible")
            assert not controller.state["hasVault"]
            assert ui.named("vault-submit").isEnabled()
            assert any(
                item.isVisible() and item.property("text") == controller.state["notice"]
                for item in ui.walk()
            )

            ui.text("vault-directory", str(vault))
            open_entered, release_open = threading.Event(), threading.Event()
            original_open = VaultSession.open
            open_descriptor = VaultSession.__dict__["open"]

            def delayed_open(directory):
                open_entered.set()
                assert release_open.wait(10), "test did not release the vault-open worker"
                return original_open(directory)

            VaultSession.open = staticmethod(delayed_open)
            try:
                ui.click_without_settle("vault-submit")
                assert open_entered.wait(2), "vault-open worker did not start"
                assert controller.state["openingVault"]
                submit = ui.named("vault-submit")
                assert submit.property("text") == "Abrindo…"
                assert not submit.isEnabled()
                ui.capture("65b-vault-loading")
                release_open.set()
                wait(
                    app,
                    lambda: (
                        not controller.state["openingVault"]
                        and (controller.state["hasVault"] or controller.state["noticeError"])
                    ),
                    timeout=10,
                )
            finally:
                release_open.set()
                VaultSession.open = open_descriptor
            assert controller.state["hasVault"], controller.state["notice"]
            ui.dialog_closed("VaultDialog")
            ui.click("nav-week")
            if reopen:
                habit, record_id = reopen[1:]
                row = next(r for r in controller.state["habits"]["rows"] if r["id"] == habit)
                assert row["cell"]["recorded"] == "done"
                assert records(vault)["checkins"][0]["id"] == record_id
                ui.named("quick-complete-" + habit)
                print(json.dumps({"result": "PASS", "reopened": True, "qmlWarnings": ui.errors}))
                return
            ui.click("new-habit")
            ui.text("habit-name", "Ler diariamente")
            ui.click("habit-daily")
            ui.click("habit-save")
            ui.dialog_closed("HabitDialog")
            assert not controller.studio.draft
            habit = controller.state["habits"]["rows"][0]["id"]
            control = "quick-complete-" + habit
            available = any(i.objectName() == control and i.isVisible() for i in ui.walk())
            if audit:
                ui.capture("65b-before-first-habit")
                print(
                    json.dumps(
                        {
                            "direct_checkin_available": available,
                            "built_in_blocks": [
                                b.get("type") for b in controller.state["composition"]["blocks"]
                            ],
                            "qmlWarnings": ui.errors,
                        }
                    )
                )
                return
            assert available, "first check-in must be available without Studio"
            capture_entered, release_capture = threading.Event(), threading.Event()
            original_capture = CaptureService.set_checkin

            def delayed_capture(service, *args, **kwargs):
                capture_entered.set()
                assert release_capture.wait(10), "test did not release the capture worker"
                return original_capture(service, *args, **kwargs)

            CaptureService.set_checkin = delayed_capture
            try:
                ui.click_without_settle(control)
                assert capture_entered.wait(2), "capture worker did not start"
                feedback = controller.state["tracking"]["feedback"]
                assert feedback["saving"] and not feedback["error"]
                assert ui.named("quick-feedback-" + habit).property("text") == "Salvando…"
                ui.capture("65b-capture-saving")
                release_capture.set()
                wait(app, lambda: not controller.actions.busy)
            finally:
                release_capture.set()
                CaptureService.set_checkin = original_capture
            assert controller.state["habits"]["rows"][0]["cell"]["recorded"] == "done"
            feedback = controller.state["tracking"]["feedback"]
            assert not feedback["saving"] and not feedback["error"]
            assert "Salvo" in ui.named("quick-feedback-" + habit).property("text")
            saved = records(vault)["checkins"]
            assert len(saved) == 1 and saved[0]["habit_id"] == habit
            record_id = saved[0]["id"]
            ui.capture("65b-first-completion")
            failure_entered, release_failure = threading.Event(), threading.Event()

            def failed_capture(_service, *_args, **_kwargs):
                failure_entered.set()
                assert release_failure.wait(10), "test did not release the failing worker"
                raise OSError("simulated write failure")

            CaptureService.set_checkin = failed_capture
            try:
                ui.click_without_settle(control)
                assert failure_entered.wait(2), "failing capture worker did not start"
                assert controller.state["tracking"]["feedback"]["saving"]
                release_failure.set()
                wait(app, lambda: not controller.actions.busy)
            finally:
                release_failure.set()
                CaptureService.set_checkin = original_capture
            feedback = controller.state["tracking"]["feedback"]
            assert feedback["error"] and not feedback["saving"]
            assert "Não foi possível salvar" in feedback["text"]
            assert "Não foi possível salvar" in ui.named("quick-feedback-" + habit).property("text")
            assert controller.state["habits"]["rows"][0]["cell"]["recorded"] == "done"
            assert records(vault)["checkins"][0]["state"] == "done"
            ui.click("habit-details-" + habit)
            ui.click("habit-detail-edit")
            ui.text("habit-name", "Ler com calma")
            ui.text("habit-tags", "estudos")
            ui.click("habit-save")
            ui.dialog_closed("HabitDialog")
            ui.click("habit-detail-track")
            assert controller.state["period"] == "week/2026-W44"
            assert controller.state["tracking"]["date"] == "2026-10-29"
            assert controller.state["habits"]["rows"][0]["name"] == "Ler com calma"
            # Existing source in a custom checklist must see the direct capture.
            ui.click("open-layout-studio")
            ui.click("palette-checklist")
            ui.text("checklist-search", "Ler com calma")
            ui.click("checklist-add")
            ui.click("studio-save")
            ui.click("studio-confirm-save")
            wait(app, lambda: not controller.studio.busy)
            ui.dialog_closed("StudioDialog")
            assert not controller.studio.draft
            ui.click("checkin-skipped-" + habit)
            wait(app, lambda: not controller.actions.busy)
            assert controller.state["habits"]["rows"][0]["cell"]["recorded"] == "skipped"
            ui.focus(ui.named(control))
            QTest.keyClick(ui.window, Qt.Key_Space)
            wait(app, lambda: not controller.actions.busy)
            assert records(vault)["checkins"][0]["id"] == record_id
            assert records(vault)["checkins"][0]["state"] == "done"
            for theme in ("light", "dark"):
                controller.setTheme(theme)
                for width, height in ((640, 480), (1024, 768), (1440, 900)):
                    ui.window.setWidth(width)
                    ui.window.setHeight(height)
                    ui.settle()
                    ui.focus(ui.named(control))
                    QTest.keyClick(ui.window, Qt.Key_Tab)
                    assert ui.window.activeFocusItem() is not None
                    ui.capture(f"65b-{theme}-{width}")
            controller.setReducedMotion(True)
            assert controller.state["reducedMotion"]
            ui.window.setWidth(1440)
            ui.window.setHeight(900)
            ui.settle()
            ui.text("capture-jump", "invalid")
            ui.focus(ui.named("capture-jump"))
            QTest.keyClick(ui.window, Qt.Key_Return)
            assert controller.state["noticeError"]
            assert controller.capture_day.isoformat() == "2026-10-29"
            controller.close()
            ui.window.hide()
            (vault / ".habit-workspace/index.sqlite").unlink()
            result = subprocess.run(
                [sys.executable, __file__, "--reopen", str(vault), habit, record_id],
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert result.returncode == 0, result.stdout + result.stderr
            assert '"result": "PASS"' in result.stdout
            print(
                json.dumps(
                    {
                        "result": "PASS",
                        "journeys": [
                            "first use without Studio",
                            "details/edit/return",
                            "direct and customized canonical record",
                            "keyboard capture",
                            "themes/widths/reduced motion",
                            "invalid date",
                            "independent reopen/index recovery",
                        ],
                        "qmlWarnings": ui.errors,
                        "captures": ui.captures,
                    }
                )
            )
        finally:
            ui.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--reopen", nargs=3)
    args = parser.parse_args()
    verify(args.audit, args.reopen)
