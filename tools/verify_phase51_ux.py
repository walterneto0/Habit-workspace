"""Layout Studio 5.1 journey with real pointer/keyboard events and temporary files.

Reuses the Phase 6 interaction harness and frozen clock. No user vault is opened.
"""

import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import verify_phase6_refinements as harness
from PySide6.QtCore import QObject, QPointF, QSettings, Qt, QThreadPool
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest
from verify_phase6 import records

from habit_workspace.application.vault import VaultSession

harness.OUTPUT = Path("/tmp/habit-workspace-phase51")


def choose(ui, name, index):
    item = ui.focus(ui.named(name))
    QTest.keyClick(ui.window, Qt.Key_Home)
    for _ in range(index):
        QTest.keyClick(ui.window, Qt.Key_Down)
    ui.settle()
    assert item.property("currentIndex") == index


def drag(ui, source, target):
    def point(item):
        return item.mapToScene(QPointF(item.width() / 2, item.height() / 2)).toPoint()

    start = point(ui.focus(ui.named(source)))
    end = point(ui.named(target))
    QTest.mousePress(ui.window, Qt.LeftButton, Qt.NoModifier, start)
    for step in range(1, 16):
        QTest.mouseMove(ui.window, start + (end - start) * (step / 15), 16)
    ui.settle()
    QTest.mouseRelease(ui.window, Qt.LeftButton, Qt.NoModifier, end)
    ui.settle()


def verify(reopen=None):
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication([])
    with TemporaryDirectory() as temporary:
        base = Path(temporary)
        controller = harness.controllers.WorkspaceController(
            settings=QSettings(str(base / "prefs"), QSettings.IniFormat),
            clock=harness.FrozenClock(),
        )
        ui = harness.Interface(app, controller)
        if reopen:
            harness.FrozenDatetime.ticks = 10000
            assert controller.openVault(reopen)
            controller.navigate("day", harness.DAY.isoformat())
            ui.settle()
            saved = records(Path(reopen))
            assert [r["value"] for r in saved["observations"]] == [30]
            assert [r["state"] for r in saved["checkins"]] == ["done"]
            cells = [
                c for b in controller.state["composition"]["blocks"] for c in b.get("capture", [])
            ]
            assert [c.get("state") for c in cells if c["kind"] == "habit"] == ["done", "pending"]
            assert [c["value"] for c in cells if c["kind"] == "field"] == ["30"]
            assert len(controller.session.report.layouts) == 1
            assert controller.session.index.path.exists()
            ui.capture("reopened")
            ui.close()
            return {"result": "PASS", "captures": ui.captures, "qmlWarnings": ui.errors}

        vault = base / "vault"
        VaultSession.create(vault, "Rotina · verificação 5.1")
        QTest.keyClick(ui.window, Qt.Key_O, Qt.ControlModifier)
        ui.settle()
        ui.text("vault-directory", str(vault))
        ui.click("vault-submit")
        ui.click("nav-day")
        for name in ("Ler", "Caminhar"):
            ui.click("new-habit")
            ui.text("habit-name", name)
            ui.text("habit-tags", "rotina")
            ui.click("habit-save")
        ids = {r["name"]: r["id"] for r in controller.state["habits"]["rows"]}
        ui.click("open-layout-studio")
        studio = controller.layoutStudio
        ui.click("studio-start")
        choose(ui, "studio-start-choice", 1)
        ui.capture("starting-point")
        ui.click("studio-start-apply")
        assert not studio.draft.layout.blocks
        ui.capture("empty-layout")
        ui.click("palette-checklist")
        for name in ("Ler", "Caminhar"):
            ui.text("checklist-search", name)
            ui.click("checklist-add")
        expected_ids = tuple(studio.draft.layout.blocks[0].config.selection.source_ids)
        ui.capture("checklist-selected")
        ui.click("palette-section")
        ui.text("studio-title", "Minha rotina")
        before = studio.draft.layout
        drag(ui, "layout-handle-0", "layout-card-1")
        assert studio.draft.layout.blocks[1].type == "checklist"
        ui.click("studio-up")
        assert studio.draft.layout == before
        QTest.keyClick(ui.window, Qt.Key_Z, Qt.ControlModifier)
        ui.settle()
        assert studio.draft.layout.blocks[1].type == "checklist"
        QTest.keyClick(ui.window, Qt.Key_Z, Qt.ControlModifier | Qt.ShiftModifier)
        ui.settle()
        assert studio.draft.layout == before
        assert studio.draft.layout.blocks[0].config.selection.source_ids == expected_ids
        ui.click("studio-add")
        ui.text("library-search", "duração")
        ui.click("palette-duration_input")
        assert ui.window.activeFocusItem().objectName() == "metric-name"
        ui.click("metric-create")
        assert ui.named("metric-name-error").property("text")
        assert not studio.fields
        ui.text("metric-name", "Tempo de leitura")
        ui.text("metric-unit", "minutos")
        ui.capture("field-basic")
        assert ui.window.findChild(QObject, "metric-dialog").property("height") < 600
        ui.click("metric-advanced")
        ui.text("metric-minimum", "10")
        ui.text("metric-maximum", "5")
        ui.click("metric-create")
        assert not studio.fields
        assert ui.named("metric-name").property("text") == "Tempo de leitura"
        ui.capture("field-validation")
        ui.text("metric-maximum", "120")
        ui.click("metric-create")
        ui.text("library-search", "")
        field_id = str(next(iter(studio.fields)))
        assert len(studio.fields) == 1
        for theme in ("dark", "light"):
            controller.setTheme(theme)
            for width, height in ((640, 480), (1024, 768), (1440, 900), (1920, 1080)):
                ui.window.setWidth(width)
                ui.window.setHeight(height)
                ui.settle()
                ui.focus(ui.named("studio-title"))
                point = ui.window.activeFocusItem().mapToScene(QPointF(5, 5))
                assert 0 <= point.x() < width and 0 <= point.y() < height
                ui.capture(f"{theme}-{width}")
        ui.window.setWidth(640)
        ui.window.setHeight(480)
        ui.settle()
        ui.click("studio-add")
        ui.click("palette-duration_input")
        assert ui.named("metric-source").property("count") == 1
        ui.text("metric-source-search", "inexistente")
        assert ui.named("metric-source").property("count") == 0
        ui.capture("existing-empty-small")
        ui.text("metric-source-search", "leitura")
        ui.click("metric-create")
        assert len(studio.fields) == 1
        assert str(studio.draft.layout.blocks[-1].binding.source_id) == field_id
        ui.click("studio-remove")
        assert len(studio.fields) == 1
        controller.setReducedMotion(True)
        ui.click("studio-show-canvas")
        ui.capture("small-canvas")
        ui.window.setWidth(1440)
        ui.window.setHeight(900)
        ui.settle()
        before = studio.draft.layout
        ui.click("studio-preview")
        assert studio.draft.layout == before
        assert not records(vault)["observations"]
        ui.capture("preview-reduced-motion")
        ui.click("studio-save")
        assert "Tempo de leitura" in studio.state["summary"]
        assert "29 de outubro de 2026" in studio.state["summary"]
        ui.capture("save-review")
        ui.click("studio-confirm-save")
        QThreadPool.globalInstance().waitForDone()
        ui.settle()
        assert not studio.draft, studio.message
        ui.click("checkin-done-" + ids["Ler"])
        ui.text("observation-input-" + field_id, "30")
        ui.click("observation-save-" + field_id)
        saved = records(vault)
        assert [r["value"] for r in saved["observations"]] == [30]
        assert [r["habit_id"] for r in saved["checkins"]] == [ids["Ler"]]
        assert [r["state"] for r in saved["checkins"]] == ["done"]
        assert (
            len(
                [
                    d
                    for d in controller.session.report.documents
                    if d.document.kind == "metric_definition"
                ]
            )
            == 1
        )
        ui.capture("tracking-saved")
        expected = [b["id"] for b in controller.state["composition"]["blocks"]]
        assert expected == [str(b.id) for b in before.blocks]
        canonical = {
            p: p.read_bytes()
            for p in vault.rglob("*")
            if p.is_file() and p.suffix in (".md", ".json")
        }
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
        assert all(path.read_bytes() == raw for path, raw in canonical.items())
        return {
            "result": "PASS",
            "platform": app.platformName(),
            "captures": ui.captures + restarted["captures"],
            "qmlWarnings": ui.errors,
            "checks": [
                "empty start",
                "multi-habit button add",
                "pointer and button reorder",
                "undo/redo",
                "field validation preserves input",
                "compatible source reuse",
                "small/large desktop and both themes",
                "reduced motion preview",
                "review and save",
                "tracking check-in and duration",
                "new process with deleted cache",
            ],
        }


if __name__ == "__main__":
    print(json.dumps(verify(sys.argv[2] if len(sys.argv) > 1 else None), indent=2))
