"""Rendered nested-note and calendar-selector regressions, disposable vaults only."""

import argparse
import json
import subprocess
import sys
from copy import deepcopy
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

from habit_workspace.application.content import ContentService, regions
from habit_workspace.application.layouts import LayoutService, period_page
from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.layouts import (
    Binding,
    Component,
    LayoutTemplate,
    NoteConfig,
    SectionConfig,
)
from habit_workspace.domain.temporal import PeriodRef
from habit_workspace.presentation.controllers import WorkspaceController


def make_fixture(root, depth):
    s = VaultSession.create(root, "Nested notes")
    note = ContentService(s).create("Linked", "Original linked", "month/2026-10")
    explicit, implicit, linked, region = uuid4(), uuid4(), uuid4(), uuid4()
    children = (
        Component(explicit, "note", "Explicit region", NoteConfig(region)),
        Component(implicit, "note", "Block region", NoteConfig()),
        Component(
            linked, "note", "Linked", NoteConfig(), binding=Binding(note.document.id, "note")
        ),
    )
    for _ in range(depth):
        children = (Component(uuid4(), "section", "Section", SectionConfig(children)),)
    layout = LayoutTemplate(uuid4(), 1, "Nested", children)
    LayoutService(s).save_revision(PeriodRef("week/2026-W44"), layout, datetime.now().astimezone())
    page = period_page(s.report, PeriodRef("week/2026-W44"))
    doc = deepcopy(page.document)
    doc.body = (
        f'Before<!-- hw:content id="{region}" -->Original explicit<!-- /hw:content -->'
        f'Middle<!-- hw:content id="{implicit}" -->Original implicit<!-- /hw:content -->After'
    )
    s.save(page, doc)


def nested_notes(w):
    def walk(rows):
        for row in rows:
            if row["type"] == "section":
                yield from walk(row["children"])
            elif row["type"] == "note":
                yield row

    return list(walk(w.state["composition"]["blocks"]))


def verify(root, reopen=False):
    app = QGuiApplication.instance()
    w = WorkspaceController(
        today=date(2026, 10, 29),
        settings=QSettings(str(root.parent / "prefs"), QSettings.IniFormat),
    )
    ui = Journey(app, w)

    def saved():
        wait(app, lambda: not w.actions.busy and not w.content.form and not w.planning.form)
        ui.settle()

    def choose(name, index):
        ui.focus(ui.named(name))
        QTest.keyClick(ui.window, Qt.Key_Home)
        for _ in range(index):
            QTest.keyClick(ui.window, Qt.Key_Down)
        QTest.keyClick(ui.window, Qt.Key_Tab)
        ui.settle()

    try:
        w.actions.openVault(str(root))
        wait(app, lambda: w.state["hasVault"] and not w.actions.opening)
        w.navigate("week", "2026-10-29")
        ui.settle()
        if not reopen:
            # Save another version via the existing Studio, then reload the page.
            w.studio.open()
            w.studio.select(0)
            w.studio.edit("title", "Saved nested section")
            w.studio.prepare()
            w.studio.save()
            wait(app, lambda: not w.studio.busy and not w.studio.draft)
            w.navigate("day", "2026-10-29")
            w.navigate("week", "2026-10-29")
            w.actions.tasks.refresh()
            wait(app, lambda: not w.actions.tasks.active)
            ui.settle()
        notes = nested_notes(w)
        assert len(notes) == 3
        page = period_page(w.session.report, PeriodRef("week/2026-W44"))
        original = page.document.body
        for row, label in zip(notes, ("explicit", "implicit", "linked"), strict=True):
            ui.click("edit-content-" + row["id"])
            assert w.content.form["open"]
            assert (
                len([i for i in ui.walk() if i.objectName() == "content-body" and i.isVisible()])
                == 1
            )
            assert w.content.form["region"] == ("" if row["noteLinked"] else row["noteRegion"])
            assert str(w.content.loaded.document.id) == (row["noteLinked"] or str(page.document.id))
            expected = "Edited " + label
            if reopen:
                assert ui.named("content-body").property("text") == expected
                ui.click("content-cancel")
            else:
                ui.text("content-body", expected)
                ui.click("content-save")
                saved()
            ui.dialog_closed("ContentDialog")
        updated = VaultSession.open(root).load(page.document.id).document.body
        if not reopen:
            assert updated == original.replace("Original explicit", "Edited explicit").replace(
                "Original implicit", "Edited implicit"
            )
        assert len(regions(updated)) == 2

        if reopen:
            for doc in w.session.report.documents:
                if doc.document.kind in ("note", "review"):
                    w.content.edit(str(doc.document.id))
                    ui.settle()
                    assert ui.named("content-period").property("period") == doc.document.metadata[
                        "hw"
                    ].get("period", "")
                    ui.click("content-cancel")
                    ui.dialog_closed("ContentDialog")
            assert not ui.errors, ui.errors
            return dict(freshProcess=True, qmlWarnings=ui.errors)

        # Home period and cadence are independent; invalid choices preserve draft.
        w.navigate("year", "2026-10-29")
        w.planning.create("goal")
        ui.settle()
        ui.text("planning-title", "Calendar goal")
        assert ui.named("goal-home").property("period") == "year/2026"
        assert ui.named("goal-cadence").property("currentIndex") == 0
        choose("goal-cadence", 1)
        choose("goal-home-type", 4)
        choose("goal-home-month", 9)
        choose("goal-home-choice", 28)
        assert ui.named("goal-home").property("period") == "day/2026-10-29"
        assert ui.named("goal-cadence").property("currentIndex") == -1
        ui.click("planning-save")
        assert not w.actions.busy and w.planning.form["cadence"] == "month"
        assert w.planning.form["error"] and w.planning.form["title"] == "Calendar goal"
        choose("goal-home-type", 1)
        ui.click("planning-save")
        saved()
        ui.dialog_closed("PlanningDialog")
        goal = next(d.document for d in w.session.report.documents if d.document.kind == "goal")
        assert goal.metadata["hw"]["home_period_ref"] == "year/2026"
        assert goal.metadata["hw"]["tracking"] == dict(mode="periodic", granularity="month")

        w.navigate("notes")
        w.content.create()
        ui.settle()
        ui.text("content-title", "Unassociated")
        assert ui.named("content-period").property("period") == ""
        ui.click("content-save")
        saved()
        ui.dialog_closed("ContentDialog")

        w.navigate("week", "2026-12-31")
        w.content.createReview()
        ui.settle()
        ui.text("content-title", "Boundary review")
        ui.text("content-body", "Keep review draft")
        assert ui.named("content-period").property("period") == "week/2026-W53"
        assert ui.named("content-period-type").property("currentIndex") == 3
        screenshots = Path("/tmp/habit-workspace-phase7b1") / app.platformName()
        screenshots.mkdir(parents=True, exist_ok=True)
        assert ui.window.grabWindow().save(str(screenshots / "review-desktop.png"))
        ui.window.setWidth(640)
        ui.window.setHeight(480)
        ui.settle()
        assert ui.window.grabWindow().save(str(screenshots / "review-640.png"))
        ui.click("content-save")
        saved()
        ui.dialog_closed("ContentDialog")
        # Reopen the exact review at full size and reject a nonexistent week 53.
        review = next(d.document for d in w.session.report.documents if d.document.kind == "review")
        ui.window.setWidth(1440)
        ui.window.setHeight(1000)
        w.content.edit(str(review.id))
        ui.settle()
        ui.text("content-period-year", "2027")
        assert ui.named("content-period").property("period") == ""
        ui.click("content-save")
        assert not w.actions.busy and w.content.form["error"]
        assert ui.named("content-body").property("text") == "Keep review draft"
        ui.text("content-period-year", "2020")
        assert ui.named("content-period").property("period") == "week/2020-W53"
        ui.click("content-save")
        saved()
        ui.dialog_closed("ContentDialog")
        review = next(d.document for d in w.session.report.documents if d.document.kind == "review")
        assert review.metadata["hw"]["period"] == "week/2020-W53"
        assert "2021" in w.period_choices.label("week/2020-W53")
        assert not ui.errors, ui.errors
        return dict(nestedTargets=3, selector=True, qmlWarnings=ui.errors)
    finally:
        w.close()
        ui.window.close()
        ui.engine.deleteLater()
        app.processEvents()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--depth", type=int, default=2)
    parser.add_argument("--reopen", type=Path)
    args = parser.parse_args()
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication([])
    if args.reopen:
        print(json.dumps(verify(args.reopen, reopen=True)))
        return
    with TemporaryDirectory(prefix="hw-7b1-ux-") as tmp:
        root = Path(tmp) / "vault"
        make_fixture(root, args.depth)
        result = verify(root)
        (root / ".habit-workspace/index.sqlite").unlink()
        child = subprocess.run(
            [sys.executable, __file__, "--reopen", str(root)],
            capture_output=True,
            text=True,
            timeout=45,
        )
        assert child.returncode == 0, child.stdout + child.stderr
        assert not child.stderr, child.stderr
        print(
            json.dumps(
                dict(
                    result="PASS",
                    depth=args.depth,
                    platform=app.platformName(),
                    checks=result,
                    restart=json.loads(child.stdout),
                )
            )
        )


if __name__ == "__main__":
    main()
