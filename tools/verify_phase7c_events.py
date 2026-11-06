"""Rendered event/agenda acceptance with real input and fresh-process restart.

Only disposable synthetic vaults are used. Also run with QT_QPA_PLATFORM=xcb.
"""

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from benchmark_gui import wait
from PySide6.QtCore import QEvent, QSettings, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest
from verify_phase65b import Journey

from habit_workspace.application.habits import HabitService
from habit_workspace.application.planning import PlanningService
from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.temporal import PeriodRef
from habit_workspace.presentation.controllers import WorkspaceController


def verify(root, reopen=False):
    app = QGuiApplication.instance()
    w = WorkspaceController(
        today=date(2027, 1, 2), settings=QSettings(str(root.parent / "prefs"), QSettings.IniFormat)
    )
    ui = Journey(app, w)
    captures = Path("/tmp/habit-workspace-phase7c") / app.platformName()
    captures.mkdir(parents=True, exist_ok=True)

    def saved():
        wait(app, lambda: not w.actions.busy and not w.events.form)
        ui.settle()
        assert not w.events.form

    def choose_zone(search, identifier):
        ui.text("event-zone-search", search)
        ui.focus(ui.named("event-zone"))
        QTest.keyClick(ui.window, Qt.Key_Space)
        QTest.keyClick(ui.window, Qt.Key_Home)
        QTest.keyClick(ui.window, Qt.Key_Return)
        ui.settle()
        assert identifier in ui.named("event-zone-selected").property("text")

    def row_click(row):
        ui.click("calendar-day-" + row["display_day"])
        ui.click("agenda-open-" + row["source_id"] + "-" + row["display_day"])

    try:
        w.actions.openVault(str(root))
        wait(app, lambda: w.state["hasVault"] and not w.actions.opening)
        w.navigate("week", "2027-01-01")
        ui.settle()
        if not reopen:
            ui.window.setWidth(800)
            ui.window.setHeight(640)
            ui.settle()
            ui.click("calendar-new")
            ui.click("calendar-new-event")
            ui.text("event-titleInput", "Overnight meeting")
            ui.text("event-start", "31/12/2026")
            ui.text("event-end", "01/01/2027")
            ui.text("event-startTime", "23:00")
            ui.text("event-endTime", "02:00")
            choose_zone("Recife", "America/Recife")
            assert ui.window.grabWindow().save(str(captures / "small-event-form.png"))
            ui.click("event-save")
            saved()
            event = next(r for r in w.state["agenda"] if r["title"] == "Overnight meeting")
            row_click(event)
            assert w.events.form["timezone"] == "America/Recife"
            # External edits never replace the user's draft or get overwritten.
            loaded = w.events.loaded
            loaded.path.write_bytes(loaded.path.read_bytes() + b"\nExternal text")
            original = loaded.path.read_bytes()
            ui.text("event-titleInput", "Draft after external edit")
            ui.click("event-save")
            wait(app, lambda: not w.actions.busy)
            assert w.events.form["title"] == "Draft after external edit"
            assert "rascunho preservado" in w.events.form["error"]
            assert loaded.path.read_bytes() == original
            ui.click("event-cancel")
            row_click(event)
            ui.focus(ui.named("event-save"))
            QTest.keyClick(ui.window, Qt.Key_Space)
            saved()
            ui.click("calendar-new")
            ui.click("calendar-new-event")
            ui.text("event-titleInput", "Conference")
            ui.click("event-all-day")
            ui.text("event-start", "31/12/2026")
            ui.text("event-end", "02/01/2027")
            choose_zone("Recife", "America/Recife")
            ui.click("event-save")
            saved()
            # DST gap keeps text and creates no file; fold choices are accessible.
            ui.click("calendar-new")
            ui.click("calendar-new-event")
            ui.text("event-titleInput", "Invalid DST draft")
            ui.text("event-start", "08/03/2026")
            ui.text("event-end", "08/03/2026")
            ui.text("event-startTime", "02:30")
            ui.text("event-endTime", "04:00")
            choose_zone("New York", "America/New_York")
            ui.click("event-save")
            assert "não existe" in w.events.form["error"]
            assert ui.named("event-titleInput").property("text") == "Invalid DST draft"
            ui.text("event-start", "01/11/2026")
            ui.text("event-end", "01/11/2026")
            ui.text("event-startTime", "01:30")
            ui.focus(ui.named("event-start-choice"))
            QTest.keyClick(ui.window, Qt.Key_Space)
            QTest.keyClick(ui.window, Qt.Key_End)
            QTest.keyClick(ui.window, Qt.Key_Return)
            ui.settle()
            assert ui.named("event-start-choice").property("currentIndex") == 1
            ui.click("event-cancel")
        w.navigate("week", "2027-01-01")
        ui.settle()
        rows = w.state["agenda"]
        timed = [r for r in rows if r["title"] == "Overnight meeting"]
        all_day = [r for r in rows if r["title"] == "Conference"]
        assert len(timed) == 2 and len(all_day) == 3
        assert len({r["source_id"] for r in timed}) == 1
        assert "Continuação" in timed[1]["time_label"]
        assert timed[1]["end_time"] == "02:00"
        assert all(r["all_day"] for r in all_day)
        ui.click("calendar-day-2027-01-01")
        assert "Conference" in w.events.dayPreview("2027-01-01")
        ui.focus(ui.named("calendar-day-2027-01-01"))
        assert "Conference" in ui.named("calendar-day-2027-01-01").property("hint")
        ui.click("calendar-collapse")
        ui.click("calendar-collapse")
        ui.click("calendar-expand")
        ui.click("calendar-expand")
        # Full window for workspace navigation and day-group rendering.
        ui.window.setWidth(1200)
        ui.window.setHeight(900)
        ui.settle()
        assert ui.window.grabWindow().save(
            str(captures / ("restarted.png" if reopen else "agenda.png"))
        )
        task = next(r for r in rows if r["source_kind"] == "task")
        row_click(task)
        assert w.planning.form["title"] == "Deadline outside scope"
        ui.click("planning-cancel")
        habit = next(
            r for r in rows if r["source_kind"] == "habit" and r["display_day"] == "2027-01-01"
        )
        before = {d.path: d.path.read_bytes() for d in w.session.report.documents}
        row_click(habit)
        assert w.state["period"] == "day/2027-01-01"
        assert w.state["selected"]["id"] == habit["source_id"]
        assert w.state["selected"]["habit"]["date"] == "2027-01-01"
        assert w.state["selected"]["habit"]["state"] == "unrecorded"
        assert all(p.read_bytes() == data for p, data in before.items())
        assert len(w.session.report.documents) == 4
        assert not any(d.document.kind == "day_page" for d in w.session.report.documents)
        w.navigate("year", "2027-01-01")
        ui.settle()
        assert len(w.state["agenda"]) < 40  # only one bounded 31-day window
        w.navigate("month", "2027-01-01")
        ui.settle()
        assert len([r for r in w.state["agenda"] if r["source_kind"] == "task"]) == 1
        ui.click("calendar-day-2027-01-12")
        ui.click("calendar-new")
        ui.click("calendar-new-note")
        assert w.content.form["period"] == "day/2027-01-12"
        w.content.cancel()
        return dict(
            platform=app.platformName(),
            restart=reopen,
            timed_rows=2,
            all_day_rows=3,
            canonical_files=4,
            task_navigation=True,
            habit_day_navigation=True,
            pointer=True,
            keyboard=True,
            qmlWarnings=ui.errors,
        )
    finally:
        w.close()
        ui.window.close()
        ui.engine.deleteLater()
        app.sendPostedEvents(None, QEvent.DeferredDelete)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reopen", type=Path)
    args = parser.parse_args()
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication([])
    if args.reopen:
        print(json.dumps(verify(args.reopen, True)))
        return
    with TemporaryDirectory(prefix="hw-7c-") as tmp:
        root = Path(tmp) / "vault"
        s = VaultSession.create(root, "Events")
        PlanningService(s).create(
            kind="task",
            title="Deadline outside scope",
            period=PeriodRef("year/2025"),
            due_date=date(2027, 1, 1),
        )
        HabitService(s).create(name="Read", period=PeriodRef("week/2026-W53"))
        result = verify(root)
        s.index.path.unlink()
        child = subprocess.run(
            [sys.executable, __file__, "--reopen", str(root)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert child.returncode == 0, child.stdout + child.stderr
        print(json.dumps(dict(initial=result, fresh_process=json.loads(child.stdout))))
    app.processEvents()


if __name__ == "__main__":
    main()
