"""Phase 6 refinement contracts against canonical files and the Qt adapter."""

from datetime import date
from uuid import uuid4

import pytest
from test_tracking import cells, controller, save_studio
from test_vault import note

from habit_workspace.application.capture import CaptureSnapshot
from habit_workspace.application.habits import HabitService
from habit_workspace.domain.layouts import Binding, ChecklistConfig, Component
from habit_workspace.domain.metrics import SourceSelection
from habit_workspace.domain.temporal import PeriodRef, Recurrence, TemporalScope
from habit_workspace.vault.layouts import component_from_mapping, component_mapping

DAY = date(2026, 10, 29)


@pytest.fixture
def workspace(tmp_path):
    desktop = controller(tmp_path)
    desktop.createVault(str(tmp_path / "vault"), "Refinamentos")
    desktop.navigate("day", DAY.isoformat())
    yield desktop
    desktop.close()


def habits(workspace):
    service = HabitService(workspace.session)
    return [
        service.create(name=name, period=PeriodRef("month/2026-10"), tags=tags).habit
        for name, tags in (("Ler", ("estudos",)), ("Andar", ("saúde",)), ("Beber água", ()))
    ]


def checklist(selection):
    return Component(uuid4(), "checklist", "Rotina", ChecklistConfig(selection))


def test_manual_order_roundtrip_missing_and_legacy(workspace):
    a, b, c = habits(workspace)
    missing = uuid4()
    block = checklist(
        SourceSelection("manual", (c.id, missing, a.id, b.id), value_types=("habit",))
    )
    assert component_from_mapping(component_mapping(block)) == block
    snapshot = CaptureSnapshot(workspace.session.report, DAY, DAY)
    result = snapshot.block(block)
    assert [cell.habit_id for cell in result] == [c.id, missing, a.id, b.id]
    assert not result[1].editable and "ausente" in result[1].note
    legacy = Component(
        uuid4(), "checklist", "Antigo", ChecklistConfig(), binding=Binding(a.id, "habit")
    )
    assert component_from_mapping(component_mapping(legacy)) == legacy
    assert snapshot.block(legacy) == [snapshot.habit_cell(a.id)]
    with pytest.raises(ValueError, match="Duplicate"):
        SourceSelection("manual", (a.id, a.id), value_types=("habit",))


def test_dynamic_or_tags_and_contextual_recurrence(workspace):
    a, b, _ = habits(workspace)
    service = HabitService(workspace.session)
    service.create(
        name="Só sexta",
        period=PeriodRef("month/2026-10"),
        recurrence=Recurrence.weekdays((5,)),
        tags=("estudos",),
    )
    service.create(name="Expirado", period=PeriodRef("day/2026-10-01"), tags=("estudos",))
    service.create(name="Futuro", period=PeriodRef("day/2026-10-30"), tags=("saúde",))
    tagged = checklist(
        SourceSelection("by_tags", tags=("ESTUDOS", "saúde"), value_types=("habit",))
    )
    snapshot = CaptureSnapshot(workspace.session.report, DAY, DAY)
    assert {c.habit_id for c in snapshot.block(tagged)} == {a.id, b.id}
    added = service.create(name="Novo", period=PeriodRef("month/2026-10"), tags=("estudos",)).habit
    snapshot = CaptureSnapshot(workspace.session.report, DAY, DAY)
    assert {c.habit_id for c in snapshot.block(tagged)} == {a.id, b.id, added.id}
    contextual = checklist(SourceSelection("all", value_types=("habit",)))
    assert len(snapshot.block(contextual)) == 4
    assert all(c.editable and c.state == "pending" for c in snapshot.block(contextual))
    friday = CaptureSnapshot(workspace.session.report, date(2026, 10, 30), DAY)
    assert len(friday.block(contextual)) == 6
    assert all(c.state == "future" and not c.editable for c in friday.block(contextual))


def test_studio_multiselect_reorder_independent_records_restart(workspace, tmp_path):
    a, b, c = habits(workspace)
    workspace.reindex()
    studio = workspace.layoutStudio
    studio.open()
    studio.add("checklist", str(a.id), "Rotina", "")
    studio.edit("source", str(b.id))
    studio.edit("source", str(c.id))
    studio.edit("source", str(b.id))
    studio.edit("source_up", str(c.id))
    block = studio.draft.view.blocks[-1]
    assert block.binding is None
    assert block.config.selection.source_ids == (a.id, c.id, b.id)
    studio.edit("remove_source", str(c.id))
    assert studio.draft.view.blocks[-1].config.selection.source_ids == (a.id, b.id)
    studio.command("undo")
    assert studio.draft.view.blocks[-1].config.selection.source_ids == (a.id, c.id, b.id)
    save_studio(workspace)
    assert [c[1]["id"] for c in cells(workspace)] == list(map(str, (a.id, c.id, b.id)))
    assert workspace.setCheckin(str(a.id), "done", "null")
    assert workspace.setCheckin(str(b.id), "skipped", "null")
    assert workspace.setCheckin(str(c.id), "missed", "null")
    assert workspace.setCheckin(str(c.id), "", '"missed"')
    studio.open()
    studio.select(len(studio.draft.view.blocks) - 1)
    studio.command("duplicate")
    save_studio(workspace)
    assert [c[1]["state"] for c in cells(workspace)] == ["done", "pending", "skipped"] * 2
    page = next(d for d in workspace.session.report.documents if d.document.kind == "day_page")
    assert len(page.document.metadata["hw"]["checkins"]) == 2
    workspace.navigate("month", "2026-10-29")
    workspace.navigate("day", "2026-10-29")
    expected = workspace.state["composition"]
    root = workspace.session.root
    workspace.close()
    (root / ".habit-workspace/index.sqlite").unlink()
    again = controller(tmp_path / "restarted")
    try:
        again.openVault(str(root))
        again.navigate("day", DAY.isoformat())
        assert again.state["composition"] == expected
        assert again.session.index.path.exists()
    finally:
        again.close()


def test_type_aware_preview_and_inventory(workspace):
    a, _, _ = habits(workspace)
    doc = note(body="# Minha nota\n\nTexto preservado", tags=["pessoal"])
    workspace.session.create_document("Notes/note.md", doc)
    workspace.setCheckin(str(a.id), "done", "null")
    originals = {d.path: d.path.read_bytes() for d in workspace.session.report.documents}
    workspace.navigate("habits", DAY.isoformat())
    assert len(workspace.state["documents"]) == 3
    assert all(r["documentKind"] == "habit" for r in workspace.state["documents"])
    workspace.setQuery("estudos")
    assert [r["id"] for r in workspace.state["documents"]] == [str(a.id)]
    workspace.selectDocument(str(a.id))
    selected = workspace.state["selected"]
    assert selected["previewType"] == "habit"
    assert selected["habit"]["name"] == "Ler"
    assert selected["habit"]["recurrence"] == "Diário"
    assert selected["habit"]["stateLabel"] == "Concluído"
    assert selected["habit"]["date"] == DAY.isoformat()
    assert selected["habit"]["scope"]
    workspace.editHabit(str(a.id))
    assert workspace.state["habitForm"]["mode"] == "edit"
    workspace.cancelHabit()
    workspace.setQuery("")
    workspace.navigate("notes")
    assert [r["id"] for r in workspace.state["documents"]] == [str(doc.id)]
    workspace.selectDocument(str(doc.id))
    assert workspace.state["selected"]["previewType"] == "note"
    assert workspace.state["selected"]["excerpt"] == "Minha nota\n\nTexto preservado"
    workspace.navigate("day", DAY.isoformat())
    assert [r["documentKind"] for r in workspace.state["documents"]] == ["day_page"]
    assert workspace.state["documentCount"] == 5
    assert all(path.read_bytes() == raw for path, raw in originals.items())


def test_manual_ineligible_is_explicit_and_move_keeps_uuid(workspace):
    a, _, _ = habits(workspace)
    service = HabitService(workspace.session)
    loaded = service.load(a.id)
    service.update(loaded, scope=TemporalScope(DAY, date(2026, 10, 30)))
    moved = loaded.loaded.path.with_name("friendly.md")
    loaded.loaded.path.rename(moved)
    workspace.reindex()
    snapshot = CaptureSnapshot(workspace.session.report, date(2026, 10, 28), DAY)
    block = checklist(SourceSelection("manual", (a.id,), value_types=("habit",)))
    assert snapshot.block(block)[0].state == "not_scheduled"
    assert not snapshot.block(block)[0].editable


@pytest.mark.parametrize("view", ["week", "month"])
def test_period_checklists_always_target_the_selected_day(workspace, view):
    a, b, _ = habits(workspace)
    workspace.navigate(view, DAY.isoformat())
    studio = workspace.layoutStudio
    studio.open()
    studio.add("checklist", "", "", "")
    studio.edit("selection_mode", "all")
    assert studio.draft.view.blocks[-1].config.selection.mode == "all"
    save_studio(workspace)
    workspace.setCaptureDate("2026-10-28")
    assert workspace.setCheckin(str(a.id), "done", "null")
    workspace.setCaptureDate("2026-10-29")
    assert workspace.setCheckin(str(b.id), "skipped", "null")
    assert {c[1]["id"]: c[1]["state"] for c in cells(workspace)}[str(a.id)] == "pending"
    records = [
        r
        for d in workspace.session.report.documents
        for r in d.document.metadata["hw"].get("checkins", [])
    ]
    assert {(r["habit_id"], r["date"], r["state"]) for r in records} == {
        (str(a.id), "2026-10-28", "done"),
        (str(b.id), "2026-10-29", "skipped"),
    }
    workspace.navigate("habits")
    workspace.selectDocument(str(a.id))
    assert workspace.state["selected"]["habit"]["date"] == "2026-10-29"


def test_studio_tags_saved_and_dynamic_refresh(workspace):
    a, b, _ = habits(workspace)
    studio = workspace.layoutStudio
    studio.open()
    studio.add("checklist", "", "", "")
    studio.edit("tags", " Estudos, saúde, ESTUDOS ")
    assert studio.draft.view.blocks[-1].config.selection.tags == ("estudos", "saúde")
    save_studio(workspace)
    assert {c[1]["id"] for c in cells(workspace)} == {str(a.id), str(b.id)}
    workspace.newHabit()
    assert workspace.saveHabit({"name": "Aprender", "tags": "estudos"})
    assert len(cells(workspace)) == 3
    studio.open()
    studio.select(len(studio.draft.view.blocks) - 1)
    original = studio.draft.view.blocks[-1]
    studio.edit("tags", " , ")
    assert studio.message and studio.draft.view.blocks[-1] == original
    studio.discard()


def test_description_and_structured_fallback_are_read_only(workspace):
    loaded = HabitService(workspace.session).create(
        name="Descrito", period=PeriodRef("day/2026-10-29"), body="Uma descrição opcional."
    )
    raw = loaded.loaded.path.read_bytes()
    workspace.navigate("habits")
    workspace.selectDocument(str(loaded.habit.id))
    assert workspace.state["selected"]["excerpt"] == "Uma descrição opcional."
    assert loaded.loaded.path.read_bytes() == raw
    workspace.editHabit(str(loaded.habit.id))
    assert workspace.saveHabit({"name": "Nome corrigido"})
    assert (
        HabitService(workspace.session).load(loaded.habit.id).loaded.document.body
        == "Uma descrição opcional."
    )
    workspace.navigate("day", DAY.isoformat())
    workspace.setCheckin(str(loaded.habit.id), "done", "null")
    page = next(d for d in workspace.session.report.documents if d.document.kind == "day_page")
    workspace.selectDocument(str(page.document.id))
    assert workspace.state["selected"]["previewType"] == "structured"
    assert "Documento estruturado" in workspace.state["selected"]["fallback"]


def test_manual_boolean_compatibility_and_incompatible_source_is_read_only(workspace):
    from test_capture import make_field

    a, _, _ = habits(workspace)
    flag = make_field(workspace.session, "boolean", name="Revisou")
    number = make_field(workspace.session, "integer", name="Minutos")
    block = checklist(
        SourceSelection("manual", (flag.id, a.id, number.id), value_types=("boolean", "habit"))
    )
    result = CaptureSnapshot(workspace.session.report, DAY, DAY).block(block)
    assert result[0].field_id == flag.id and result[0].editable
    assert result[1].habit_id == a.id and result[1].editable
    assert result[2].field_id == number.id and not result[2].editable
    assert "incompatível" in result[2].note
