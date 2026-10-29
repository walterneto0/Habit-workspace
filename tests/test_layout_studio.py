from dataclasses import replace
from datetime import date, datetime
from uuid import uuid4

import pytest
from PySide6.QtCore import QCoreApplication, QSettings, QThreadPool

from habit_workspace.application.layouts import LayoutService
from habit_workspace.domain.layouts import Assignment, LayoutTemplate
from habit_workspace.domain.temporal import PeriodRef
from habit_workspace.presentation.controllers import WorkspaceController
from habit_workspace.vault.atomic_io import ConflictError


@pytest.fixture
def studio(tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    workspace = WorkspaceController(
        settings=QSettings(str(tmp_path / "prefs"), QSettings.IniFormat), today=date(2026, 10, 29)
    )
    workspace.createVault(str(tmp_path / "vault"), "Synthetic")
    workspace.navigate("week", "2026-10-29")
    yield workspace.layoutStudio
    QThreadPool.globalInstance().waitForDone()
    app.processEvents()
    workspace.close()


def save(studio):
    studio.prepare()
    studio.save()
    QThreadPool.globalInstance().waitForDone()
    QCoreApplication.instance().processEvents()
    assert not studio.draft, studio.message


def test_journey_save_reopen_history_remove_and_rebuild(studio):
    w = studio.workspace
    studio.open()
    studio.command("columns")
    for kind in ("checklist", "note", "chart"):
        studio.add(kind, "", "", "")
    studio.add("number_input", "", "Leitura", "estudos")
    studio.edit("title", "Minutos")
    studio.command("up")
    studio.command("undo")
    studio.command("redo")
    draft = studio.draft.layout
    studio.command("preview")
    studio.command("preview")
    assert studio.draft.layout == draft
    assert not w.session.report.layouts
    save(studio)
    session = w.session
    first = LayoutService(session).resolve(PeriodRef("week/2026-W44"), datetime.now().astimezone())
    assert first.layout.blocks == draft.blocks
    field = next(d for d in session.report.documents if d.document.kind == "metric_definition")
    raw = field.path.read_bytes()
    studio.open()
    studio.select(
        next(i for i, b in enumerate(studio.draft.layout.blocks) if b.type == "number_input")
    )
    studio.command("remove")
    save(studio)
    assert field.path.read_bytes() == raw
    assert len(session.report.layouts) == 2
    assert LayoutService(session).resolve(first.period, first.instant).layout == first.layout
    current = w.state["composition"]["blocks"]
    session.index.path.unlink()
    w.reindex()
    assert w.state["composition"]["blocks"] == current
    assert (
        LayoutService(session)
        .resolve(PeriodRef("week/2026-W45"), datetime.now().astimezone())
        .origin
        == "builtin"
    )


def test_default_fork_discard_and_navigation(studio):
    w = studio.workspace
    service = LayoutService(w.session)
    template = LayoutTemplate(uuid4(), 1, "Default")
    service.save_template(template)
    service.set_default("week", Assignment(template.id, 1, datetime(2026, 1, 1).astimezone()))
    studio.open()
    studio.add("note", "", "", "")
    w.navigate("month")
    assert w.navigation.period == "week/2026-W44"
    studio.discard()
    assert len(w.session.report.layouts) == 1
    studio.open()
    studio.add("note", "", "", "")
    save(studio)
    assert (
        service.resolve(PeriodRef("week/2026-W45"), datetime.now().astimezone()).layout == template
    )
    assert (
        service.resolve(PeriodRef("week/2026-W44"), datetime.now().astimezone()).layout.id
        != template.id
    )


def test_new_page_and_external_layout_conflicts(studio):
    w = studio.workspace
    studio.open()
    report = studio.report
    service = LayoutService(w.session)
    template = LayoutTemplate(uuid4(), 1, "External")
    instant = datetime.now().astimezone()
    service.save_revision(studio.period, template, instant)
    with pytest.raises(ConflictError):
        service.save_revision(
            studio.period, replace(template, id=uuid4()), instant, expected_report=report
        )
    studio.discard()
    studio.open()
    loaded = studio.original
    loaded.path.write_bytes(loaded.path.read_bytes() + b"\n")
    with pytest.raises(ConflictError):
        service.save_revision(
            studio.period,
            template.new_revision(),
            datetime.now().astimezone(),
            expected_report=studio.report,
        )


def test_invalid_input_does_not_create_field(studio):
    studio.open()
    studio.add("number_input", "", "", "")
    assert studio.message
    assert not studio.fields
    assert not studio.workspace.session.report.documents


def test_shared_revision_identity_and_same_instant(studio):
    w = studio.workspace
    service = LayoutService(w.session)
    template = LayoutTemplate(uuid4(), 1, "Shared")
    start = datetime(2026, 1, 1).astimezone()
    service.save_revision(PeriodRef("week/2026-W44"), template, start)
    service.save_revision(PeriodRef("week/2026-W45"), template.new_revision(name="Other"), start)
    studio.open()
    studio.add("note", "", "", "")
    save(studio)
    assert (
        service.resolve(PeriodRef("week/2026-W44"), datetime.now().astimezone()).layout.version == 3
    )
    assert (
        service.resolve(PeriodRef("week/2026-W45"), datetime.now().astimezone()).layout.version == 2
    )
    with pytest.raises(ConflictError):
        service.save_revision(PeriodRef("week/2026-W44"), template.new_revision(), start)


def test_property_binding_and_source_selection(studio):
    from habit_workspace.application.metrics import MetricService
    from habit_workspace.domain.metrics import FieldDefinition

    field = FieldDefinition(uuid4(), "Número", "number", datetime.now().astimezone())
    MetricService(studio.workspace.session).create(field)
    studio.open()
    studio.add("number_input", str(field.id), "", "")
    assert studio.draft.layout.blocks[-1].binding.source_id == field.id
    studio.edit("placeholder", "Minutos")
    studio.edit("required", "true")
    assert studio.draft.layout.blocks[-1].config.required
    studio.add("chart", "", "", "")
    studio.edit("source", str(field.id))
    assert studio.draft.layout.blocks[-1].config.selection.source_ids == (field.id,)
    studio.command("duplicate")
    assert studio.draft.layout.blocks[-1].config.selection.source_ids == (field.id,)
    studio.add("checklist", str(field.id), "", "")
    assert "booleano" in studio.message
    assert not studio.fields


def test_table_columns_roundtrip(studio):
    studio.open()
    studio.addConfigured("number_input", "", "Minutes", "study", {"unit": "min"})
    field = next(iter(studio.fields))
    studio.add("table", "", "Measures", "")
    studio.edit("source", str(field))
    studio.edit("source", str(field))
    columns = studio.draft.layout.blocks[-1].config.columns
    studio.columnEdit(0, "label", "Duration")
    studio.columnEdit(0, "down", "")
    assert studio.draft.layout.blocks[-1].config.columns[1].id == columns[0].id
    studio.columnEdit(0, "remove", "")
    assert studio.draft.layout.blocks[-1].config.columns[0].label == "Duration"
    expected = studio.draft.layout.blocks
    save(studio)
    studio.open()
    assert studio.draft.layout.blocks == expected


def test_nested_section_edit_history(studio):
    studio.open()
    studio.add("section", "", "Group", "")
    studio.command("enter")
    studio.command("columns")
    studio.add("note", "", "First", "")
    studio.add("section", "", "Nested", "")
    studio.command("enter")
    studio.add("note", "", "Deep", "")
    studio.edit("title", "Edited")
    studio.command("duplicate")
    studio.command("remove")
    studio.command("undo")
    studio.command("redo")
    studio.command("back")
    studio.command("up")
    studio.command("back")
    group = studio.draft.layout.blocks[-1]
    assert group.config.columns == 2
    assert group.config.children[0].config.children[0].title == "Edited"
    expected = studio.draft.layout.blocks
    save(studio)
    studio.open()
    assert studio.draft.layout.blocks == expected


@pytest.mark.parametrize(
    "kind",
    ["text", "integer", "number", "date", "duration", "boolean", "selection", "rating", "time"],
)
def test_specialized_new_metric_configuration(studio, kind):
    studio.open()
    numeric = kind in ("integer", "number", "duration", "rating")
    options = {
        "temporal_policy": "weekly",
        "weekly_attribution": "end",
        "aggregation": "mean" if numeric else "count",
    }
    if numeric:
        options.update(minimum="1", maximum="5", unit="points")
    if kind == "selection":
        options["options"] = "Low\nMedium\nHigh"
    studio.addConfigured(kind + "_input", "", kind, "test", options)
    assert not studio.message
    field = next(iter(studio.fields.values()))
    assert field.temporal_policy == "weekly"
    assert field.weekly_attribution == "end"
    assert field.options == (("Low", "Medium", "High") if kind == "selection" else ())
    studio.edit("required", "true")
    studio.edit("placeholder", "Example")
    save(studio)
    studio.open()
    assert studio.draft.layout.blocks[-1].config.required


def test_chart_full_configuration_and_rejection(studio):
    studio.open()
    studio.add("number_input", "", "Measure", "study")
    field = next(iter(studio.fields))
    studio.add("chart", "", "Summary", "")
    studio.edit("types", "number,integer")
    studio.edit("aggregation", "sum")
    studio.edit("visualization", "line")
    studio.edit("source", str(field))
    studio.edit("period", "month/2026-10")
    config = studio.draft.layout.blocks[-1].config
    assert config.selection.source_ids == (field,)
    assert config.selection.value_types == ("number", "integer")
    assert config.aggregation == "sum"
    studio.edit("types", "text")
    assert studio.message
    assert studio.draft.layout.blocks[-1].config == config
    studio.edit("tags", "study")
    assert studio.draft.layout.blocks[-1].config.selection.value_types == ("number", "integer")
    studio.edit("clear_sources", "")
    studio.edit("source", str(field))
    studio.edit("remove_source", str(field))
    assert not studio.draft.layout.blocks[-1].config.selection.source_ids
    save(studio)


def test_invalid_metric_config_and_move_are_nonmutating(studio):
    studio.open()
    before = studio.draft.layout
    studio.addConfigured("selection_input", "", "Choice", "", {"options": "same\nsame"})
    assert studio.message and not studio.fields
    assert studio.draft.layout == before
    studio.move(-1, 0)
    assert studio.message
    assert studio.draft.layout == before


def test_missing_chart_and_table_references_are_disclosed(studio):
    from habit_workspace.domain.layouts import ChartConfig, Component, TableColumn, TableConfig
    from habit_workspace.domain.metrics import SourceSelection
    from habit_workspace.presentation.layout_studio import composition

    missing = uuid4()
    layout = LayoutTemplate(
        uuid4(),
        1,
        "Missing",
        (
            Component(
                uuid4(), "chart", "Chart", ChartConfig(SourceSelection("manual", (missing,)))
            ),
            Component(
                uuid4(),
                "table",
                "Table",
                TableConfig((TableColumn(uuid4(), "Snapshot", "number", missing),)),
            ),
        ),
    )
    rows = composition(layout, studio.workspace.session.report)
    assert all("Referências ausentes" in row["detail"] for row in rows)
    assert "Snapshot" in rows[1]["detail"]


def test_starting_points_are_undoable_and_preserve_assignments(studio):
    from habit_workspace.domain.layouts import Component, NoteConfig

    service = LayoutService(studio.workspace.session)
    template = LayoutTemplate(
        uuid4(), 1, "Minha rotina", (Component(uuid4(), "note", "Reflexão", NoteConfig()),)
    )
    service.save_template(template)
    service.set_default("week", Assignment(template.id, 1, datetime(2026, 1, 1).astimezone()))
    studio.open()
    original = studio.draft.layout
    studio.startFrom("empty")
    assert not studio.draft.layout.blocks
    assert not studio.workspace.session.report.documents
    studio.command("undo")
    assert studio.draft.layout == original
    studio.startFrom("default")
    assert studio.draft.layout.blocks == template.blocks
    studio.startFrom(f"{template.id}:1")
    assert studio.draft.layout.blocks == template.blocks
    studio.add("integer_input", "", "Minutos", "")
    save(studio)
    assert (
        service.resolve(PeriodRef("week/2026-W45"), datetime.now().astimezone()).layout == template
    )
    assert unique_template_bytes(studio, template) == template
    studio.open()
    before = studio.draft.layout
    studio.startFrom("invalid")
    assert studio.message and studio.draft.layout == before
    studio.startFrom("empty")
    studio.startFrom("current")
    assert studio.draft.layout == before


def unique_template_bytes(studio, template):
    from habit_workspace.application.layouts import unique_layout

    return unique_layout(studio.workspace.session.report, template.id, 1).layout


def test_summary_names_reordering_and_new_sources(studio):
    studio.open()
    studio.startFrom("empty")
    studio.add("checklist", "", "", "")
    studio.add("integer_input", "", "Minutos", "")
    save(studio)
    studio.open()
    studio.move(1, 0)
    studio.prepare()
    assert "Ordem alterada" in studio.state["summary"]
    assert "Semana 44" in studio.state["periodLabel"]
    assert "Minutos" in studio.state["summary"]
    assert "Novos campos: nenhum" in studio.state["summary"]
    studio.add("duration_input", "", "Estudo", "")
    assert "Novos campos: Estudo" in studio.state["summary"]
    assert "registros históricos" in studio.state["summary"]


def test_existing_source_uses_name_without_creating_definition(studio):
    from habit_workspace.application.metrics import MetricService
    from habit_workspace.domain.metrics import FieldDefinition

    field = FieldDefinition(uuid4(), "Tempo de leitura", "integer", datetime.now().astimezone())
    MetricService(studio.workspace.session).create(field)
    studio.open()
    studio.addConfigured("number_input", str(field.id), "", "", {})
    block = studio.draft.layout.blocks[-1]
    assert block.title == field.name
    assert block.binding.source_id == field.id
    assert not studio.fields
    before = studio.draft.layout
    studio.addConfigured("duration_input", str(field.id), "", "", {})
    assert studio.message and studio.draft.layout == before
    assert not studio.fields


def test_note_cannot_be_used_as_text_metric(studio):
    from habit_workspace.domain.documents import Document

    note = Document.from_metadata(
        {"hw": {"schema_version": 4, "kind": "note", "id": str(uuid4()), "title": "Nota"}},
        "Conteúdo preservado.",
    )
    studio.workspace.session.create_document("Notes/note.md", note)
    studio.open()
    before = studio.draft.layout
    studio.addConfigured("text_input", str(note.id), "", "", {})
    assert studio.message and studio.draft.layout == before
    assert not studio.fields
