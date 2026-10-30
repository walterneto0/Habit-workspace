"""Offscreen Qt input/render verification using generated temporary vaults only.

Usage: QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
.venv/bin/python tools/verify_phase2.py --output /tmp/habit-workspace-phase2
"""

import argparse
import json
import threading
from datetime import date
from importlib.resources import files
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from benchmark_gui import wait
from PySide6.QtCore import QObject, QPointF, QSettings, Qt, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest

from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.documents import Document
from habit_workspace.presentation.controllers import WorkspaceController


def verify(output: Path) -> dict:
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication([])
    app.setApplicationName("Habit Workspace verification")
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="habit-workspace-phase2-") as directory:
        base = Path(directory)
        settings = QSettings(str(base / "settings.ini"), QSettings.Format.IniFormat)
        controller = WorkspaceController(settings=settings, today=date(2026, 10, 29))
        engine = QQmlApplicationEngine()
        errors = []
        engine.warnings.connect(lambda warnings: errors.extend(w.toString() for w in warnings))
        engine.setInitialProperties({"backend": controller})
        engine.load(
            QUrl.fromLocalFile(str(files("habit_workspace.presentation").joinpath("qml/Main.qml")))
        )
        assert len(engine.rootObjects()) == 1, errors
        window = engine.rootObjects()[0]
        captures = []

        def settle():
            QTest.qWait(260)
            app.processEvents()
            assert not errors, "\n".join(errors)

        def capture(name, width=1200, height=800):
            window.setWidth(width)
            window.setHeight(height)
            settle()
            image = window.grabWindow()
            assert not image.isNull()
            path = output / (name + ".png")
            assert image.save(str(path))
            captures.append(str(path))

        def items():
            def walk(item):
                yield item
                for child in item.childItems():
                    yield from walk(child)

            return list(walk(window.contentItem()))

        def named(name):
            obj = window.findChild(QObject, name)
            if obj is None:
                obj = next((i for i in items() if i.objectName() == name), None)
            assert obj is not None, name
            return obj

        def click(item):
            assert isinstance(item, QQuickItem)
            assert item.isVisible() and item.isEnabled()
            point = item.mapToScene(QPointF(item.width() / 2, item.height() / 2))
            QTest.mouseClick(
                window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point.toPoint()
            )
            settle()

        settle()
        capture("welcome-dark")
        capture("welcome-compact", 640, 480)
        window.setWidth(1200)
        window.setHeight(800)
        settle()
        QTest.keyClick(window, Qt.Key.Key_O, Qt.KeyboardModifier.ControlModifier)
        settle()
        dialog = named("vault-dialog")
        assert dialog.property("visible")
        dialog.setProperty("creating", True)
        named("vault-name").setProperty("text", "Cofre de verificação")
        named("vault-directory").setProperty("text", str(base / "vault"))
        capture("create-dialog")
        capture("create-dialog-compact", 640, 480)
        window.setWidth(1200)
        window.setHeight(800)
        settle()
        create_entered, release_create = threading.Event(), threading.Event()
        create_descriptor = VaultSession.__dict__["create"]
        create_method = VaultSession.create

        def delayed_create(cls, directory, name):
            create_entered.set()
            assert release_create.wait(10), "test did not release the vault-create worker"
            return create_method(directory, name)

        VaultSession.create = classmethod(delayed_create)
        try:
            click(named("vault-submit"))
            assert create_entered.wait(2), "vault-create worker did not start"
            assert controller.state["openingVault"]
            submit = named("vault-submit")
            assert submit.property("text") == "Abrindo…"
            assert not submit.isEnabled()
            capture("create-dialog-loading")
            release_create.set()
            wait(
                app,
                lambda: (
                    not controller.state["openingVault"]
                    and (controller.state["hasVault"] or controller.state["noticeError"])
                ),
                timeout=10,
            )
        finally:
            release_create.set()
            VaultSession.create = create_descriptor
        assert controller.state["hasVault"], f"Vault creation failed: {controller.state['notice']}"
        wait(app, lambda: not dialog.property("visible"), timeout=5)
        assert not dialog.property("visible")
        capture("empty-vault")
        QTest.keyClick(window, Qt.Key.Key_B, Qt.KeyboardModifier.ControlModifier)
        settle()
        assert controller.state["sidebarCollapsed"]
        QTest.keyClick(window, Qt.Key.Key_B, Qt.KeyboardModifier.ControlModifier)
        settle()
        assert not controller.state["sidebarCollapsed"]
        click(named("nav-month"))
        assert controller.state["period"] == "month/2026-10"
        capture("calendar-dark")
        QTest.keyClick(window, Qt.Key.Key_Right, Qt.KeyboardModifier.AltModifier)
        settle()
        assert controller.state["period"] == "month/2026-11"
        # Real pointer input through the calendar cell, then ISO-week navigation.
        controller.navigate("month", "2026-10-29")
        settle()
        calendar_day = named("calendar-day-2026-10-29")
        calendar_day.forceActiveFocus(Qt.FocusReason.TabFocusReason)
        settle()
        click(calendar_day)
        assert controller.state["period"] == "day/2026-10-29"
        click(named("nav-week"))
        assert controller.state["period"] == "week/2026-W44"
        capture("week-dark")
        controller.setTheme("light")
        controller.navigate("month")
        capture("calendar-light", 1000, 740)
        capture("calendar-compact", 640, 480)
        # Keyboard focus must scroll offscreen controls into view at minimum size.
        last_day = named("calendar-day-2026-11-08")
        last_day.forceActiveFocus(Qt.FocusReason.TabFocusReason)
        settle()
        point = last_day.mapToScene(QPointF(0, 0))
        assert 60 <= point.y() <= window.height() - last_day.height()
        assert 64 <= point.x() <= window.width() - last_day.width()
        capture("calendar-compact-scrolled", 640, 480)
        QTest.keyClick(window, Qt.Key.Key_Space)
        settle()
        assert controller.state["period"] == "day/2026-11-08"
        window.setWidth(1000)
        window.setHeight(740)
        settle()
        click(named("nav-year"))
        assert controller.state["period"] == "year/2026"
        capture("year-light", 1000, 740)
        controller.navigate("settings")
        capture("settings-light", 1200, 900)
        controller.setReducedMotion(True)
        controller.setTheme("dark")
        controller.navigate("overview")
        # Generated fixture visibly labelled as verification content, never app seed data.
        source = VaultSession.create(base / "source", "Origem de verificação")
        doc = Document.from_metadata(
            {
                "hw": {
                    "schema_version": 4,
                    "kind": "day_page",
                    "id": str(uuid4()),
                    "date": "2026-10-29",
                    "title": "Página de verificação",
                    "tags": ["teste"],
                    "origin_page_id": str(uuid4()),
                }
            },
            "# Nota de verificação\n\nTexto criado apenas para validar a interface.\n"
            "![Não carregar imagem](https://example.invalid/remote.png)\n",
        )
        loaded = source.create_document("Elsewhere/day.md", doc)
        QTest.keyClick(window, Qt.Key.Key_I, Qt.KeyboardModifier.ControlModifier)
        settle()
        assert named("import-dialog").property("visible")
        assert controller.previewImport(str(loaded.path), False)
        capture("import-preview", 1000, 740)
        capture("import-preview-compact", 640, 480)
        window.setWidth(1000)
        window.setHeight(740)
        settle()
        confirmation = next(
            i for i in items() if i.property("text") == "Confirmar importação" and i.isVisible()
        )
        click(confirmation)
        assert controller.state["selected"]["id"] == str(doc.id)
        assert controller.state["issues"]
        capture("document-properties", 1440, 960)
        capture("document-compact", 640, 480)
        properties = next(
            i
            for i in items()
            if i.property("hint") == "Propriedades do documento" and i.isVisible()
        )
        properties.forceActiveFocus(Qt.FocusReason.TabFocusReason)
        settle()
        click(properties)
        capture("properties-drawer", 640, 480)
        QTest.keyClick(window, Qt.Key.Key_Escape)
        settle()
        QTest.keyClick(window, Qt.Key.Key_K, Qt.KeyboardModifier.ControlModifier)
        settle()
        assert named("document-search").hasActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Z)
        settle()
        assert not controller.state["documents"]
        controller.setQuery("")
        first_watcher = controller.watcher
        assert controller.openVault(str(source.root))
        assert not first_watcher.periodic.isActive()
        assert not first_watcher.paths
        controller.navigate("day", "2026-10-29")
        before = loaded.path.read_bytes()
        moved = loaded.path.with_name("renamed.md")
        loaded.path.rename(moved)
        controller.reindex()
        assert controller.state["documents"][0]["path"].endswith("renamed.md")
        controller.session.index.path.unlink()
        controller.reindex()
        assert moved.read_bytes() == before
        # All Qt-facing paths stay readable after malformed external changes.
        moved.write_bytes(b"broken")
        controller.reindex()
        assert controller.state["issues"]
        assert moved.read_bytes() == b"broken"
        controller.close()
        window.close()
        engine.deleteLater()
        app.processEvents()
        assert not errors, errors
        return {
            "result": "PASS",
            "qmlWarnings": errors,
            "captures": captures,
            "input": (
                "mouse, Ctrl+B, Ctrl+O, Ctrl+I, Ctrl+K, Alt+Right, keyboard scroll, Space, Esc"
            ),
            "renderer": "Qt Quick (selected by environment)",
            "nativeDesktopValidated": False,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("/tmp/habit-workspace-phase2"))
    args = parser.parse_args()
    print(json.dumps(verify(args.output), ensure_ascii=False, indent=2))
