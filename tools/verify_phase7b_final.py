"""Pointer and keyboard verification using a disposable vault."""

import json
import os
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from benchmark_gui import wait
from PySide6.QtCore import QObject, QSettings, Qt, QUrl
from PySide6.QtGui import QGuiApplication, QImage
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest
from verify_phase65b import Journey

from habit_workspace.application.layouts import LayoutService, period_page
from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.layouts.components import Binding, Component, NoteConfig
from habit_workspace.domain.layouts.models import LayoutTemplate
from habit_workspace.domain.temporal import PeriodRef
from habit_workspace.presentation.controllers import WorkspaceController
from habit_workspace.presentation.layout_assets import markdown_images


def reopen_process(root):
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication([])
    w = WorkspaceController(
        today=date(2026, 10, 29),
        settings=QSettings(str(Path(root).parent / "child-prefs"), QSettings.IniFormat),
    )
    ui = Journey(app, w)
    try:
        w.actions.openVault(root)
        wait(app, lambda: w.state["hasVault"] and not w.actions.opening)
        report = w.session.report
        assert len([d for d in report.documents if d.document.kind == "goal"]) == 1
        goal = next(d for d in report.documents if d.document.kind == "goal")
        assert goal.document.metadata["hw"]["followups"][0]["commentary"] == "Monthly reflection"
        review = next(d for d in report.documents if d.document.kind == "review")
        assert review.document.metadata["hw"]["period"] == "week/2026-W53"
        note = next(d for d in report.documents if d.document.kind == "note")
        assert markdown_images(w.session.root, note.document.body)[0]["source"]
        w.content.edit(str(note.document.id))
        ui.settle()
        ui.click("content-preview")
        wait(app, lambda: not w.actions.busy)
        ui.settle()
        images = [i for i in ui.walk() if i.objectName() == "local-image" and i.isVisible()]
        assert images and any(i.property("decoded") for i in images)
        ui.click("content-cancel")
        ui.dialog_closed("ContentDialog")
        w.navigate("week", "2026-10-29")
        ui.settle()
        assert any(b.get("imageSource") for b in w.state["composition"]["blocks"])
        assert not ui.errors, ui.errors
        print(json.dumps({"result": "PASS", "freshProcess": True, "renderedImages": True}))
    finally:
        w.close()
        ui.engine.deleteLater()
        app.processEvents()


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
            ui.click("planning-save")
            wait(app, lambda: not w.actions.busy and not w.planning.form)
            ui.dialog_closed("PlanningDialog")
            goal_id = w.state["planning"][0]["id"]
            for scale in ("month", "week", "day"):
                w.navigate(scale, "2026-10-29")
                assert not w.state["planning"], (scale, w.state["planning"])
            w.navigate("year", "2026-10-29")
            ui.settle()
            ui.click("planning-edit-" + goal_id)
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
            # Period review: one ISO week across the year boundary.
            w.navigate("week", "2026-12-31")
            w.content.createReview()
            ui.settle()
            ui.text("content-title", "Year boundary review")
            ui.text("content-body", "Weekly commentary")
            ui.text("review-rating", "4")
            ui.click("content-save")
            wait(app, lambda: not w.actions.busy and not w.content.form)
            ui.dialog_closed("ContentDialog")
            review = next(d for d in w.session.report.documents if d.document.kind == "review")
            assert review.document.metadata["hw"]["period"] == "week/2026-W53"

            w.content.edit(str(note.document.id))
            ui.settle()
            ui.text("image-alt", "Local illustration")
            image_path = base / "local.png"
            image = QImage(30, 20, QImage.Format_RGB32)
            image.fill(0xFF336699)
            assert image.save(str(image_path))
            # Exercise chooser opening, then its selection callback deterministically.
            ui.click("content-image-select")
            picker = ui.window.findChild(QObject, "note-image-picker")
            assert picker is not None
            assert picker.setProperty("selectedFile", QUrl.fromLocalFile(str(image_path)))
            picker.accepted.emit()
            picker.close()
            wait(
                app,
                lambda: (
                    not w.actions.busy
                    and (
                        w.content.form.get("imageRevision", 0) == 1
                        or bool(w.content.form.get("error"))
                    )
                ),
                timeout=10,
            )
            assert not w.content.form.get("error"), w.content.form
            ui.settle()
            assert "![Local illustration](Assets/" in ui.named("content-body").property("text")
            ui.click("content-save")
            wait(app, lambda: not w.actions.busy and not w.content.form)
            ui.dialog_closed("ContentDialog")
            note = VaultSession.open(vault.root).load(note.document.id)
            expected_body = note.document.body
            assert markdown_images(vault.root, expected_body)[0]["source"]

            # Import the same local image into an image layout block asynchronously.
            w.navigate("week", "2026-10-29")
            w.studio.open()
            w.studio.add("image", "", "", "")
            w.studio.importImage(str(image_path))
            wait(app, lambda: not w.actions.busy and not w.studio.busy)
            w.studio.edit("alt", "Layout illustration")
            w.studio.prepare()
            w.studio.save()
            wait(app, lambda: not w.studio.busy)
            assert not w.studio.draft, w.studio.message
            ui.settle()
            assert any(b.get("imageSource") for b in w.state["composition"]["blocks"])

            # New controller/engine models a complete app restart, then rebuild index.
            w.close()
            ui.engine.deleteLater()
            app.processEvents()
            w = WorkspaceController(
                settings=QSettings(str(base / "prefs"), QSettings.IniFormat),
                today=date(2026, 10, 29),
            )
            ui = Journey(app, w)
            w.actions.openVault(str(vault.root))
            wait(app, lambda: w.state["hasVault"] and not w.actions.opening)
            w.content.edit(str(note.document.id))
            ui.settle()
            assert ui.named("content-body").property("text") == expected_body
            w.content.previewImages(expected_body)
            wait(app, lambda: not w.actions.busy)
            assert w.content.form["images"][0]["source"]
            ui.click("content-cancel")
            ui.dialog_closed("ContentDialog")
            w.content.edit(str(review.document.id))
            ui.settle()
            assert ui.named("review-rating").property("text") == "4"
            ui.click("content-cancel")
            ui.dialog_closed("ContentDialog")
            vault.index.path.unlink()
            reopened = VaultSession.open(vault.root)
            assert reopened.load(note.document.id).document.body == expected_body
            goal = next(d for d in reopened.report.documents if d.document.kind == "goal")
            assert (
                goal.document.metadata["hw"]["followups"][0]["commentary"] == "Monthly reflection"
            )
            assert (
                reopened.load(review.document.id).document.metadata["hw"]["period"]
                == "week/2026-W53"
            )
            assert markdown_images(vault.root, expected_body)[0]["source"]
            assert reopened.load(page.document.id).document.body == doc.body.replace(
                "Original", "Edited region"
            )
            assert not ui.errors, ui.errors
            child = subprocess.run(
                [sys.executable, __file__, "--reopen", str(vault.root)],
                env=dict(os.environ),
                capture_output=True,
                text=True,
                timeout=45,
            )
            assert child.returncode == 0, child.stdout + child.stderr
            child_result = json.loads(child.stdout)
            assert child_result["freshProcess"] and child_result["renderedImages"]
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
                            "review",
                            "local image selection/import/display",
                            "layout image",
                            "application restart in fresh process",
                            "home-only isolation",
                        ],
                    )
                )
            )
        finally:
            w.close()
            ui.engine.deleteLater()
            app.processEvents()


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--reopen":
        reopen_process(sys.argv[2])
    else:
        main()
