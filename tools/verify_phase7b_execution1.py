"""Pointer and keyboard verification using a disposable vault."""

import json
from datetime import date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from benchmark_gui import wait
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest
from verify_phase65b import Journey

from habit_workspace.application.layouts import LayoutService, period_page
from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.layouts.components import Binding, Component, NoteConfig
from habit_workspace.domain.layouts.models import LayoutTemplate
from habit_workspace.domain.temporal import PeriodRef
from habit_workspace.presentation.controllers import WorkspaceController


def main():
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication([])
    with TemporaryDirectory(prefix="hw-7b-") as tmp:
        base = Path(tmp)
        vault = VaultSession.create(base / "vault", "Content")
        w = WorkspaceController(
            settings=QSettings(str(base / "prefs"), QSettings.IniFormat),
            today=date(2026, 10, 29),
        )
        ui = Journey(app, w)
        try:
            w.actions.openVault(str(vault.root))
            wait(app, lambda: w.state["hasVault"] and not w.actions.opening)
            w.content.create()
            ui.settle()
            ui.text("content-title", "Long note")
            ui.text("content-body", "Human **Markdown**")
            ui.focus(ui.named("content-save"))
            QTest.keyClick(ui.window, Qt.Key_Space)
            wait(app, lambda: not w.actions.busy and not w.content.form)
            ui.dialog_closed("ContentDialog")
            note = next(d for d in w.session.report.documents if d.document.kind == "note")
            w.content.edit(str(note.document.id))
            ui.settle()
            assert ui.named("content-body").property("text") == "Human **Markdown**"
            ui.text("content-body", "Edited note")
            ui.click("content-save")
            wait(app, lambda: not w.actions.busy and not w.content.form)
            ui.dialog_closed("ContentDialog")
            w.navigate("year", "2026-10-29")
            ui.settle()
            ui.click("new-goal")
            ui.text("planning-title", "Annual goal")
            ui.focus(ui.named("goal-cadence"))
            QTest.keyClick(ui.window, Qt.Key_Down)
            QTest.keyClick(ui.window, Qt.Key_Tab)
            ui.click("planning-save")
            wait(app, lambda: not w.actions.busy and not w.planning.form)
            ui.dialog_closed("PlanningDialog")
            w.navigate("month", "2026-10-29")
            ui.settle()
            row = w.state["planning"][0]
            assert row["followup_period"] == "month/2026-10", row
            ui.click("planning-edit-" + row["id"])
            ui.text("content-body", "Monthly reflection")
            ui.click("content-save")
            wait(app, lambda: not w.actions.busy and not w.content.form)
            ui.dialog_closed("ContentDialog")
            w.content.followup(row["id"], row["followup_period"])
            ui.settle()
            assert ui.named("content-body").property("text") == "Monthly reflection"
            ui.click("content-cancel")
            ui.dialog_closed("ContentDialog")
            # Install a page-local region and a separately linked standalone note.
            disk = VaultSession.open(vault.root)
            period = PeriodRef("week/2026-W44")
            region_id, linked_id = uuid4(), uuid4()
            layout = LayoutTemplate(
                uuid4(),
                1,
                "Content",
                (
                    Component(region_id, "note", "Page region", NoteConfig()),
                    Component(
                        linked_id,
                        "note",
                        "Linked note",
                        NoteConfig(),
                        binding=Binding(note.document.id, "note"),
                    ),
                ),
            )
            LayoutService(disk).save_revision(period, layout, datetime.now().astimezone())
            page = period_page(disk.report, period)
            from copy import deepcopy

            doc = deepcopy(page.document)
            doc.body = (
                f'Before<!-- hw:content id="{region_id}" -->Original<!-- /hw:content -->After'
            )
            page = disk.save(page, doc)
            w.actions.tasks.refresh()
            wait(app, lambda: not w.actions.tasks.active)
            w.navigate("week", "2026-10-29")
            ui.settle()
            ui.click("edit-content-" + str(region_id))
            ui.text("content-body", "Edited region")
            ui.click("content-save")
            wait(app, lambda: not w.actions.busy and not w.content.form)
            ui.dialog_closed("ContentDialog")
            assert VaultSession.open(vault.root).load(
                page.document.id
            ).document.body == doc.body.replace("Original", "Edited region")
            ui.click("edit-content-" + str(linked_id))
            assert ui.named("content-body").property("text") == "Edited note"
            ui.click("content-cancel")
            ui.dialog_closed("ContentDialog")
            vault.index.path.unlink()
            reopened = VaultSession.open(vault.root)
            assert reopened.load(note.document.id).document.body == "Edited note"
            goal = next(d for d in reopened.report.documents if d.document.kind == "goal")
            assert (
                goal.document.metadata["hw"]["followups"][0]["commentary"] == "Monthly reflection"
            )
            assert not ui.errors, ui.errors
            print(
                json.dumps(
                    dict(
                        result="PASS",
                        platform=app.platformName(),
                        qmlWarnings=ui.errors,
                        journeys=[
                            "note create/edit",
                            "keyboard save",
                            "goal monthly tracking",
                            "followup edit/reopen",
                            "index rebuild",
                            "page region",
                            "linked note",
                        ],
                    )
                )
            )
        finally:
            w.close()
            ui.engine.deleteLater()
            app.processEvents()


if __name__ == "__main__":
    main()
