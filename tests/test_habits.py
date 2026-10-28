"""Canonical habit services use real Markdown; no Qt or completion writes."""

from copy import deepcopy
from datetime import date
from uuid import uuid4

import pytest
from test_vault import day, habit

from habit_workspace.application.habits import HabitService, HistoryImpactError
from habit_workspace.application.imports import ImportService
from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.documents import DocumentError
from habit_workspace.domain.temporal import PeriodRef, Recurrence, TemporalScope
from habit_workspace.vault.atomic_io import ConflictError
from habit_workspace.vault.format import decode, encode


@pytest.fixture
def service(tmp_path):
    return HabitService(VaultSession.create(tmp_path / "vault", "Phase 3"))


def create(service, **overrides):
    return service.create(name="Read", period=PeriodRef.parse("day/2026-10-27"), **overrides)


def test_default_create_update_and_shared_views(service):
    origin = uuid4()  # An absent origin is disclosed, never restricts validity.
    loaded = create(service, origin_page_id=origin, tags=(" Study ", "STUDY", "reading"))
    assert loaded.habit.scope == PeriodRef.parse("day/2026-10-27").scope
    assert loaded.habit.tags == ("study", "reading")
    updated = service.update(
        loaded,
        scope=TemporalScope.from_inclusive(date(2026, 10, 27), date(2026, 12, 31)),
        recurrence=Recurrence.weekdays((1, 2, 3, 4, 5)),
    )
    assert updated.habit.id == loaded.habit.id
    assert updated.habit.origin_page_id == origin
    for identifier in (
        "year/2026",
        "month/2026-10",
        "month/2026-12",
        "week/2026-W44",
        "day/2026-10-29",
    ):
        result = service.query(PeriodRef.parse(identifier), today=date(2026, 10, 29))
        assert [row.habit.id for row in result.habits] == [loaded.habit.id]
        assert result.missing_references[0].target_id == origin
        assert all(
            occ.record is None and occ.state != "missed" for occ in result.habits[0].occurrences
        )
    assert len(service.session.scan().documents) == 1
    assert not service.query(PeriodRef.parse("month/2027-01"), today=date(2026, 10, 29)).habits
    saturday = service.query(PeriodRef.parse("day/2026-10-31"), today=date(2026, 10, 29))
    assert saturday.habits[0].occurrences == ()  # Active does not mean scheduled/completed.


def test_real_records_remain_after_scope_and_schedule_change(service):
    loaded = create(service, scope=PeriodRef.parse("month/2026-10").scope)
    daily = service.session.create_document("arbitrary/daily.md", day(loaded.habit.id))
    raw = daily.path.read_bytes()
    weekly = service.query(PeriodRef.parse("week/2026-W44"), today=date(2026, 10, 29))
    states = {o.date: o.state for o in weekly.habits[0].occurrences}
    assert states[date(2026, 10, 26)] == "unrecorded"
    assert states[date(2026, 10, 29)] == "done"
    assert states[date(2026, 10, 30)] == "future"
    with pytest.raises(HistoryImpactError) as error:
        service.update(loaded, scope=PeriodRef.parse("day/2026-10-27").scope)
    assert len(error.value.records) == 1
    updated = service.update(
        loaded, scope=PeriodRef.parse("day/2026-10-27").scope, acknowledge_history=True
    )
    assert updated.habit.id == loaded.habit.id
    assert daily.path.read_bytes() == raw
    result = service.query(PeriodRef.parse("month/2026-10"), today=date(2026, 10, 29))
    assert len(result.unscheduled_records) == 1
    assert all(o.record is None for o in result.habits[0].occurrences)
    # Restoring eligibility restores the projection, not a new recorded fact.
    restored = service.update(updated, scope=PeriodRef.parse("month/2026-10").scope)
    with pytest.raises(HistoryImpactError):
        service.update(restored, recurrence=Recurrence.weekdays((1,)))
    assert daily.path.read_bytes() == raw


def test_restart_rename_rebuild_and_roundtrip(service):
    legacy = habit(uuid4())
    legacy.metadata["hw"]["scope"]["vendor"] = {"keep": True}
    legacy.metadata["hw"]["recurrence"]["extension"] = "keep"
    legacy.metadata["hw"]["custom"] = [1, "two"]
    original = service.session.create_document("Items/Habits/old.md", legacy)
    loaded = service.load(legacy.id)
    moved = service.session.root / "different-name.md"
    original.path.rename(moved)
    with pytest.raises(ConflictError):
        service.update(loaded, scope=TemporalScope(date(2026, 10, 27)))
    loaded = service.load(legacy.id)
    service.update(loaded, scope=TemporalScope(date(2026, 10, 27)))
    saved = decode(moved.read_bytes())
    assert saved.schema_version == 1
    assert saved.body == legacy.body
    assert saved.metadata["hw"]["scope"]["vendor"] == {"keep": True}
    assert saved.metadata["hw"]["recurrence"]["extension"] == "keep"
    assert saved.metadata["hw"]["custom"] == [1, "two"]
    assert encode(saved) == moved.read_bytes()
    expected = service.query(PeriodRef.parse("week/2026-W44"), today=date(2026, 10, 29))
    raw = moved.read_bytes()
    service.session.index.path.unlink()
    reopened = HabitService(VaultSession.open(service.session.root))
    assert reopened.query(PeriodRef.parse("week/2026-W44"), today=date(2026, 10, 29)) == expected
    assert reopened.load(legacy.id).loaded.path == moved
    assert moved.read_bytes() == raw
    assert len(reopened.session.index.documents(str(legacy.id))) == 1


def test_missing_imported_habit_and_duplicate_conflicts(service, tmp_path):
    identifier = uuid4()
    source = tmp_path / "day.md"
    source.write_bytes(encode(day(identifier)))
    ImportService(service.session).import_files([source])
    result = service.query(PeriodRef.parse("week/2026-W44"), today=date(2026, 10, 29))
    assert not result.habits
    assert result.missing_references[0].target_id == identifier
    assert len(result.unresolved_records) == 1
    source.write_bytes(encode(habit(identifier)))
    ImportService(service.session).import_files([source])
    assert not service.query(
        PeriodRef.parse("week/2026-W44"), today=date(2026, 10, 29)
    ).missing_references
    loaded = service.load(identifier)
    (service.session.root / "duplicate.md").write_bytes(loaded.loaded.path.read_bytes())
    with pytest.raises(ConflictError):
        service.load(identifier)
    with pytest.raises(ConflictError):
        service.query(PeriodRef.parse("week/2026-W44"), today=date(2026, 10, 29))


def test_external_edit_and_ambiguous_daily_records(service):
    loaded = create(service, scope=PeriodRef.parse("month/2026-10").scope)
    loaded.loaded.path.write_bytes(loaded.loaded.path.read_bytes() + b"External note\n")
    with pytest.raises(ConflictError):
        service.update(loaded, recurrence=Recurrence.weekdays((1,)))
    first = service.session.create_document("day-one.md", day(loaded.habit.id))
    second = deepcopy(first.document)
    second.metadata["hw"]["id"] = str(uuid4())
    service.session.create_document("day-two.md", second)
    with pytest.raises(ConflictError, match="check-in"):
        service.query(PeriodRef.parse("week/2026-W44"), today=date(2026, 10, 29))


def test_pending_is_not_recorded_and_queries_do_not_write(service):
    loaded = create(service)
    before = loaded.loaded.path.read_bytes()
    result = service.query(PeriodRef.parse("day/2026-10-27"), today=date(2026, 10, 27))
    occurrence = result.habits[0].occurrences[0]
    assert occurrence.state == "pending" and occurrence.record is None
    assert loaded.loaded.path.read_bytes() == before
    assert len(service.session.scan().documents) == 1


def test_invalid_lifecycle_metadata_is_preserved_as_error(service):
    loaded = create(service)
    bad = deepcopy(loaded.loaded.document)
    bad.metadata["hw"]["archived_at"] = "yesterday"
    with pytest.raises(DocumentError):
        encode(bad)


@pytest.mark.parametrize(
    "identifier", ["year/2026", "month/2026-10", "week/2026-W44", "day/2026-10-27"]
)
def test_habit_creation_defaults_and_override(service, identifier):
    period = PeriodRef.parse(identifier)
    default = service.create(name="Default", period=period)
    assert default.habit.scope == period.scope
    custom = service.create(name="Custom", period=period, scope=TemporalScope(date(2027, 1, 1)))
    assert custom.habit.scope.end_exclusive is None
    assert custom.habit.scope.start == date(2027, 1, 1)


def test_codec_preserves_comments_line_endings_versions_and_archive(service):
    identifier = uuid4()
    raw = (
        "\ufeff---\r\nhw:\r\n  schema_version: 1\r\n  kind: habit\r\n"
        f'  id: "{identifier}" # stable\r\n'
        '  name: Read\r\n  tags: [STUDY]\r\n  archived_at: "2026-11-01T12:00:00-03:00"\r\n'
        '  scope:\r\n    start: "2026-10-01" # keep this comment\r\n    end_exclusive: null\r\n'
        "  recurrence:\r\n    kind: daily\r\n    vendor: [keep]\r\n"
        'extra: "Keep me"\r\n---\r\n# Human notes\r\n  **Keep** spacing.\r\n'
    ).encode()
    path = service.session.root / "legacy.md"
    path.write_bytes(raw)
    loaded = service.load(identifier)
    assert loaded.habit.archived_at.isoformat() == "2026-11-01T12:00:00-03:00"
    service.update(loaded, recurrence=Recurrence.weekdays((1, 3, 5)))
    changed = path.read_bytes()
    assert b"# stable" in changed and b"# keep this comment" in changed
    assert changed.startswith(b"\xef\xbb\xbf---\r\n")
    assert decode(changed).body == decode(raw).body
    assert decode(changed).metadata["hw"]["tags"] == ["STUDY"]
    assert decode(changed).schema_version == 1
    assert decode(changed).metadata["extra"] == "Keep me"
    loaded = service.load(identifier)
    service.update(loaded, recurrence=Recurrence.daily())
    assert "days" not in decode(path.read_bytes()).metadata["hw"]["recurrence"]
    assert decode(path.read_bytes()).metadata["hw"]["recurrence"]["vendor"] == ["keep"]


def test_normalized_tag_collisions_do_not_merge_habit_identities(service):
    first = create(service, tags=("  CAFÉ  ", "cafe\u0301", "", "Study", "study"))
    second = create(service, tags=("café",))
    assert first.habit.tags == ("café", "study")
    assert first.habit.id != second.habit.id


def test_external_scope_edits_refresh_queries(service):
    loaded = create(service)
    document = decode(loaded.loaded.path.read_bytes())
    document.metadata["hw"]["scope"]["end_exclusive"] = "2027-01-01"
    document.metadata["hw"]["recurrence"] = {"kind": "weekdays", "days": [1]}
    loaded.loaded.path.write_bytes(encode(document))
    result = service.query(PeriodRef.parse("week/2026-W45"), today=date(2026, 10, 29))
    assert [o.date for o in result.habits[0].occurrences] == [date(2026, 11, 2)]
    assert result.habits[0].habit.id == loaded.habit.id


def test_cache_failure_does_not_undo_canonical_habit_write(service, monkeypatch):
    def unavailable(_report):
        raise OSError("diagnostic cache failure")

    monkeypatch.setattr(service.session.index, "rebuild", unavailable)
    loaded = create(service)
    result = service.query(PeriodRef.parse("day/2026-10-27"), today=date(2026, 10, 27))
    assert result.habits[0].habit.id == loaded.habit.id
    assert "diagnostic cache failure" in result.index_error
    assert service.load(loaded.habit.id).habit == loaded.habit


def test_readonly_snapshot_query_needs_no_filesystem(service, monkeypatch):
    create(service)
    report = service.session.report

    def forbidden():
        raise AssertionError("Snapshot query must not perform file I/O")

    monkeypatch.setattr(service.session, "scan", forbidden)
    result = HabitService.query_report(
        report, PeriodRef.parse("day/2026-10-27"), today=date(2026, 10, 27)
    )
    assert len(result.habits) == 1
