"""Actual QML interactions for multi-habit checklists and semantic browsing.

Only synthetic temporary vaults are used. Dates and activation instants are fixed.
A fresh process verifies the persisted layout and records after index deletion.
"""

import json
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from PySide6.QtCore import QEvent, QPointF, QSettings, Qt, QThreadPool
from PySide6.QtGui import QGuiApplication, QKeyEvent
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest
from verify_phase6 import load, records

from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.documents import Document
from habit_workspace.presentation import controllers, layout_studio

DAY = date(2026, 10, 29)
OUTPUT = Path("/tmp/habit-workspace-phase6-refinements")


class FrozenDatetime(datetime):
    ticks = 0

    @classmethod
    def now(cls, tz=None):
        cls.ticks += 1
        value = datetime(2026, 10, 29, 12, tzinfo=UTC) + timedelta(seconds=cls.ticks)
        return value if tz is None else value.astimezone(tz)


controllers.datetime = layout_studio.datetime = FrozenDatetime


class Interface:
    def __init__(self, app, controller):
        self.app, self.controller = app, controller
        self.errors, self.captures = [], []
        self.engine, self.window = load(controller, self.errors)
        self.window.setWidth(1440)
        self.window.setHeight(1000)
        self.window.requestActivate()
        self.settle()

    def settle(self):
        QTest.qWait(210)
        assert not self.errors, self.errors

    def walk(self, item=None):
        item = item or self.window.contentItem()
        yield item
        for child in item.childItems():
            yield from self.walk(child)

    def named(self, name):
        matches = [i for i in self.walk() if i.objectName() == name and i.isVisible()]
        if not matches:
            self.capture("missing-" + name)
        assert matches, (name, self.controller.state["habitForm"], self.controller.state["notice"])
        return matches[0]

    def focus(self, item):
        item.forceActiveFocus(Qt.TabFocusReason)
        self.settle()
        return item

    def click_item(self, item):
        self.focus(item)
        point = item.mapToScene(QPointF(item.width() / 2, item.height() / 2)).toPoint()
        assert 0 <= point.x() < self.window.width() and 0 <= point.y() < self.window.height(), point
        QTest.mouseClick(self.window, Qt.LeftButton, Qt.NoModifier, point)
        self.settle()

    def click(self, name):
        item = self.named(name)
        assert item.isEnabled(), name
        self.click_item(item)

    def text(self, name, value):
        self.focus(self.named(name))
        QTest.keyClick(self.window, Qt.Key_A, Qt.ControlModifier)
        QTest.keyClick(self.window, Qt.Key_Delete)
        for char in value:
            self.app.sendEvent(self.window, QKeyEvent(QEvent.KeyPress, 0, Qt.NoModifier, char))
            self.app.sendEvent(self.window, QKeyEvent(QEvent.KeyRelease, 0, Qt.NoModifier, char))
        QTest.keyClick(self.window, Qt.Key_Tab)
        self.settle()

    def capture(self, name):
        output = OUTPUT / self.app.platformName()
        output.mkdir(parents=True, exist_ok=True)
        path = output / (name + ".png")
        assert self.window.grabWindow().save(str(path))
        self.captures.append(str(path))

    def close(self):
        self.controller.close()
        self.window.close()
        self.engine.deleteLater()
        self.app.sendPostedEvents(None, QEvent.DeferredDelete)


def states(controller):
    return [
        c["state"] for b in controller.state["composition"]["blocks"] for c in b.get("capture", [])
    ]


def verify(reopen=None):
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication([])
    with TemporaryDirectory() as temporary:
        base = Path(temporary)
        controller = controllers.WorkspaceController(
            settings=QSettings(str(base / "prefs"), QSettings.IniFormat), today=DAY
        )
        ui = Interface(app, controller)
        if reopen:
            FrozenDatetime.ticks = 10000
            assert controller.openVault(reopen)
            controller.navigate("day", DAY.isoformat())
            ui.settle()
            assert states(controller) == ["done", "skipped", "pending"]
            assert controller.session.index.path.exists()
            ui.focus(ui.named("checkin-done-" + records(Path(reopen))["checkins"][0]["habit_id"]))
            ui.capture("restarted")
            ui.close()
            return {"result": "PASS", "captures": ui.captures, "qmlWarnings": ui.errors}

        vault = base / "vault"
        session = VaultSession.create(vault, "Refinamentos da Fase 6")
        note = Document.from_metadata(
            {
                "hw": {
                    "schema_version": 4,
                    "kind": "note",
                    "id": str(uuid4()),
                    "title": "Uma nota comum",
                    "tags": ["pessoal"],
                }
            },
            "# Minha nota\n\nTexto preservado na prévia.",
        )
        session.create_document("Notes/nota.md", note)
        QTest.keyClick(ui.window, Qt.Key_O, Qt.ControlModifier)
        ui.settle()
        ui.text("vault-directory", str(vault))
        ui.click("vault-submit")
        ui.click("nav-day")
        for name in ("Ler", "Caminhar", "Beber água"):
            ui.click("new-habit")
            assert controller.state["habitForm"], (
                name,
                controller.state["view"],
                controller.state["notice"],
            )
            ui.text("habit-name", name)
            ui.text("habit-tags", "rotina")
            ui.click("habit-save")
        ids = {r["name"]: r["id"] for r in controller.state["habits"]["rows"]}
        ui.click("open-layout-studio")
        ui.click("palette-checklist")
        for name in ("Ler", "Caminhar", "Beber água"):
            ui.text("checklist-search", name)
            ui.click("checklist-add")
        studio = controller.layoutStudio
        block = studio.draft.view.blocks[-1]
        assert len(block.config.selection.source_ids) == 3
        ui.click("checklist-up-" + ids["Beber água"])
        assert list(map(str, studio.draft.view.blocks[-1].config.selection.source_ids)) == [
            ids["Ler"],
            ids["Beber água"],
            ids["Caminhar"],
        ]
        ui.click("checklist-down-" + ids["Beber água"])
        ui.capture("manual-selection")
        # Keyboard-operated selection modes; undo restores the exact manual UUID order.
        ui.focus(ui.named("checklist-mode"))
        QTest.keyClick(ui.window, Qt.Key_Down)
        ui.settle()
        ui.text("checklist-tags", "rotina")
        ui.click("checklist-apply-tags")
        assert studio.draft.view.blocks[-1].config.selection.mode == "by_tags"
        ui.capture("dynamic-tags")
        ui.focus(ui.named("checklist-mode"))
        QTest.keyClick(ui.window, Qt.Key_Down)
        ui.settle()
        assert studio.draft.view.blocks[-1].config.selection.mode == "all"
        ui.capture("contextual-selection")
        QTest.keyClick(ui.window, Qt.Key_Z, Qt.ControlModifier)
        ui.settle()
        QTest.keyClick(ui.window, Qt.Key_Z, Qt.ControlModifier)
        ui.settle()
        assert (
            studio.draft.view.blocks[-1].config.selection.source_ids
            == block.config.selection.source_ids
        )

        ui.click("studio-save")
        buttons = [
            i for i in ui.walk() if i.isVisible() and i.property("text") in ("Salvar", "Save")
        ]
        ui.click_item(buttons[-1])
        QThreadPool.globalInstance().waitForDone()
        ui.settle()
        assert not studio.draft, studio.message
        ui.click("checkin-done-" + ids["Ler"])
        ui.click("checkin-skipped-" + ids["Caminhar"])
        assert states(controller) == ["done", "skipped", "pending"]
        saved = records(vault)["checkins"]
        assert [(r["habit_id"], r["state"]) for r in saved] == [
            (ids["Ler"], "done"),
            (ids["Caminhar"], "skipped"),
        ]
        ui.focus(ui.named("checkin-done-" + ids["Beber água"]))
        ui.capture("checklist-saved")
        ui.click("nav-month")
        ui.click("nav-day")
        assert states(controller) == ["done", "skipped", "pending"]
        ui.click("nav-habits")
        ui.click("document-" + ids["Ler"])
        assert ui.named("habit-detail-scope").property("text") == "Escopo: 2026-10-29 → 2026-10-29"
        assert "Concluído" in ui.named("habit-detail-status").property("text")
        ui.focus(ui.named("habit-detail-edit"))
        ui.capture("habit-detail")
        ui.click("habit-detail-edit")
        ui.text("habit-name", "Ler com calma")
        ui.click("habit-save")
        assert controller.state["selected"]["title"] == "Ler com calma"
        ui.click("nav-notes")
        ui.click("document-" + str(note.id))
        assert (
            ui.named("document-preview").property("text")
            == "Minha nota\n\nTexto preservado na prévia."
        )
        ui.capture("note-preview")
        ui.click("nav-day")
        for width, height in ((640, 480), (1024, 768)):
            ui.window.setWidth(width)
            ui.window.setHeight(height)
            ui.settle()
            ui.focus(ui.named("checkin-skipped-" + ids["Caminhar"]))
            ui.capture(f"checklist-{width}")
        ui.close()
        (vault / ".habit-workspace/index.sqlite").unlink()
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--reopen", str(vault)],
            capture_output=True,
            text=True,
            timeout=40,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert not result.stderr, result.stderr
        restarted = json.loads(result.stdout)
        return {
            "result": "PASS",
            "platform": app.platformName(),
            "nativeWindowTest": app.platformName() in ("xcb", "wayland"),
            "captures": ui.captures + restarted["captures"],
            "qmlWarnings": ui.errors,
            "checks": [
                "three habits created via QML",
                "one checklist, manual search/add/reorder, tag and contextual modes",
                "independent done/skipped records in canonical day",
                "navigate away and back",
                "habit detail and edit",
                "ordinary note preview",
                "640/1024 resize",
                "fresh process and SQLite reconstruction",
            ],
        }


if __name__ == "__main__":
    print(json.dumps(verify(sys.argv[2] if len(sys.argv) > 1 else None), indent=2))
