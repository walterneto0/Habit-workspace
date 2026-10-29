"""Phase 6.5A GUI check: date rollover and historical-layout label in the real QML window.

Synthetic temporary vault only. A ManualClock stands in for midnight; the controller's
own date timer (shortened) performs the change, then a real pointer click records the
next day's check-in. Writes screenshots to /tmp/habit-workspace-phase65a/<platform>/.
Offscreen/X11 rendering is not a substitute for human accessibility review.
"""

import json
from datetime import datetime
from importlib.resources import files
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from PySide6.QtCore import QPointF, QSettings, Qt, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest

from habit_workspace.application.habits import HabitService
from habit_workspace.application.layouts import LayoutService
from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.layouts import (
    Binding,
    ChecklistConfig,
    Component,
    InputConfig,
    LayoutTemplate,
)
from habit_workspace.domain.metrics import FieldDefinition, SourceSelection
from habit_workspace.domain.temporal import PeriodRef
from habit_workspace.presentation.clock import ManualClock
from habit_workspace.presentation.controllers import WorkspaceController
from habit_workspace.vault.scanner import scan

OUTPUT = Path("/tmp/habit-workspace-phase65a")


def local(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute).astimezone()


def fixture(vault: Path):
    """Week 2026-W44: checklist from Monday, a typed field added Thursday 10:00."""
    session = VaultSession.create(vault, "Fase 6.5A")
    habit = HabitService(session).create(
        name="Estudar Python", period=PeriodRef("week/2026-W44"), tags=("estudos",)
    )
    week = PeriodRef("week/2026-W44")
    service = LayoutService(session)
    checklist = Component(
        uuid4(),
        "checklist",
        "Rotina",
        ChecklistConfig(SourceSelection("by_tags", tags=("estudos",), value_types=("habit",))),
    )
    v1 = LayoutTemplate(uuid4(), 1, "Semana de estudo", (checklist,))
    service.save_revision(week, v1, local(2026, 10, 26, 0))
    activation = local(2026, 10, 29, 10)
    field = FieldDefinition(uuid4(), "Minutos de leitura", "integer", activation)
    block = Component(
        uuid4(),
        "integer_input",
        field.name,
        InputConfig("integer"),
        binding=Binding(field.id, "metric"),
    )
    service.save_revision(
        week, v1.new_revision(blocks=(checklist, block)), activation, new_fields=(field,)
    )
    return str(habit.habit.id)


def verify():
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication([])
    output = OUTPUT / app.platformName()
    output.mkdir(parents=True, exist_ok=True)
    errors, checks, captures = [], [], []
    clock = ManualClock(local(2026, 10, 29, 23, 59))
    with TemporaryDirectory() as temporary:
        base = Path(temporary)
        habit = fixture(base / "vault")
        controller = WorkspaceController(
            settings=QSettings(str(base / "prefs"), QSettings.IniFormat), clock=clock
        )
        assert controller.openVault(str(base / "vault"))
        engine = QQmlApplicationEngine()
        engine.warnings.connect(lambda ws: errors.extend(w.toString() for w in ws))
        engine.setInitialProperties({"backend": controller})
        engine.load(
            QUrl.fromLocalFile(str(files("habit_workspace.presentation").joinpath("qml/Main.qml")))
        )
        assert engine.rootObjects(), errors
        window = engine.rootObjects()[0]
        window.setWidth(1280)
        window.setHeight(860)

        def settle(ms=80):
            QTest.qWait(ms)
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

        def click(name):
            item = named(name)
            item.forceActiveFocus(Qt.TabFocusReason)
            settle()
            point = item.mapToScene(QPointF(item.width() / 2, item.height() / 2)).toPoint()
            assert 0 <= point.x() < window.width() and 0 <= point.y() < window.height(), name
            QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point)
            settle()

        def capture(name):
            path = output / f"{name}.png"
            assert window.grabWindow().save(str(path))
            captures.append(str(path))

        def check(name, condition):
            assert condition, name
            checks.append(name)

        settle()
        controller.navigate("week", "2026-10-29")
        settle()
        label = named("capture-date").property("text")
        check("before midnight the tracking date is today", "29 de outubro" in label)
        check("today label", label.endswith(" · hoje"))
        capture("before-midnight")

        # Midnight: the controller's own timer notices the new civil date.
        controller.date_timer.setInterval(50)
        clock.set(local(2026, 10, 30, 0, 0))
        settle(300)
        label = named("capture-date").property("text")
        check("timer moved the followed day after midnight", "30 de outubro" in label)
        check("new day is today", label.endswith(" · hoje"))
        click(f"checkin-done-{habit}")
        records = [
            (r["date"], r["state"])
            for d in scan(base / "vault").documents
            for r in d.document.metadata["hw"].get("checkins", ())
        ]
        check("pointer check-in written to the new day", records == [("2026-10-30", "done")])
        capture("after-midnight-checkin")

        # Historical day: the current layout is labelled, not presented as that day's.
        controller.setCaptureDate("2026-10-27")
        settle()
        notice = named("layout-notice").property("text")
        check("pre-activation day shows a historical notice", "versão 1" in notice)
        capture("pre-activation-notice")
        controller.setCaptureDate("2026-10-30")
        settle()
        check(
            "notice hidden on a current day",
            not [
                i
                for i in walk(window.contentItem())
                if i.objectName() == "layout-notice" and i.isVisible()
            ],
        )
        controller.close()
        engine.deleteLater()
        settle()
    result = {
        "result": "PASS",
        "platform": app.platformName(),
        "checks": checks,
        "captures": captures,
        "qmlWarnings": errors,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(verify())
