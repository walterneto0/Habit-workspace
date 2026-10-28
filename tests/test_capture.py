"""Phase 6 canonical capture: check-ins by habit_id, observations by field_id."""

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest

from habit_workspace.application.capture import (
    UNCHECKED,
    CaptureService,
    CaptureSnapshot,
    parse_value,
)
from habit_workspace.application.habits import HabitService, HistoryImpactError
from habit_workspace.application.metrics import MetricService
from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.documents import DocumentError
from habit_workspace.domain.layouts import (
    Binding,
    ChecklistConfig,
    Component,
    InputConfig,
)
from habit_workspace.domain.metrics import FieldDefinition, SourceSelection
from habit_workspace.domain.temporal import PeriodRef, Recurrence, TemporalScope
from habit_workspace.vault.atomic_io import ConflictError

TZ = timezone(timedelta(hours=-3))
TODAY = date(2026, 10, 29)  # Thursday, ISO week 2026-W44 (Oct 26 – Nov 1).
NOW = datetime(2026, 10, 29, 19, 12, tzinfo=TZ)
ACTIVE = datetime(2026, 10, 29, 10, 0, tzinfo=TZ)


@pytest.fixture
def session(tmp_path):
    return VaultSession.create(tmp_path / "vault", "Phase 6")


def make_habit(session, *, period="week/2026-W44", **overrides):
    return HabitService(session).create(
        name=overrides.pop("name", "Estudar Python"), period=PeriodRef(period), **overrides
    )


def make_field(session, value_type="integer", *, active=ACTIVE, **overrides):
    field = FieldDefinition(
        uuid4(), overrides.pop("name", "Tempo de estudo"), value_type, active, **overrides
    )
    MetricService(session).create(field)
    return field


def day_records(session, day, collection):
    pages = [
        d
        for d in session.scan().documents
        if d.document.kind == "day_page" and d.document.metadata["hw"].get("date") == day
    ]
    assert len(pages) <= 1
    return pages[0].document.metadata["hw"].get(collection, []) if pages else []


def checkin(session, habit_id, day, state, **kwargs):
    return CaptureService(session).set_checkin(
        habit_id, day, state, today=kwargs.pop("today", TODAY), recorded_at=NOW, **kwargs
    )


def observe(session, field_id, day, value, **kwargs):
    return CaptureService(session).set_observation(
        field_id, day, value, today=kwargs.pop("today", TODAY), recorded_at=NOW, **kwargs
    )


def test_default_and_overridden_scope_with_weekday_recurrence(session):
    default = make_habit(session)
    assert default.habit.scope == PeriodRef("week/2026-W44").scope
    override = make_habit(
        session,
        name="Ler",
        scope=TemporalScope.from_inclusive(date(2026, 10, 1), date(2026, 12, 31)),
        recurrence=Recurrence.weekdays((1, 3, 5)),
        tags=(" Estudos ", "ESTUDOS"),
    )
    assert override.habit.tags == ("estudos",)
    assert override.habit.scope.end_exclusive == date(2027, 1, 1)
    snapshot = CaptureSnapshot(session.report, date(2026, 10, 27), TODAY)  # Tuesday
    assert snapshot.habit_cell(override.habit.id).state == "not_scheduled"
    assert snapshot.habit_cell(default.habit.id).state == "unrecorded"
    with pytest.raises(DocumentError, match="programado"):
        checkin(session, override.habit.id, date(2026, 10, 27), "done")
    assert not day_records(session, "2026-10-27", "checkins")


def test_iso_week_across_month_and_year_boundaries(session):
    habit = make_habit(session, period="week/2026-W53")  # Dec 28 2026 – Jan 3 2027.
    assert habit.habit.scope.contains(date(2027, 1, 3))
    today = date(2027, 1, 2)
    for value in (date(2026, 12, 31), date(2027, 1, 1)):
        assert checkin(session, habit.habit.id, value, "done", today=today).action == "created"
    month = HabitService(session).query(PeriodRef("month/2027-01"), today=today)
    assert [o.state for o in month.habits[0].occurrences] == ["done", "pending", "future"]
    week = HabitService(session).query(PeriodRef("week/2026-W44"), today=TODAY)
    assert not week.habits
    crossing = make_habit(session, name="Caminhar", period="week/2026-W44")
    checkin(session, crossing.habit.id, date(2026, 10, 26), "done")
    november = HabitService(session).query(PeriodRef("month/2026-11"), today=date(2026, 11, 2))
    assert [o.state for o in november.habits[0].occurrences] == ["unrecorded"]  # Nov 1.


def test_create_correct_clear_and_idempotent_checkin(session):
    habit = make_habit(session).habit
    first = checkin(session, habit.id, TODAY, "done", expected=None)
    assert first.action == "created"
    record_id = first.record["id"]
    page_bytes = first.page.path.read_bytes()
    assert checkin(session, habit.id, TODAY, "done").action == "unchanged"
    assert first.page.path.read_bytes() == page_bytes
    corrected = checkin(session, habit.id, TODAY, "skipped", expected="done")
    assert corrected.action == "updated" and corrected.record["id"] == record_id
    records = day_records(session, "2026-10-29", "checkins")
    assert len(records) == 1 and records[0]["state"] == "skipped"
    assert checkin(session, habit.id, TODAY, None, expected="skipped").action == "cleared"
    assert day_records(session, "2026-10-29", "checkins") == []
    assert not day_records(session, "2026-10-29", "observations")
    again = checkin(session, habit.id, TODAY, "done")
    assert len(day_records(session, "2026-10-29", "checkins")) == 1
    assert again.page.path == first.page.path  # Same canonical day page, never a second one.
    pages = [d for d in session.scan().documents if d.document.kind == "day_page"]
    assert len(pages) == 1


def test_correction_preserves_unknown_record_metadata_and_page_body(session):
    habit = make_habit(session).habit
    created = checkin(session, habit.id, TODAY, "done")
    raw = created.page.path.read_text()
    raw = raw.replace("state: done", "state: done\n    custom_note: kept").replace(
        "---\n", "---\n", 1
    )
    created.page.path.write_text(raw + "\nMinhas anotações do dia.\n")
    session.scan()
    checkin(session, habit.id, TODAY, "missed", expected="done")
    record = day_records(session, "2026-10-29", "checkins")[0]
    assert record["custom_note"] == "kept" and record["state"] == "missed"
    assert "Minhas anotações do dia." in created.page.path.read_text()


def test_future_unrecorded_and_pending_never_become_missed(session):
    habit = make_habit(session).habit
    with pytest.raises(DocumentError, match="futuras"):
        checkin(session, habit.id, TODAY + timedelta(days=1), "done")
    result = HabitService(session).query(PeriodRef("week/2026-W44"), today=TODAY)
    states = [o.state for o in result.habits[0].occurrences]
    assert states == ["unrecorded"] * 3 + ["pending"] + ["future"] * 3
    assert not any(d.document.kind == "day_page" for d in session.scan().documents)


def test_numeric_observation_create_edit_validate_and_clear(session):
    field = make_field(session, minimum=0, maximum=600, unit="minutes")
    assert parse_value(field, " 40 ") == 40
    with pytest.raises(ValueError):
        parse_value(field, "40,5")  # integer field
    with pytest.raises(ValueError):
        parse_value(field, "999")  # above maximum
    created = observe(
        session,
        field.id,
        TODAY,
        40,
        expected=None,
        source_period=PeriodRef("week/2026-W44"),
        source_block_id=(block := uuid4()),
    )
    assert created.action == "created"
    record = day_records(session, "2026-10-29", "observations")[0]
    assert record["field_id"] == str(field.id) and record["value"] == 40
    assert record["source_period_ref"] == "week/2026-W44"
    assert record["source_block_id"] == str(block)
    assert observe(session, field.id, TODAY, 40).action == "unchanged"
    updated = observe(session, field.id, TODAY, 45, expected=40)
    assert updated.action == "updated" and updated.record["id"] == record["id"]
    with pytest.raises(ValueError):
        observe(session, field.id, TODAY, 40.5)
    with pytest.raises(ValueError):
        observe(session, field.id, TODAY, -1)
    assert day_records(session, "2026-10-29", "observations")[0]["value"] == 45
    assert observe(session, field.id, TODAY, None, expected=45).action == "cleared"
    assert day_records(session, "2026-10-29", "observations") == []
    number = make_field(session, "number", name="Horas")
    assert parse_value(number, "1,5") == 1.5 and parse_value(number, "2") == 2


def test_pre_activation_and_future_observations_are_rejected_without_inference(session):
    field = make_field(session)
    with pytest.raises(DocumentError, match="ativação"):
        observe(session, field.id, date(2026, 10, 28), 10)
    snapshot = CaptureSnapshot(session.scan(), date(2026, 10, 28), TODAY)
    cell = snapshot.field_cell(field.id)
    assert not cell.editable and cell.value is None and "falha" in cell.note
    with pytest.raises(DocumentError, match="futuras"):
        observe(session, field.id, TODAY + timedelta(days=1), 10)
    weekly = FieldDefinition(
        uuid4(),
        "Semanal",
        "integer",
        ACTIVE,
        temporal_policy="weekly",
        weekly_attribution="start",
    )
    MetricService(session).create(weekly)
    with pytest.raises(DocumentError, match="semanais"):
        observe(session, weekly.id, TODAY, 1)
    assert not any(d.document.kind == "day_page" for d in session.scan().documents)


def test_checkins_and_observations_never_share_a_fact(session):
    habit = make_habit(session).habit
    flag = make_field(session, "boolean", name="Meditou")
    with pytest.raises(DocumentError, match="check-ins"):
        observe(session, habit.id, TODAY, True)
    with pytest.raises(DocumentError, match="Hábito ausente"):
        checkin(session, flag.id, TODAY, "done")
    checkin(session, habit.id, TODAY, "done")
    observe(session, flag.id, TODAY, True)
    checkins = day_records(session, "2026-10-29", "checkins")
    observations = day_records(session, "2026-10-29", "observations")
    assert [r["habit_id"] for r in checkins] == [str(habit.id)]
    assert [r["field_id"] for r in observations] == [str(flag.id)]
    assert {r["id"] for r in checkins}.isdisjoint(r["id"] for r in observations)
    # A habit-bound checklist and a boolean-field checklist read different records.
    snapshot = CaptureSnapshot(session.report, TODAY, TODAY)
    habit_block = Component(
        uuid4(), "checklist", "H", ChecklistConfig(), binding=Binding(habit.id, "habit")
    )
    field_block = Component(
        uuid4(), "checklist", "F", ChecklistConfig(), binding=Binding(flag.id, "metric")
    )
    assert snapshot.block(habit_block)[0].state == "done"
    assert snapshot.block(field_block)[0].value is True


def test_dynamic_checklist_enumerates_habits_and_boolean_fields_by_tag(session):
    study = make_habit(session, tags=("estudos",)).habit
    make_habit(session, name="Outro", tags=("casa",))
    flag = make_field(session, "boolean", name="Revisou", tags=("estudos",))
    make_field(session, "integer", name="Minutos", tags=("estudos",))
    selection = SourceSelection("by_tags", tags=("estudos",), value_types=("habit", "boolean"))
    block = Component(uuid4(), "checklist", "Estudos", ChecklistConfig(selection))
    cells = CaptureSnapshot(session.report, TODAY, TODAY).block(block)
    assert [getattr(c, "habit_id", None) or c.field_id for c in cells] == [study.id, flag.id]


def test_scope_change_after_checkins_preserves_records(session):
    loaded = make_habit(session, scope=PeriodRef("month/2026-10").scope)
    checkin(session, loaded.habit.id, date(2026, 10, 27), "done")
    service = HabitService(session)
    with pytest.raises(HistoryImpactError):
        service.update(loaded, recurrence=Recurrence.weekdays((4,)))
    updated = service.update(
        loaded, recurrence=Recurrence.weekdays((4,)), name="Python", acknowledge_history=True
    )
    assert updated.habit.name == "Python" and updated.habit.id == loaded.habit.id
    assert day_records(session, "2026-10-27", "checkins")[0]["state"] == "done"
    cell = CaptureSnapshot(session.scan(), date(2026, 10, 27), TODAY).habit_cell(loaded.habit.id)
    assert cell.state == "done" and not cell.editable and "preservado" in cell.note
    with pytest.raises(DocumentError, match="programado"):
        checkin(session, loaded.habit.id, date(2026, 10, 27), None)
    query = service.query(PeriodRef("week/2026-W44"), today=TODAY)
    assert [r.date for r in query.unscheduled_records] == [date(2026, 10, 27)]


def test_restart_and_index_rebuild_keep_records(session, tmp_path):
    habit = make_habit(session).habit
    field = make_field(session)
    checkin(session, habit.id, TODAY, "done")
    observe(session, field.id, TODAY, 40)
    session.index.path.unlink()
    reopened = VaultSession.open(session.root)
    assert reopened.index.path.exists()
    snapshot = CaptureSnapshot(reopened.report, TODAY, TODAY)
    assert snapshot.habit_cell(habit.id).state == "done"
    assert snapshot.field_cell(field.id).value == 40
    assert observe(reopened, field.id, TODAY, 40).action == "unchanged"


def test_external_edit_conflict_and_missing_references(session):
    habit = make_habit(session).habit
    field = make_field(session)
    created = checkin(session, habit.id, TODAY, "done")
    observe(session, field.id, TODAY, 40)
    path = created.page.path
    path.write_text(path.read_text().replace("state: done", "state: skipped"))
    with pytest.raises(ConflictError, match="mudou"):
        checkin(session, habit.id, TODAY, "missed", expected="done")
    assert day_records(session, "2026-10-29", "checkins")[0]["state"] == "skipped"
    path.write_text(path.read_text().replace("value: 40", "value: 50"))
    with pytest.raises(ConflictError):
        observe(session, field.id, TODAY, 60, expected=40)
    assert day_records(session, "2026-10-29", "observations")[0]["value"] == 50
    # Expected value types matter: True is not the integer 1.
    with pytest.raises(ConflictError):
        observe(session, field.id, TODAY, 60, expected=50.0)
    missing = uuid4()
    with pytest.raises(DocumentError, match="ausente"):
        checkin(session, missing, TODAY, "done")
    with pytest.raises(DocumentError, match="ausente"):
        observe(session, missing, TODAY, 1)
    cell = CaptureSnapshot(session.scan(), TODAY, TODAY).habit_cell(missing)
    assert not cell.editable and "ausente" in cell.note
    assert UNCHECKED is not None


def test_missing_habit_shows_saved_label_without_recreating(session):
    habit = make_habit(session).habit
    checkin(session, habit.id, TODAY, "done")
    definition = next(d for d in session.scan().documents if d.document.kind == "habit")
    definition.path.unlink()
    snapshot = CaptureSnapshot(session.scan(), TODAY, TODAY)
    cell = snapshot.habit_cell(habit.id)
    assert (cell.name, cell.state, cell.editable) == ("Estudar Python", "done", False)
    with pytest.raises(DocumentError):
        checkin(session, habit.id, TODAY, None)
    assert day_records(session, "2026-10-29", "checkins")[0]["state"] == "done"
    assert not any(d.document.kind == "habit" for d in session.scan().documents)


def test_input_block_and_duplicate_ambiguity(session):
    field = make_field(session)
    block = Component(
        uuid4(),
        "integer_input",
        "Tempo",
        InputConfig("integer"),
        binding=Binding(field.id, "metric"),
    )
    cell = CaptureSnapshot(session.report, TODAY, TODAY).block(block)[0]
    assert cell.editable and cell.value is None and cell.unit is None
    habit = make_habit(session).habit
    created = checkin(session, habit.id, TODAY, "done")
    clone = created.page.path.read_text().replace(str(created.page.document.id), str(uuid4()))
    (session.root / "Pages" / "copy.md").write_text(clone)
    with pytest.raises(ConflictError):
        checkin(session, habit.id, TODAY, "skipped")
    snapshot = CaptureSnapshot(session.scan(), TODAY, TODAY)
    assert snapshot.error and not snapshot.habit_cell(habit.id).editable
