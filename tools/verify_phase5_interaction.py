"""Real QQuickWindow pointer/key events; synthetic vault; no data capture."""

import json
import subprocess
import sys
from datetime import date
from importlib.resources import files
from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtCore import QEvent, QPointF, QSettings, Qt, QThreadPool, QUrl
from PySide6.QtGui import QGuiApplication, QKeyEvent
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest

from habit_workspace.application.vault import VaultSession
from habit_workspace.presentation.controllers import WorkspaceController


def verify():
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication([])
    output = Path("/tmp/habit-workspace-phase5") / app.platformName()
    output.mkdir(parents=True, exist_ok=True)
    errors = []
    checks = []
    captures = []
    with TemporaryDirectory() as temporary:
        base = Path(temporary)
        session = VaultSession.create(base / "vault", "Interaction fixture")
        del session
        controller = WorkspaceController(
            settings=QSettings(str(base / "prefs"), QSettings.IniFormat), today=date(2026, 10, 29)
        )
        engine = QQmlApplicationEngine()
        engine.warnings.connect(lambda ws: errors.extend(w.toString() for w in ws))
        engine.setInitialProperties({"backend": controller})
        engine.load(
            QUrl.fromLocalFile(str(files("habit_workspace.presentation").joinpath("qml/Main.qml")))
        )
        assert engine.rootObjects(), errors
        window = engine.rootObjects()[0]
        window.setWidth(1440)
        window.setHeight(900)
        window.requestActivate()
        studio = controller.layoutStudio

        def settle():
            QTest.qWait(80)
            assert not errors, errors

        def walk(item):
            yield item
            for child in item.childItems():
                yield from walk(child)

        def named(name):
            matches = [
                i for i in walk(window.contentItem()) if i.objectName() == name and i.isVisible()
            ]
            assert matches, name
            return matches[0]

        def point(item):
            return item.mapToScene(QPointF(item.width() / 2, item.height() / 2)).toPoint()

        def reveal(item):
            item.forceActiveFocus(Qt.TabFocusReason)
            settle()
            return item

        def click(name):
            item = reveal(named(name))
            assert item.isEnabled(), name
            p = point(item)
            assert 0 <= p.x() < window.width() and 0 <= p.y() < window.height(), (name, p)
            QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, p)
            settle()

        def type_text(name, text):
            item = reveal(named(name))
            QTest.keyClick(window, Qt.Key_A, Qt.ControlModifier)
            for char in text:
                if char == "\n":
                    QTest.keyClick(window, Qt.Key_Return)
                    continue
                app.sendEvent(window, QKeyEvent(QEvent.KeyPress, 0, Qt.NoModifier, char))
                app.sendEvent(window, QKeyEvent(QEvent.KeyRelease, 0, Qt.NoModifier, char))
            QTest.keyClick(window, Qt.Key_Tab)
            settle()
            return item

        def choose(name, index):
            item = reveal(named(name))
            QTest.keyClick(window, Qt.Key_Home)
            for _ in range(index):
                QTest.keyClick(window, Qt.Key_Down)
            settle()
            assert item.property("currentIndex") == index

        def capture(name):
            path = output / (name + ".png")
            assert window.grabWindow().save(str(path))
            captures.append(str(path))

        def drag(source, target, feedback=None):
            item = reveal(named(source))
            start = point(item)
            end = point(named(target))
            QTest.mousePress(window, Qt.LeftButton, Qt.NoModifier, start)
            for step in range(1, 16):
                p = start + (end - start) * (step / 15)
                QTest.mouseMove(window, p, 16)
            settle()
            if feedback:
                drop = named(feedback)
                assert drop.property("containsDrag"), (source, target, "no drop feedback")
                if feedback.startswith("layout-drop-"):
                    assert drop.property("valid") == (
                        source != "layout-handle-0" or target != "layout-card-0"
                    )
                capture("drop-" + str(len(captures)) + "-" + feedback)
            QTest.mouseRelease(window, Qt.LeftButton, Qt.NoModifier, end)
            settle()

        settle()
        QTest.keyClick(window, Qt.Key_O, Qt.ControlModifier)
        settle()
        type_text("vault-directory", str(base / "vault"))
        click("vault-submit")
        assert controller.state["hasVault"]
        click("nav-week")
        assert controller.state["period"] == "week/2026-W44"
        click("open-layout-studio")
        click("layout-handle-0")
        click("studio-remove")
        assert not studio.draft.layout.blocks
        drag("palette-note", "layout-append", "layout-append-drop")
        assert len(studio.draft.layout.blocks) == 1
        checks.append("palette drag into empty canvas")
        click("layout-handle-0")
        type_text("studio-title", "First note")
        assert studio.draft.layout.blocks[0].title == "First note"
        click("studio-columns")
        click("palette-checklist")
        assert studio.draft.layout.positions()[1].column == 1
        drag("layout-handle-1", "layout-card-0", "layout-drop-0")
        assert studio.draft.layout.blocks[0].type == "checklist"
        checks.append("reorder existing components in two columns")
        before = studio.draft.layout
        drag("layout-handle-0", "layout-card-0", "layout-drop-0")
        assert studio.draft.layout == before
        checks.append("invalid same-component drop rejected")
        drag("palette-note", "studio-preview")
        assert studio.draft.layout == before
        checks.append("drop outside canvas rejected")
        click("layout-handle-0")
        click("studio-width")
        assert studio.draft.layout.blocks[0].placement.width == 2
        click("studio-down")
        click("studio-up")
        click("studio-duplicate")
        click("studio-remove")
        assert len(studio.draft.layout.blocks) == 2
        click("studio-columns")
        assert all(p.column == 0 for p in studio.draft.layout.positions())
        drag("layout-handle-1", "layout-card-0", "layout-drop-0")
        checks.append("resize, duplicate, remove, one-column reorder")
        before = studio.draft.layout
        QTest.keyClick(window, Qt.Key_Z, Qt.ControlModifier)
        settle()
        assert studio.draft.layout != before
        QTest.keyClick(window, Qt.Key_Z, Qt.ControlModifier | Qt.ShiftModifier)
        settle()
        assert studio.draft.layout == before
        # Essential operation entirely with focused keyboard button activation.
        reveal(named("palette-section"))
        QTest.keyClick(window, Qt.Key_Space)
        settle()
        assert studio.draft.layout.blocks[-1].type == "section"
        click("studio-enter")
        click("palette-note")
        type_text("studio-title", "Nested note")
        click("studio-back")
        assert studio.draft.layout.blocks[-1].config.children[0].title == "Nested note"
        checks.append("keyboard add and nested section editing")
        click("palette-selection_input")
        type_text("metric-name", "Mood")
        type_text("metric-options", "Low\nMedium\nHigh")
        click("metric-create")
        assert studio.draft.layout.blocks[-1].type == "selection_input"
        assert next(iter(studio.fields.values())).options == ("Low", "Medium", "High")
        checks.append("specialized selection configuration through dialog")
        click("palette-number_input")
        type_text("metric-name", "Minutes")
        type_text("metric-minimum", "0.5")
        type_text("metric-maximum", "100")
        click("metric-create")
        assert list(studio.fields.values())[-1].minimum == 0.5
        click("palette-table")
        choose("studio-source", 1)
        click("studio-bind")
        click("studio-bind")
        type_text("column-label-0", "Duration")
        click("column-down-0")
        click("column-remove-0")
        assert studio.draft.layout.blocks[-1].config.columns[0].label == "Duration"
        checks.append("table add, rename, reorder and remove columns through controls")
        click("palette-chart")
        click("chart-type-number")
        choose("chart-aggregation", 2)
        choose("chart-visualization", 1)
        type_text("chart-period", "month/2026-10")
        type_text("chart-tags", "study")
        config = studio.draft.layout.blocks[-1].config
        assert config.aggregation == "sum" and config.visualization == "line"
        assert config.selection.value_types == ("number",)
        before_error = studio.draft.layout
        type_text("chart-period", "day/2026-10-29")
        assert studio.message and studio.draft.layout == before_error
        capture("invalid-chart-period")
        type_text("chart-period", "week/2026-W44")
        assert not studio.message
        checks.append(
            "chart numeric filter, aggregation, visualization, tags, period and validation"
        )
        before = studio.draft.layout
        for theme in ("dark", "light"):
            controller.setTheme(theme)
            for width, height in ((640, 480), (1024, 768), (1440, 900), (1920, 1080)):
                window.setWidth(width)
                window.setHeight(height)
                settle()
                capture(f"{theme}-{width}")
                reveal(named("studio-title"))
                focused = window.activeFocusItem()
                assert focused is not None
                p = point(focused)
                assert 0 <= p.x() < width and 0 <= p.y() < height, (width, p)
                QTest.keyClick(window, Qt.Key_Tab)
                settle()
                assert window.activeFocusItem() is not focused
                capture(f"{theme}-{width}-properties-focus")
        controller.setReducedMotion(True)
        click("studio-preview")
        assert studio.draft.layout == before
        capture("preview-reduced-motion")
        click("studio-preview")
        click("studio-save")
        # Dialog standard button: activate the actual Qt control with pointer.
        buttons = [
            i
            for i in walk(window.contentItem())
            if i.isVisible() and i.property("text") in ("Save", "Salvar")
        ]
        assert buttons
        QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point(buttons[-1]))
        QThreadPool.globalInstance().waitForDone()
        settle()
        assert not studio.draft, studio.message
        expected = controller.state["composition"]["blocks"]
        assert len(expected) == len(before.blocks)
        capture("normal-page-saved")
        checks.append("preview, immutable save and return to normal page")
        controller.close()
        window.close()
        engine.deleteLater()
        app.sendPostedEvents(None, QEvent.DeferredDelete)
        expected_path = base / "expected.json"
        expected_path.write_text(json.dumps(expected), encoding="utf-8")
        restarted = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--reopen",
                str(base / "vault"),
                str(expected_path),
            ],
            capture_output=True,
            text=True,
            timeout=25,
        )
        assert restarted.returncode == 0, restarted.stdout + restarted.stderr
        assert not restarted.stderr, restarted.stderr
        checks.append(
            "independent application process reloads and renders identical saved composition"
        )
        # Fresh controller and QML engine reopen files, not an in-memory draft.
        controller = WorkspaceController(
            settings=QSettings(str(base / "prefs2"), QSettings.IniFormat), today=date(2026, 10, 29)
        )
        engine = QQmlApplicationEngine()
        engine.warnings.connect(lambda ws: errors.extend(w.toString() for w in ws))
        engine.setInitialProperties({"backend": controller})
        engine.load(
            QUrl.fromLocalFile(str(files("habit_workspace.presentation").joinpath("qml/Main.qml")))
        )
        window = engine.rootObjects()[0]
        window.requestActivate()
        settle()
        QTest.keyClick(window, Qt.Key_O, Qt.ControlModifier)
        settle()
        type_text("vault-directory", str(base / "vault"))
        click("vault-submit")
        click("nav-week")
        assert controller.state["composition"]["blocks"] == expected
        capture("reopened")
        checks.append(
            "fresh controller/engine reopen preserves component positions and configuration"
        )
        controller.close()
        window.close()
        engine.deleteLater()
        app.sendPostedEvents(None, QEvent.DeferredDelete)
        assert not errors, errors
        return dict(
            result="PASS",
            platform=app.platformName(),
            nativeWindowTest=app.platformName() in ("xcb", "wayland"),
            humanAccessibilityReview=False,
            checks=checks,
            captures=captures,
            qmlWarnings=errors,
        )


def verify_reopen(vault, expected_path):
    """A separate Qt process has no access to the editor's in-memory objects."""
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication([])
    with TemporaryDirectory() as temporary:
        controller = WorkspaceController(
            settings=QSettings(str(Path(temporary) / "prefs"), QSettings.IniFormat),
            today=date(2026, 10, 29),
        )
        controller.openVault(vault)
        controller.navigate("week", "2026-10-29")
        assert controller.state["composition"]["blocks"] == json.loads(
            Path(expected_path).read_text()
        )
        engine = QQmlApplicationEngine()
        errors = []
        engine.warnings.connect(lambda ws: errors.extend(w.toString() for w in ws))
        engine.setInitialProperties({"backend": controller})
        engine.load(
            QUrl.fromLocalFile(str(files("habit_workspace.presentation").joinpath("qml/Main.qml")))
        )
        QTest.qWait(200)
        assert engine.rootObjects() and not errors, errors
        window = engine.rootObjects()[0]
        output = Path("/tmp/habit-workspace-phase5") / app.platformName() / "restarted-process.png"
        assert window.grabWindow().save(str(output))
        controller.close()
        window.close()
        engine.deleteLater()
        app.sendPostedEvents(None, QEvent.DeferredDelete)
        assert not errors, errors
    return {"result": "PASS", "restartedProcess": True, "capture": str(output)}


if __name__ == "__main__":
    result = (
        verify_reopen(*sys.argv[2:])
        if len(sys.argv) > 1 and sys.argv[1] == "--reopen"
        else verify()
    )
    print(json.dumps(result, indent=2))
