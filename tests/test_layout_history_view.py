"""Phase 6.5A: tracking shows the period's current layout and labels other revisions.

A revision activated midweek must not be presented as "the layout of" an earlier
day, must not unlock pre-activation capture, and reading never writes files.
"""

from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from PySide6.QtCore import QCoreApplication, QSettings
from test_layouts import ACTIVE, START, WEEK

from habit_workspace.application.layouts import LayoutService
from habit_workspace.domain.layouts import (
    Binding,
    Component,
    InputConfig,
    LayoutTemplate,
    NoteConfig,
)
from habit_workspace.domain.metrics import FieldDefinition
from habit_workspace.presentation.clock import ManualClock
from habit_workspace.presentation.controllers import WorkspaceController
from habit_workspace.presentation.tracking import instant_label, layout_notice

# Local civil dates of the fixed instants, whatever the machine's time zone.
ACTIVATION_DAY = ACTIVE.astimezone().date()
BEFORE_DAY = ACTIVATION_DAY - timedelta(days=2)
AFTER_DAY = ACTIVATION_DAY + timedelta(days=1)


def canonical_bytes(root: Path) -> dict:
    return {
        p.relative_to(root): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file() and ".habit-workspace" not in p.parts
    }


@pytest.fixture
def world(tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    clock = ManualClock(ACTIVE + timedelta(days=1, hours=2))
    settings = QSettings(str(tmp_path / "prefs.ini"), QSettings.Format.IniFormat)
    desktop = WorkspaceController(settings=settings, clock=clock)
    assert desktop.createVault(str(tmp_path / "vault"), "Histórico")
    layouts = LayoutService(desktop.session)
    v1 = LayoutTemplate(
        uuid4(), 1, "Semana de estudo", (Component(uuid4(), "note", "Notas", NoteConfig()),)
    )
    layouts.save_revision(WEEK, v1, START)
    field = FieldDefinition(uuid4(), "Minutos de leitura", "integer", ACTIVE)
    v2 = v1.new_revision(
        blocks=v1.blocks
        + (
            Component(
                uuid4(),
                "integer_input",
                field.name,
                InputConfig("integer"),
                binding=Binding(field.id, "metric"),
            ),
        )
    )
    layouts.save_revision(WEEK, v2, ACTIVE, new_fields=(field,))
    desktop.session.scan()
    desktop.navigate("week", AFTER_DAY.isoformat())
    yield desktop, layouts, v1, v2, field, clock
    desktop.close()
    app.processEvents()


def field_cell(desktop, field):
    return next(
        c
        for b in desktop.state["composition"]["blocks"]
        for c in b.get("capture", [])
        if c["id"] == str(field.id)
    )


def test_current_layout_resolution_is_used_and_labelled(world):
    desktop, _, _, v2, field, _ = world
    composition = desktop.state["composition"]
    assert [b["title"] for b in composition["blocks"]] == ["Notas", field.name]
    assert composition["activation"] == instant_label(ACTIVE)
    assert composition["layoutNotice"] == ""
    assert field_cell(desktop, field)["editable"]


def test_pre_activation_day_is_labelled_and_capture_stays_refused(world):
    desktop, _, _, _, field, _ = world
    desktop.setCaptureDate(BEFORE_DAY.isoformat())
    composition = desktop.state["composition"]
    notice = composition["layoutNotice"]
    assert "Exibindo o layout atual do período" in notice
    assert "“Semana de estudo” · versão 1" in notice and " era " in notice
    assert "nem contam como falha" in notice
    # Still the current composition; the new field is shown but not editable that day.
    assert [b["title"] for b in composition["blocks"]][-1] == field.name
    cell = field_cell(desktop, field)
    assert not cell["editable"] and "ativo desde" in cell["note"]
    before = canonical_bytes(desktop.session.root)
    assert not desktop.saveObservation(str(field.id), "", "30", "null")
    assert "anterior à ativação" in desktop.state["notice"]
    assert canonical_bytes(desktop.session.root) == before


def test_activation_day_mentions_the_midday_change(world):
    desktop, *_ = world
    desktop.setCaptureDate(ACTIVATION_DAY.isoformat())
    notice = desktop.state["composition"]["layoutNotice"]
    assert notice.startswith("Este layout passou a valer durante este dia, às ")
    assert f"{ACTIVE.astimezone():%H:%M}" in notice


def test_day_before_any_assignment_names_the_basic_layout(tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    desktop = WorkspaceController(
        settings=QSettings(str(tmp_path / "p.ini"), QSettings.Format.IniFormat),
        clock=ManualClock(ACTIVE + timedelta(days=1)),
    )
    try:
        desktop.createVault(str(tmp_path / "vault"), "Básico")
        layout = LayoutTemplate(uuid4(), 1, "Meio da semana", ())
        LayoutService(desktop.session).save_revision(WEEK, layout, ACTIVE)
        desktop.session.scan()
        desktop.navigate("week", BEFORE_DAY.isoformat())
        desktop.setCaptureDate(BEFORE_DAY.isoformat())
        assert "era o layout básico" in desktop.state["composition"]["layoutNotice"]
    finally:
        desktop.close()
        app.processEvents()


def test_future_scheduled_revision_uses_future_tense(world):
    desktop, layouts, _, v2, _, clock = world
    v3 = v2.new_revision(name="Fim de semana")
    later = ACTIVE + timedelta(days=2)
    layouts.save_revision(WEEK, v3, later)
    report = desktop.session.scan()
    current = LayoutService.resolve_report(report, WEEK, clock.now())
    assert current.layout == v2
    day = later.astimezone().date()
    notice = layout_notice(report, WEEK, day, AFTER_DAY, current)
    assert "será “Fim de semana” · versão 3" in notice


def test_reading_and_navigating_history_never_writes(world):
    desktop, layouts, *_ = world
    root = desktop.session.root
    before = canonical_bytes(root)
    for day in (BEFORE_DAY, ACTIVATION_DAY, AFTER_DAY, BEFORE_DAY):
        desktop.setCaptureDate(day.isoformat())
        LayoutService.resolve_report(desktop.session.report, WEEK, ACTIVE - timedelta(days=1))
    desktop.navigate("day", BEFORE_DAY.isoformat())
    desktop.reindex()
    assert canonical_bytes(root) == before


def test_studio_from_a_past_day_edits_the_current_revision(world):
    desktop, _, _, v2, *_ = world
    desktop.setCaptureDate(BEFORE_DAY.isoformat())
    desktop.studio.open()
    try:
        assert desktop.studio.draft.original == v2
    finally:
        desktop.studio.discard()
