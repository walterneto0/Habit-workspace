"""Rendered Qt Quick measurements used by benchmark_vault --gui.

Synthetic fixtures only. Heartbeat gaps measure GUI-thread unavailability, while
pointer-to-return and pointer-to-frame include synchronous slot work and rendering.
No arbitrary settle sleep is included in operation latency.
"""

import statistics
import time
from pathlib import Path

from PySide6.QtCore import QPointF, QSettings, Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest
from verify_phase6 import load

from habit_workspace.presentation.controllers import WorkspaceController


def summary(values):
    return dict(
        median_ms=round(statistics.median(values), 1), max_ms=round(max(values), 1), n=len(values)
    )


def wait(app, predicate, timeout=60):
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.001)  # yield the GIL while Qt workers perform Python I/O
    assert predicate(), "GUI condition timed out"


def measure_gui(root: Path, info: dict, repeat: int, settings_path: Path):
    from benchmark_vault import TODAY

    QQuickStyle.setStyle("Basic")
    app = QGuiApplication.instance() or QGuiApplication([])
    controller = WorkspaceController(
        settings=QSettings(str(settings_path), QSettings.IniFormat), today=TODAY
    )
    errors = []
    engine, window = load(controller, errors)
    window.setWidth(1440)
    window.setHeight(1000)
    window.requestActivate()
    frames = []
    window.frameSwapped.connect(lambda: frames.append(time.perf_counter()))
    wait(app, lambda: bool(frames))
    gaps, last = [], [time.perf_counter()]
    timer = QTimer()
    timer.setInterval(5)

    def tick():
        now = time.perf_counter()
        gaps.append(max(0, (now - last[0]) * 1000 - 5))
        last[0] = now

    timer.timeout.connect(tick)
    timer.start()
    results = {}

    def idle():
        actions = getattr(controller, "actions", None)
        return not actions or not actions.tasks or not actions.tasks.active

    def measure(name, action):
        wall, stalls, rendered, feedback = [], [], [], []
        for _ in range(repeat):
            wait(app, idle)
            complete = []
            gaps.clear()
            frames.clear()
            start = [0.0]

            def run(start=start, complete=complete):
                start[0] = time.perf_counter()
                action()
                complete.append(time.perf_counter())
                window.update()

            QTimer.singleShot(0, run)
            wait(app, lambda complete=complete: bool(complete) and bool(frames))
            feedback.append((frames[0] - start[0]) * 1000)
            wait(app, idle)
            finished = time.perf_counter()
            window.update()
            wait(app, lambda finished=finished: frames[-1] >= finished)
            tick()
            wall.append((complete[-1] - start[0]) * 1000)
            rendered.append((frames[-1] - start[0]) * 1000)
            stalls.append(max(gaps, default=0))
        results[name] = dict(
            slot=summary(wall),
            feedback=summary(feedback),
            rendered=summary(rendered),
            stall=summary(stalls),
        )

    def walk(item):
        yield item
        for child in item.childItems():
            yield from walk(child)

    def click(name):
        item = next(
            i for i in walk(window.contentItem()) if i.objectName() == name and i.isVisible()
        )
        item.forceActiveFocus(Qt.TabFocusReason)
        app.processEvents()
        point = item.mapToScene(QPointF(item.width() / 2, item.height() / 2)).toPoint()
        assert (
            item.isEnabled()
            and 0 <= point.x() < window.width()
            and 0 <= point.y() < window.height()
        ), (name, point)
        QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point)

    try:
        measure("warm_open", lambda: controller.openVault(str(root)))
        controller.watcher.periodic.stop()
        measure("navigate_week_pointer", lambda: click("nav-week"))
        refresh = getattr(controller.watcher, "_tick", controller.watcher.refresh)
        measure("watcher_unchanged", refresh)
        note = next((root / "Notes").iterdir())

        def modified():
            note.write_bytes(note.read_bytes() + b"\nexternal benchmark edit\n")
            refresh()

        measure("watcher_changed", modified)
        states = iter(["done", "skipped", "done"] * repeat)
        measure(
            "checkin_pointer", lambda: click("checkin-" + next(states) + "-" + info["habit_ids"][1])
        )
        field = info["field_id"]

        def typed():
            item = next(
                i
                for i in walk(window.contentItem())
                if i.objectName() == "observation-input-" + field and i.isVisible()
            )
            item.forceActiveFocus(Qt.TabFocusReason)
            app.processEvents()
            QTest.keyClick(window, Qt.Key_A, Qt.ControlModifier)
            QTest.keyClick(window, Qt.Key_Delete)
            QTest.keyClick(window, Qt.Key_4)
            QTest.keyClick(window, Qt.Key_2)
            QTest.keyClick(window, Qt.Key_Return)

        measure("typed_save_keyboard", typed)
        measure("navigate_day_pointer", lambda: click("nav-day"))
        measure("navigate_month_pointer", lambda: click("nav-month"))
        controller.watcher.periodic.start()
        end = time.monotonic() + 6
        wait(app, lambda: time.monotonic() >= end)
        wait(app, idle)
        results["periodic_stall_max_ms"] = round(max(gaps), 1)
        results["poll_interval_ms"] = controller.watcher.periodic.interval()
        assert not errors, errors
        results["qml_warnings"] = errors
    finally:
        timer.stop()
        controller.close()
        window.close()
        engine.deleteLater()
        app.processEvents()
    return results
