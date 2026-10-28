"""Actual Qt window and synthetic data only; offscreen is not native review."""

import json
from datetime import date
from importlib.resources import files
from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtCore import QSettings, Qt, QThreadPool, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest

from habit_workspace.presentation.controllers import WorkspaceController


def verify():
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication([])
    output = Path("/tmp/habit-workspace-phase5")
    output.mkdir(exist_ok=True)
    with TemporaryDirectory() as temporary:
        base = Path(temporary)
        controller = WorkspaceController(
            settings=QSettings(str(base / "prefs"), QSettings.IniFormat), today=date(2026, 10, 29)
        )
        controller.createVault(str(base / "vault"), "Cofre fictício")
        controller.navigate("week", "2026-10-29")
        engine = QQmlApplicationEngine()
        errors = []
        engine.warnings.connect(lambda ws: errors.extend(w.toString() for w in ws))
        engine.setInitialProperties({"backend": controller})
        engine.load(
            QUrl.fromLocalFile(str(files("habit_workspace.presentation").joinpath("qml/Main.qml")))
        )
        assert engine.rootObjects(), errors
        window = engine.rootObjects()[0]
        studio = controller.layoutStudio
        studio.open()
        studio.command("columns")
        for kind in ("checklist", "note", "chart"):
            studio.add(kind, "", "", "")
        studio.add("number_input", "", "Minutos de leitura", "estudos")
        studio.edit("placeholder", "Captura na Fase 6")
        studio.command("up")
        QTest.qWait(200)
        prior = studio.draft.layout
        QTest.keyClick(window, Qt.Key_Z, Qt.ControlModifier)
        QTest.qWait(100)
        assert studio.draft.layout != prior
        QTest.keyClick(window, Qt.Key_Z, Qt.ControlModifier | Qt.ShiftModifier)
        QTest.qWait(100)
        assert studio.draft.layout == prior
        captures = []
        for theme in ("dark", "light"):
            controller.setTheme(theme)
            for width, height in ((1024, 768), (1440, 900), (1920, 1080)):
                window.setWidth(width)
                window.setHeight(height)
                QTest.qWait(200)
                path = output / f"{theme}-{width}.png"
                assert window.grabWindow().save(str(path))
                captures.append(str(path))
        controller.setReducedMotion(True)
        studio.command("preview")
        QTest.qWait(200)
        assert studio.draft.layout == prior
        studio.prepare()
        studio.save()
        QThreadPool.globalInstance().waitForDone()
        app.processEvents()
        assert not studio.draft, studio.message
        QTest.qWait(200)
        assert controller.state["composition"]["blocks"]
        # Exercise every registered typed shape, including nested read-only preview.
        studio.open()
        for kind in (
            "text",
            "integer",
            "number",
            "date",
            "duration",
            "boolean",
            "selection",
            "rating",
            "time",
        ):
            studio.addConfigured(
                kind + "_input",
                "",
                "Example " + kind,
                "test",
                {"options": "Low\nHigh"} if kind == "selection" else {},
            )
        studio.command("preview")
        QTest.qWait(200)
        assert window.grabWindow().save(str(output / "all-typed-shapes.png"))
        studio.discard()
        assert not errors, errors
        controller.close()
        window.close()
        engine.deleteLater()
        app.processEvents()
        return dict(
            result="PASS",
            qmlWarnings=errors,
            captures=captures,
            nativeDesktopValidated=False,
            input="Ctrl+Z, Ctrl+Shift+Z; other operations through Qt adapter",
        )


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
