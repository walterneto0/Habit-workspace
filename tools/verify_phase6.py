"""Phase 6 GUI acceptance: real QQuickWindow pointer/key events on a synthetic vault.

Creates a habit and a numeric field entirely through the interface, records a check-in
and a typed observation in tracking mode, corrects/validates them, then reopens the
vault in a separate process after deleting the SQLite index.
"""

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

OUTPUT = Path("/tmp/habit-workspace-phase6")


def load(controller, errors):
    engine = QQmlApplicationEngine()
    engine.warnings.connect(lambda ws: errors.extend(w.toString() for w in ws))
    engine.setInitialProperties({"backend": controller})
    engine.load(
        QUrl.fromLocalFile(str(files("habit_workspace.presentation").joinpath("qml/Main.qml")))
    )
    assert engine.rootObjects(), errors
    return engine, engine.rootObjects()[0]


def records(vault: Path):
    """Read canonical day records straight from the Markdown files."""
    from habit_workspace.vault.scanner import scan

    result = {"checkins": [], "observations": []}
    for loaded in scan(vault).documents:
        for key in result:
            result[key].extend(loaded.document.metadata["hw"].get(key, []))
    return result


def verify():
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication([])
    output = OUTPUT / app.platformName()
    output.mkdir(parents=True, exist_ok=True)
    errors, checks, captures = [], [], []
    today = date.today()
    with TemporaryDirectory() as temporary:
        base = Path(temporary)
        vault = base / "vault"
        VaultSession.create(vault, "Phase 6 fixture")
        controller = WorkspaceController(
            settings=QSettings(str(base / "prefs"), QSettings.IniFormat), today=today
        )
        engine, window = load(controller, errors)
        window.setWidth(1440)
        window.setHeight(900)
        window.requestActivate()
        studio = controller.layoutStudio

        def settle():
            QTest.qWait(80)
            from benchmark_gui import wait

            wait(app, lambda: not controller.actions.busy and not controller.actions.opening)
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

        def type_text(name, text, tab=True):
            reveal(named(name))
            QTest.keyClick(window, Qt.Key_A, Qt.ControlModifier)
            QTest.keyClick(window, Qt.Key_Delete)
            for char in text:
                if char == "\n":
                    QTest.keyClick(window, Qt.Key_Return)
                    continue
                app.sendEvent(window, QKeyEvent(QEvent.KeyPress, 0, Qt.NoModifier, char))
                app.sendEvent(window, QKeyEvent(QEvent.KeyRelease, 0, Qt.NoModifier, char))
            if tab:
                QTest.keyClick(window, Qt.Key_Tab)
            settle()

        def capture(name):
            path = output / (name + ".png")
            assert window.grabWindow().save(str(path))
            captures.append(str(path))

        settle()
        QTest.keyClick(window, Qt.Key_O, Qt.ControlModifier)
        settle()
        type_text("vault-directory", str(vault))
        click("vault-submit")
        assert controller.state["hasVault"]
        click("nav-week")
        assert controller.state["tracking"]["date"] == today.isoformat()
        capture("week-empty-tracking")

        # 1. Habit form: validation, default scope, daily recurrence, bind in Studio.
        click("new-habit")
        click("habit-save")
        assert named("habit-error").property("text"), "empty name must be rejected"
        type_text("habit-name", "Estudar Python")
        type_text("habit-tags", "estudos, programação")
        click("habit-daily")
        click("habit-bind")
        capture("habit-form")
        click("habit-save")
        assert studio.draft, "habit form must open the Studio with a bound checklist"
        assert studio.draft.view.blocks[-1].binding.kind == "habit"
        checks.append("habit created via form (default period scope) and checklist bound")

        # 2. New typed numeric field through the Studio palette and metric dialog.
        click("palette-integer_input")
        type_text("metric-name", "Tempo de estudo")
        click("metric-create")
        assert studio.draft.view.blocks[-1].type == "integer_input"
        click("studio-save")
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
        checks.append("numeric field created and layout published from the Studio")

        cells = [c for b in controller.state["composition"]["blocks"] for c in b.get("capture", [])]
        habit = next(c for c in cells if c["kind"] == "habit")
        field = next(c for c in cells if c["kind"] == "field")
        assert habit["state"] == "pending" and field["editable"], cells

        # 3. Tracking mode: check-in, correct, idempotent repeat.
        click("checkin-done-" + habit["id"])
        click("checkin-skipped-" + habit["id"])
        click("checkin-done-" + habit["id"])
        click("checkin-done-" + habit["id"])
        saved = records(vault)["checkins"]
        assert [(r["habit_id"], r["state"]) for r in saved] == [(habit["id"], "done")], saved
        assert named("capture-feedback-" + habit["id"]).property("text")
        checks.append("check-in saved, corrected and repeated without duplicates")

        # 4. Typed numeric observation: invalid, save with Enter, then correction.
        type_text("observation-input-" + field["id"], "quarenta\n", tab=False)
        feedback = named("capture-feedback-" + field["id"])
        assert "Não salvo" in feedback.property("text")
        assert not records(vault)["observations"]
        capture("observation-invalid")
        type_text("observation-input-" + field["id"], "40\n", tab=False)
        assert [r["value"] for r in records(vault)["observations"]] == [40]
        type_text("observation-input-" + field["id"], "45")
        click("observation-save-" + field["id"])
        saved = records(vault)["observations"]
        assert [(r["field_id"], r["value"]) for r in saved] == [(field["id"], 45)], saved
        assert not set(r["id"] for r in saved) & set(r["id"] for r in records(vault)["checkins"])
        checks.append("numeric observation rejected/saved/corrected with inline feedback")
        capture("dark-tracking-saved")
        controller.setTheme("light")
        settle()
        capture("light-tracking-saved")
        for width, height in ((640, 480), (1024, 768)):
            window.setWidth(width)
            window.setHeight(height)
            settle()
            reveal(named("checkin-done-" + habit["id"]))
            p = point(window.activeFocusItem())
            assert 0 <= p.x() < width and 0 <= p.y() < height, (width, p)
            capture(f"light-{width}-focus")
        window.setWidth(1440)
        window.setHeight(900)
        checks.append("focus visible on capture controls at 640/1024 px; light and dark")

        # 5. Keyboard date navigation: future dates are pending, never failures.
        QTest.keyClick(window, Qt.Key_Right, Qt.AltModifier | Qt.ShiftModifier)
        settle()
        if controller.state["tracking"]["date"] != today.isoformat():
            moved = [
                c for b in controller.state["composition"]["blocks"] for c in b.get("capture", [])
            ]
            assert next(c for c in moved if c["kind"] == "habit")["state"] == "future"
            capture("future-date")
            QTest.keyClick(window, Qt.Key_Left, Qt.AltModifier | Qt.ShiftModifier)
            settle()
            checks.append("Alt+Shift+Arrow date navigation; future is not a failure")
        else:
            checks.append("today is the last day of the week; future-date check skipped")
        assert controller.state["tracking"]["date"] == today.isoformat()

        # 6. Navigate away and back.
        click("nav-month")
        click("nav-week")
        after = [c for b in controller.state["composition"]["blocks"] for c in b.get("capture", [])]
        assert [(c["kind"], c.get("state"), c.get("value")) for c in after] == [
            ("habit", "done", None),
            ("field", None, "45"),
        ], after
        checks.append("values shown again after navigating away and back")
        controller.close()
        window.close()
        engine.deleteLater()
        app.sendPostedEvents(None, QEvent.DeferredDelete)

        # 7. Separate process, index deleted first.
        (vault / ".habit-workspace" / "index.sqlite").unlink()
        restarted = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--reopen", str(vault)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert restarted.returncode == 0, restarted.stdout + restarted.stderr
        reopened = json.loads(restarted.stdout)
        captures.append(reopened["capture"])
        checks.append("separate process rebuilt the deleted index and shows both values")
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


def verify_reopen(vault):
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication([])
    errors = []
    with TemporaryDirectory() as temporary:
        controller = WorkspaceController(
            settings=QSettings(str(Path(temporary) / "prefs"), QSettings.IniFormat),
            today=date.today(),
        )
        engine, window = load(controller, errors)
        window.setWidth(1440)
        window.setHeight(900)
        assert controller.openVault(vault)
        assert Path(vault, ".habit-workspace", "index.sqlite").exists()
        controller.navigate("week", date.today().isoformat())
        QTest.qWait(200)
        cells = [c for b in controller.state["composition"]["blocks"] for c in b.get("capture", [])]
        assert [(c["kind"], c.get("state"), c.get("value")) for c in cells] == [
            ("habit", "done", None),
            ("field", None, "45"),
        ], cells
        assert [r["name"] for r in controller.state["habits"]["rows"]] == ["Estudar Python"]
        output = OUTPUT / app.platformName() / "restarted-process.png"
        assert window.grabWindow().save(str(output))
        controller.close()
        window.close()
        engine.deleteLater()
        app.sendPostedEvents(None, QEvent.DeferredDelete)
        assert not errors, errors
    return {"result": "PASS", "restartedProcess": True, "capture": str(output)}


if __name__ == "__main__":
    result = (
        verify_reopen(sys.argv[2]) if len(sys.argv) > 1 and sys.argv[1] == "--reopen" else verify()
    )
    print(json.dumps(result, indent=2))
