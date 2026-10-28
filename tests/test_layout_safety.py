"""Durability, untrusted input, binding and cross-period boundary contracts."""

import json
from copy import deepcopy
from dataclasses import replace
from datetime import date
from uuid import uuid4

import pytest
from test_layouts import ACTIVE, LATER, MONTH, START, WEEK, template

from habit_workspace.application.habits import HabitService
from habit_workspace.application.imports import ImportService
from habit_workspace.application.layouts import LayoutService
from habit_workspace.application.metrics import MetricService
from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.documents import DocumentError
from habit_workspace.domain.layouts import (
    Assignment,
    Binding,
    ChartConfig,
    ChecklistConfig,
    Component,
    ImageConfig,
    InputConfig,
    TableColumn,
    TableConfig,
)
from habit_workspace.domain.metrics import FieldDefinition, Observation, SourceSelection
from habit_workspace.domain.temporal import PeriodRef
from habit_workspace.vault.atomic_io import ConflictError
from habit_workspace.vault.layouts import decode_layout, encode_layout

pytest_plugins = ("test_layouts",)


def field(**changes):
    return replace(
        FieldDefinition(uuid4(), "Minutes", "number", ACTIVE, tags=("study",)), **changes
    )


def block(source):
    return Component(
        uuid4(),
        f"{source.value_type}_input",
        source.name,
        InputConfig(source.value_type),
        binding=Binding(source.id, "metric"),
    )


def record(source, day=29, value=40, **changes):
    return replace(
        Observation(uuid4(), source.id, source.name, date(2026, 10, day), LATER, value, WEEK),
        **changes,
    )


def test_json_extensions_roundtrip_revision_and_documented_shorthand(services):
    layouts, _ = services
    source = field(value_type="integer")
    from habit_workspace.vault.metrics import field_document

    layouts.session.create_document("metric.md", field_document(source))
    layout = template()
    value = json.loads(encode_layout(layout))
    value["vendor"] = {"keep": [1, "two"]}
    value["grid"]["vendor"] = "preserve"
    value["blocks"][0]["vendor"] = "preserve"
    value["blocks"][0]["config"]["vendor"] = "preserve"
    value["blocks"].extend(
        [
            {
                "id": str(uuid4()),
                "type": "checklist",
                "width": 1,
                "source": {"mode": "habits_by_tags", "tags": ["study"]},
            },
            {"id": str(uuid4()), "type": "number_input", "width": 1, "field_id": str(source.id)},
        ]
    )
    raw = ("\ufeff" + json.dumps(value, indent=3) + "\n").encode()
    parsed = decode_layout(raw)
    assert encode_layout(parsed.layout, parsed) == raw
    (layouts.session.root / "outside-layouts.json").write_bytes(raw)
    updated = parsed.layout.new_revision(name="Renamed")
    layouts.save_template(updated)
    saved = json.loads(layouts.load(layout.id, 2).raw)
    assert saved["vendor"] == value["vendor"]
    assert saved["grid"]["vendor"] == "preserve"
    assert saved["blocks"][0]["config"]["vendor"] == "preserve"
    assert layouts.load(layout.id, 1).raw == raw


@pytest.mark.parametrize(
    "raw",
    [
        b'{"schema_version":4,"schema_version":4}',
        b'{"schema_version":true}',
        b'{"schema_version":4,"x":NaN}',
        b'{"schema_version":4,"x":1e999}',
        b'{"schema_version":4,"kind":"qml","code":"execute()"}',
        b"\xff",
        b"[" * 1100 + b"0" + b"]" * 1100,
        b"x" * (2 * 1024 * 1024 + 1),
    ],
)
def test_untrusted_json_preserved(services, tmp_path, raw):
    layouts, _ = services
    path = tmp_path / "unsafe.json"
    path.write_bytes(raw)
    with pytest.raises(DocumentError):
        layouts.import_template(path)
    assert path.read_bytes() == raw
    assert not layouts.session.scan().layouts


@pytest.mark.parametrize(
    "path",
    [
        "../secret.png",
        "/secret.png",
        "https://a/b.png",
        "C:\\a.png",
        ".habit-workspace/secret.png",
        "Assets/active.svg",
    ],
)
def test_remote_and_escaping_images_rejected(path):
    with pytest.raises(ValueError):
        ImageConfig(path)


def test_unknown_component_and_future_schema_preserved(services):
    layouts, _ = services
    value = json.loads(encode_layout(template()))
    value["blocks"][0]["type"] = "future-widget"
    raw = json.dumps(value).encode()
    path = layouts.session.root / "unsupported.json"
    path.write_bytes(raw)
    report = layouts.session.scan()
    assert report.invalid and path.read_bytes() == raw
    assert not report.layouts
    assert layouts.resolve(WEEK, ACTIVE).issues


def test_duplicate_revision_and_period_pages_are_conflicts(services):
    layouts, _ = services
    layout = template()
    page = layouts.save_revision(WEEK, layout, START)
    duplicate = layouts.session.root / "duplicate.json"
    duplicate.write_bytes(layouts.load(layout.id, 1).raw)
    with pytest.raises(ConflictError):
        layouts.resolve(WEEK, ACTIVE)
    duplicate.unlink()
    other = deepcopy(page.document)
    other.metadata["hw"]["id"] = str(uuid4())
    layouts.session.create_document("second-week.md", other)
    with pytest.raises(ConflictError, match="page"):
        layouts.resolve(WEEK, ACTIVE)
    with pytest.raises(ConflictError):
        layouts.assign(WEEK, Assignment(layout.id, 1, LATER))


def test_field_and_habit_binding_validation(services):
    layouts, metrics = services
    numeric, boolean = field(), field(value_type="boolean")
    metrics.create(numeric)
    metrics.create(boolean)
    invalid = replace(block(numeric), type="boolean_input", config=InputConfig("boolean"))
    with pytest.raises(DocumentError, match="incompatible"):
        layouts.save_revision(WEEK, replace(template(), blocks=(invalid,)), ACTIVE)
    with pytest.raises(DocumentError, match="boolean"):
        layouts.save_revision(
            WEEK,
            replace(
                template(),
                blocks=(
                    Component(
                        uuid4(),
                        "checklist",
                        "Bad",
                        ChecklistConfig(),
                        binding=Binding(numeric.id, "metric"),
                    ),
                ),
            ),
            ACTIVE,
        )
    habit = HabitService(layouts.session).create(name="Read", period=WEEK)
    checklist = Component(
        uuid4(), "checklist", "Read", ChecklistConfig(), binding=Binding(habit.habit.id, "habit")
    )
    table = Component(
        uuid4(),
        "table",
        "Metrics",
        TableConfig((TableColumn(uuid4(), "Minutes", "number", numeric.id),)),
    )
    layout = replace(template(), blocks=(checklist, table, block(boolean)))
    layouts.save_revision(WEEK, layout, ACTIVE)
    assert not layouts.resolve(WEEK, ACTIVE).issues
    assert not any(
        d.document.metadata["hw"].get("checkins") for d in layouts.session.report.documents
    )


def test_chart_and_checklist_selections_match_component_semantics():
    with pytest.raises(ValueError, match="fixed IDs or dynamic tags"):
        ChartConfig(SourceSelection("all"))
    with pytest.raises(ValueError, match="boolean metrics or habits"):
        ChecklistConfig(SourceSelection("by_tags", tags=("study",)))


def test_stale_page_conflicts_and_interrupted_save_retry(services, monkeypatch):
    layouts, metrics = services
    layout = template()
    page = layouts.save_revision(WEEK, layout, START)
    page.path.write_bytes(page.path.read_bytes() + b"External text\n")
    with pytest.raises(ConflictError):
        layouts.save_revision(WEEK, layout.new_revision(), ACTIVE, expected_page=page)
    assert page.path.read_bytes().endswith(b"External text\n")
    source = field()
    revised = layout.new_revision(blocks=layout.blocks + (block(source),))
    original = layouts.session.repository.save

    def interrupted(*args, **kwargs):
        raise OSError("Interrupted assignment")

    monkeypatch.setattr(layouts.session.repository, "save", interrupted)
    with pytest.raises(OSError, match="Interrupted"):
        layouts.save_revision(WEEK, revised, ACTIVE, new_fields=(source,))
    assert layouts.resolve(WEEK, ACTIVE).layout == layout
    assert layouts.load(layout.id, 2).layout == revised
    assert metrics.session.load(source.id)
    monkeypatch.setattr(layouts.session.repository, "save", original)
    layouts.save_revision(WEEK, revised, ACTIVE, new_fields=(source,))
    layouts.save_revision(WEEK, revised, ACTIVE, new_fields=(source,))
    assert layouts.resolve(WEEK, ACTIVE).layout == revised
    assert len(layouts.session.report.layouts) == 2
    assert (
        sum(d.document.kind == "metric_definition" for d in layouts.session.report.documents) == 1
    )


def test_record_idempotence_duplicate_and_shared_layout_bindings(services):
    layouts, metrics = services
    source = field()
    metrics.create(source)
    layout = replace(template(), blocks=(block(source), block(source)))
    layouts.save_revision(WEEK, layout, ACTIVE)
    value = record(source)
    loaded = metrics.record(value)
    raw = loaded.path.read_bytes()
    metrics.record(value)
    assert loaded.path.read_bytes() == raw
    with pytest.raises(ConflictError):
        metrics.record(replace(value, id=uuid4()))
    with pytest.raises(ConflictError):
        metrics.record(replace(value, value=41))
    assert len(metrics.query(MONTH, SourceSelection("all"), as_of=LATER).records) == 1
    copy = deepcopy(loaded.document)
    copy.metadata["hw"]["id"] = str(uuid4())
    metrics.session.create_document("duplicate-daily.md", copy)
    with pytest.raises(ConflictError):
        metrics.query(MONTH, SourceSelection("all"), as_of=LATER)


@pytest.mark.parametrize(
    "kind,valid,invalid,options",
    [
        ("text", "text", 1, ()),
        ("integer", 1, True, ()),
        ("number", 1.5, False, ()),
        ("boolean", False, 0, ()),
        ("date", "2026-10-29", "2026-02-30", ()),
        ("duration", 60, -1, ()),
        ("selection", "a", "b", ("a",)),
        ("rating", 3, "3", ()),
        ("time", "10:30", "25:00", ()),
    ],
)
def test_typed_field_values(kind, valid, invalid, options):
    source = field(value_type=kind, options=options)
    source.validate_value(valid)
    with pytest.raises(ValueError):
        source.validate_value(invalid)


def test_historical_entry_keeps_actual_date_and_provenance(services):
    _, metrics = services
    source = field()
    metrics.create(source)
    old = record(source, day=27)
    with pytest.raises(ValueError, match="historical"):
        metrics.record(old)
    explicit = replace(
        old, historical_entry=True, provenance="Entered from paper notes on October 30"
    )
    metrics.record(explicit)
    query = metrics.query(MONTH, SourceSelection("all"), as_of=LATER)
    assert query.records == (explicit,)
    assert query.eligible_from == ((source.id, date(2026, 10, 29)),)
    assert not metrics.query(MONTH, SourceSelection("all"), as_of=START).records
    september = replace(
        record(source),
        observed_date=date(2026, 9, 20),
        historical_entry=True,
        provenance="Paper diary",
    )
    metrics.record(september)
    result = metrics.query(PeriodRef("month/2026-09"), SourceSelection("all"), as_of=LATER)
    assert result.records == (september,) and result.eligible_from == ()


@pytest.mark.parametrize(
    "policy,october,november,separate",
    [("start", 1, 0, 0), ("end", 0, 1, 0), ("completion", 1, 0, 0), ("separate", 0, 0, 1)],
)
def test_weekly_values_crossing_month_are_never_split(
    services, policy, october, november, separate
):
    _, metrics = services
    source = field(temporal_policy="weekly", weekly_attribution=policy)
    metrics.create(source)
    value = record(source)
    metrics.record(value)
    first = metrics.query(MONTH, SourceSelection("all"), as_of=LATER)
    second = metrics.query(PeriodRef("month/2026-11"), SourceSelection("all"), as_of=LATER)
    assert len(first.records) == october
    assert len(second.records) == november
    assert len(first.separate_weekly) == len(second.separate_weekly) == separate
    assert sum(r.value for r in (*first.records, *second.records)) in (0, 40)


def test_weekly_observation_date_must_belong_to_source_week(services):
    _, metrics = services
    source = field(temporal_policy="weekly", weekly_attribution="end")
    metrics.create(source)
    outside_week = record(source)
    outside_week = replace(outside_week, observed_date=date(2026, 11, 2))
    with pytest.raises(ValueError, match="within its source week"):
        metrics.record(outside_week)
    assert not any(d.document.kind == "day_page" for d in metrics.session.scan().documents)


def test_missing_metric_import_remains_intelligible_and_invalid_value_reported(services, tmp_path):
    _, metrics = services
    source = field()
    definition = metrics.create(source)
    daily = metrics.record(record(source))
    target = VaultSession.create(tmp_path / "target", "Partial import")
    result = ImportService(target).import_files([daily.path])
    assert result.imported[0].missing_references[0].role == "field_id"
    query = MetricService(target).query(MONTH, SourceSelection("manual", (source.id,)), as_of=LATER)
    assert query.unresolved_records[0].field_label_snapshot == source.name
    assert query.missing_source_ids == (source.id,)
    ImportService(target).import_files([definition.path])
    assert MetricService(target).query(MONTH, SourceSelection("all"), as_of=LATER).records
    loaded = target.load(daily.document.id)
    changed = deepcopy(loaded.document)
    changed.metadata["hw"]["observations"][0]["value"] = "wrong type"
    target.save(loaded, changed)
    query = MetricService(target).query(MONTH, SourceSelection("all"), as_of=LATER)
    assert query.issues and query.unresolved_records and not query.records


def test_export_move_reopen_and_offline_cache_failure(services, tmp_path, monkeypatch):
    import socket

    layouts, _ = services
    monkeypatch.setattr(socket, "socket", lambda *a, **k: pytest.fail("Network called"))
    layout = template()
    layouts.save_revision(WEEK, layout, START)
    source = layouts.load(layout.id, 1)
    moved = layouts.session.root / "renamed.json"
    source.path.rename(moved)
    assert layouts.load(layout.id, 1).path == moved
    exported = layouts.export_template(layout.id, 1, tmp_path / "export.json")
    assert exported.read_bytes() == moved.read_bytes()
    with pytest.raises(ConflictError):
        layouts.export_template(layout.id, 1, exported)

    def fail_cache(_report):
        raise OSError("Cache unavailable")

    monkeypatch.setattr(layouts.session.index, "rebuild", fail_cache)
    revised = layout.new_revision()
    layouts.save_revision(WEEK, revised, ACTIVE)
    assert layouts.session.index_error
    assert (
        LayoutService(VaultSession.open(layouts.session.root)).resolve(WEEK, ACTIVE).layout
        == revised
    )


def test_default_history_and_snapshot_queries_no_io(services, monkeypatch):
    layouts, metrics = services
    layout = template()
    layouts.save_template(layout)
    layouts.set_default("week", Assignment(layout.id, 1, START))
    layouts.save_template(layout.new_revision(name="New default"))
    layouts.set_default("week", Assignment(layout.id, 2, ACTIVE))
    assert layouts.resolve(WEEK, START).layout == layout
    assert layouts.resolve(WEEK, ACTIVE).layout.version == 2
    report = layouts.session.report
    monkeypatch.setattr(layouts.session, "scan", lambda: pytest.fail("Unexpected I/O"))
    assert layouts.resolve_report(report, WEEK, ACTIVE).layout.version == 2
    assert not metrics.query_report(report, MONTH, SourceSelection("all"), as_of=LATER).records
