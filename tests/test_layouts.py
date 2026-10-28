"""Phase 4 contracts, authored before the implementation; deterministic civil dates."""

from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime
from uuid import uuid4

import pytest

from habit_workspace.application.layouts import LayoutService
from habit_workspace.application.metrics import MetricService
from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.documents import DocumentError
from habit_workspace.domain.layouts import (
    Assignment,
    AssignmentHistory,
    Binding,
    ChartConfig,
    ChecklistConfig,
    Component,
    Grid,
    ImageConfig,
    InputConfig,
    LayoutTemplate,
    ListConfig,
    NoteConfig,
    Placement,
    SectionConfig,
    TableColumn,
    TableConfig,
)
from habit_workspace.domain.metrics import FieldDefinition, Observation, SourceSelection
from habit_workspace.domain.temporal import PeriodRef
from habit_workspace.vault.atomic_io import ConflictError
from habit_workspace.vault.layouts import decode_layout, encode_layout

START = datetime.fromisoformat("2026-10-26T00:00:00-03:00")
ACTIVE = datetime.fromisoformat("2026-10-29T10:00:00-03:00")
LATER = datetime.fromisoformat("2026-10-30T12:00:00-03:00")
WEEK = PeriodRef("week/2026-W44")
MONTH = PeriodRef("month/2026-10")


def note_block():
    return Component(uuid4(), "note", "Review", NoteConfig())


def template():
    return LayoutTemplate(uuid4(), 1, "Study week", (note_block(),))


@pytest.fixture
def services(tmp_path):
    session = VaultSession.create(tmp_path / "vault", "Layouts")
    return LayoutService(session), MetricService(session)


def test_template_serialization_and_immutable_tree():
    layout = template()
    assert decode_layout(encode_layout(layout)).layout == layout
    with pytest.raises(FrozenInstanceError):
        layout.name = "Changed"
    assert layout.schema_version == 4


@pytest.mark.parametrize(
    "kind,config",
    [
        ("checklist", ChecklistConfig()),
        ("list", ListConfig()),
        ("table", TableConfig((TableColumn(uuid4(), "Time", "number", uuid4()),))),
        ("chart", ChartConfig(SourceSelection("by_tags", tags=("study",)))),
        ("note", NoteConfig()),
        ("image", ImageConfig("Assets/reading.png", "Reading")),
        ("section", SectionConfig((note_block(),))),
        *[
            (f"{kind}_input", InputConfig(kind))
            for kind in ("text", "number", "date", "duration", "boolean", "selection")
        ],
    ],
)
def test_component_registry_roundtrip(kind, config):
    binding = Binding(uuid4(), "metric") if kind.endswith("_input") else None
    block = Component(uuid4(), kind, "Label", config, binding=binding)
    layout = replace(template(), blocks=(block,))
    assert decode_layout(encode_layout(layout)).layout == layout


def test_order_insert_remove_and_grid():
    first, second, third = note_block(), note_block(), note_block()
    layout = replace(template(), blocks=(first, second), grid=Grid(2))
    inserted = layout.insert(1, third)
    assert inserted.blocks == (first, third, second)
    moved = inserted.move(second.id, 0)
    assert moved.blocks == (second, first, third)
    assert moved.remove(first.id).blocks == (second, third)
    assert layout.blocks == (first, second)
    full = replace(first, placement=Placement(width=2))
    layout = replace(layout, blocks=(full, second, third))
    assert [(p.row, p.column, p.width) for p in layout.positions()] == [
        (0, 0, 2),
        (1, 0, 1),
        (1, 1, 1),
    ]
    with pytest.raises(ValueError):
        replace(layout, grid=Grid(1))
    with pytest.raises(ValueError):
        Grid(3)
    with pytest.raises(ValueError):
        Placement(width=0)
    with pytest.raises(ValueError):
        replace(layout, blocks=(first, first))
    with pytest.raises(ValueError):
        replace(
            layout,
            blocks=(
                replace(first, placement=Placement(1, 0, 0)),
                replace(second, placement=Placement(1, 0, 0)),
            ),
        )


def test_history_timezone_collisions_and_boundary():
    layout = template()
    first = Assignment(layout.id, 1, START)
    second = Assignment(layout.id, 2, ACTIVE)
    history = AssignmentHistory((first, second))
    assert history.at(START) == first
    assert history.at(ACTIVE) == second
    assert history.at(START.replace(day=25)) is None
    with pytest.raises(ValueError):
        AssignmentHistory((second, first))
    with pytest.raises(ValueError):
        AssignmentHistory(
            (second, replace(second, effective_at=datetime.fromisoformat("2026-10-29T13:00:00Z")))
        )
    with pytest.raises(ValueError):
        Assignment(layout.id, 1, datetime(2026, 10, 29))


def test_assign_defaults_fallback_and_independent_periods(services):
    layouts, _ = services
    assert layouts.resolve(WEEK, START).origin == "builtin"
    layout = template()
    layouts.save_template(layout)
    layouts.set_default("week", Assignment(layout.id, 1, START))
    assert layouts.resolve(WEEK, START).origin == "default"
    layouts.assign(WEEK, Assignment(layout.id, 1, START))
    assert layouts.resolve(WEEK, START).origin == "explicit"
    revised = layout.new_revision(name="Personal week", blocks=())
    layouts.save_revision(WEEK, revised, ACTIVE)
    assert layouts.resolve(WEEK, START).layout == layout
    assert layouts.resolve(WEEK, ACTIVE).layout == revised
    assert layouts.resolve(PeriodRef("week/2026-W45"), ACTIVE).layout == layout
    assert layouts.resolve(MONTH, ACTIVE).origin == "builtin"
    with pytest.raises(ConflictError):
        layouts.assign(WEEK, Assignment(layout.id, 1, ACTIVE))
    with pytest.raises(ConflictError):
        layouts.save_template(replace(layout, name="Overwrite"))
    assert layouts.load(layout.id, 1).layout == layout


def test_weekly_field_monthly_discovery_and_removal_preserve_data(services):
    layouts, metrics = services
    layout = template()
    layouts.save_revision(WEEK, layout, START)
    layouts.assign(MONTH, Assignment(layout.id, 1, START))
    dynamic = SourceSelection("by_tags", tags=("study",), value_types=("number",))
    existing = FieldDefinition(
        uuid4(),
        "Earlier reading",
        "number",
        START,
        tags=("manual",),
        unit="minutes",
        aggregation="sum",
    )
    metrics.create(existing)
    earlier = Observation(
        uuid4(),
        existing.id,
        existing.name,
        date(2026, 10, 27),
        datetime.fromisoformat("2026-10-27T09:00:00-03:00"),
        15,
    )
    metrics.record(earlier)
    manual = SourceSelection("manual", (existing.id,), value_types=("number",))
    manual_before = metrics.query(MONTH, manual, as_of=ACTIVE)
    assert manual_before.sources == (existing,)
    assert manual_before.records == (earlier,)
    assert not metrics.query(MONTH, dynamic, as_of=START).sources
    field = FieldDefinition(
        uuid4(),
        "Reading duration",
        "number",
        ACTIVE,
        tags=("Study",),
        unit="minutes",
        aggregation="sum",
    )
    block = Component(
        uuid4(),
        "number_input",
        "Reading",
        InputConfig("number"),
        binding=Binding(field.id, "metric"),
    )
    revised = layout.new_revision(blocks=layout.blocks + (block,))
    layouts.save_revision(WEEK, revised, ACTIVE, new_fields=(field,))
    assert layouts.resolve(MONTH, ACTIVE).layout == layout
    assert not metrics.query(MONTH, dynamic, as_of=START).sources
    assert metrics.query(MONTH, dynamic, as_of=ACTIVE).sources == (field,)
    assert metrics.query(MONTH, manual, as_of=LATER) == manual_before
    record = Observation(
        uuid4(), field.id, "Reading duration", date(2026, 10, 29), LATER, 40, WEEK, block.id
    )
    metrics.record(record)
    result = metrics.query(MONTH, dynamic, as_of=LATER)
    assert result.records == (record,)
    assert result.eligible_from == ((field.id, date(2026, 10, 29)),)
    assert not result.unresolved_records
    assert metrics.query(MONTH, manual, as_of=LATER) == manual_before
    # No synthetic failures/observations on October 26–28.
    assert [r.observed_date for r in result.records] == [date(2026, 10, 29)]
    canonical = metrics.session.load(field.id).path.read_bytes()
    layouts.save_revision(WEEK, revised.new_revision(blocks=layout.blocks), LATER)
    assert layouts.resolve(MONTH, LATER).layout == layout
    assert metrics.session.load(field.id).path.read_bytes() == canonical
    assert metrics.query(MONTH, dynamic, as_of=LATER) == result
    assert metrics.query(MONTH, manual, as_of=LATER) == manual_before
    before = layouts.session.scan()
    layouts.session.index.path.unlink()
    reopened = VaultSession.open(layouts.session.root)
    assert MetricService(reopened).query(MONTH, dynamic, as_of=LATER) == result
    assert MetricService(reopened).query(MONTH, manual, as_of=LATER) == manual_before
    assert LayoutService(reopened).resolve(WEEK, ACTIVE).layout == revised
    assert LayoutService(reopened).resolve(MONTH, ACTIVE).layout == layout
    assert len(reopened.report.layouts) == len(before.layouts) == 3


def test_import_missing_layout_and_json_roundtrip(services, tmp_path):
    from habit_workspace.application.imports import ImportService

    layouts, _ = services
    layout = template()
    layouts.save_revision(WEEK, layout, START)
    target = VaultSession.create(tmp_path / "target", "Target")
    page = next(d for d in layouts.session.report.documents if d.document.kind == "week_page")
    result = ImportService(target).import_files([page.path])
    assert result.imported[0].missing_references[0].role == "layout_id"
    resolved = LayoutService(target).resolve(WEEK, ACTIVE)
    assert resolved.origin == "builtin" and resolved.issues
    raw = layouts.load(layout.id, 1).path.read_bytes()
    external = tmp_path / "layout.json"
    external.write_bytes(raw)
    imported = LayoutService(target).import_template(external)
    assert imported.path.read_bytes() == raw
    assert LayoutService(target).resolve(WEEK, ACTIVE).layout == layout
    assert not target.scan().missing_references
    external.write_bytes(raw.replace(b"Study week", b"Conflict"))
    with pytest.raises(ConflictError):
        LayoutService(target).import_template(external)
    external.write_bytes(b'{"schema_version":999,"unknown":"preserve"}')
    with pytest.raises(DocumentError):
        LayoutService(target).import_template(external)
    assert b"preserve" in external.read_bytes()
