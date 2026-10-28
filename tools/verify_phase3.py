"""Phase 3 acceptance demonstration using generated canonical files in a temporary vault."""

import json
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from habit_workspace.application.habits import HabitService, HistoryImpactError
from habit_workspace.application.imports import ImportService
from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.documents import Document
from habit_workspace.domain.temporal import PeriodRef, Recurrence, TemporalScope


def demonstrate(base: Path) -> dict:
    session = VaultSession.create(base / "vault", "Phase 3 generated demonstration")
    service = HabitService(session)
    today = date(2026, 10, 29)
    origin = session.create_document(
        "arbitrary-origin.md",
        Document.from_metadata(
            {
                "hw": {
                    "schema_version": 4,
                    "kind": "day_page",
                    "id": str(uuid4()),
                    "date": "2026-10-27",
                    "title": "Generated origin page",
                }
            },
            "# Generated data\n\nCreation context is not the validity interval.\n",
        ),
    )
    initial = service.create(
        name="Read — generated demonstration",
        period=PeriodRef.parse("day/2026-10-27"),
        origin_page_id=origin.document.id,
        tags=("study",),
        body="# Read\n\nHuman Markdown remains canonical and editable.\n",
    )
    assert initial.habit.scope == PeriodRef.parse("day/2026-10-27").scope
    updated = service.update(
        initial,
        scope=TemporalScope.from_inclusive(date(2026, 10, 27), date(2026, 12, 31)),
        recurrence=Recurrence.weekdays((1, 2, 3, 4, 5)),
    )
    identity = updated.habit.id
    by_period = {}
    for identifier in ("year/2026", "month/2026-10", "week/2026-W44", "day/2026-10-29"):
        query = service.query(PeriodRef.parse(identifier), today=today)
        assert len(query.habits) == 1 and query.habits[0].habit.id == identity
        assert all(o.record is None and o.state != "missed" for o in query.habits[0].occurrences)
        by_period[identifier] = [o.date.isoformat() for o in query.habits[0].occurrences]
    assert by_period["week/2026-W44"] == ["2026-10-27", "2026-10-28", "2026-10-29", "2026-10-30"]
    assert len(by_period["year/2026"]) == 48
    # This pre-existing record fixture uses the Phase 1 format, not a capture service.
    daily = session.create_document(
        "history.md",
        Document.from_metadata(
            {
                "hw": {
                    "schema_version": 4,
                    "kind": "day_page",
                    "id": str(uuid4()),
                    "date": "2026-10-29",
                    "checkins": [
                        {
                            "id": str(uuid4()),
                            "habit_id": str(identity),
                            "date": "2026-10-29",
                            "state": "done",
                            "label_snapshot": "Read — generated demonstration",
                            "recorded_at": "2026-10-29T12:00:00-03:00",
                        }
                    ],
                }
            },
            "# Generated historical record\n\nThis note must survive scope edits.\n",
        ),
    )
    historical_bytes = daily.path.read_bytes()
    try:
        service.update(updated, scope=initial.habit.scope)
    except HistoryImpactError as error:
        assert len(error.records) == 1
    else:
        raise AssertionError("History impact must be disclosed")
    shortened = service.update(updated, scope=initial.habit.scope, acknowledge_history=True)
    assert daily.path.read_bytes() == historical_bytes
    assert (
        len(service.query(PeriodRef.parse("month/2026-10"), today=today).unscheduled_records) == 1
    )
    restored = service.update(shortened, scope=updated.habit.scope)
    moved = session.root / "unrelated-folder/renamed-habit.md"
    moved.parent.mkdir()
    restored.loaded.path.rename(moved)
    assert service.load(identity).loaded.path == moved
    assert not session.scan().missing_references
    week = PeriodRef.parse("week/2026-W44")
    before = service.query(week, today=today)
    canonical = {entry.path: entry.path.read_bytes() for entry in session.report.documents}
    session.index.path.unlink()
    reopened = HabitService(VaultSession.open(session.root))
    assert reopened.query(week, today=today) == before
    assert all(path.read_bytes() == raw for path, raw in canonical.items())
    assert len(reopened.session.index.documents(str(identity))) == 1
    assert sum(entry.document.kind == "habit" for entry in reopened.session.report.documents) == 1
    # Import the daily page alone, then its dependency, without synthesizing a habit.
    target = VaultSession.create(base / "import-target", "Generated import target")
    importer = ImportService(target)
    importer.import_files([daily.path])
    partial = HabitService(target).query(week, today=today)
    assert not partial.habits and len(partial.unresolved_records) == 1
    importer.import_files([moved, origin.path])
    complete = HabitService(target).query(week, today=today)
    assert not complete.missing_references
    assert complete.habits == before.habits
    return {
        "result": "PASS",
        "habit_id": str(identity),
        "default_scope": {"start": "2026-10-27", "end_exclusive": "2026-10-28"},
        "updated_scope": {"start": "2026-10-27", "end_exclusive": "2027-01-01"},
        "total_expected_weekdays": len(by_period["year/2026"]),
        "week_2026_W44": by_period["week/2026-W44"],
        "week_states_after_imported_record": [o.state for o in before.habits[0].occurrences],
        "one_habit_across_four_views": True,
        "history_preserved_after_scope_edit": True,
        "uuid_references_survive_move_and_restart": True,
        "index_rebuild_preserves_queries_and_file_bytes": True,
        "partial_import_discloses_missing_habit": True,
        "canonical_habit_markdown": moved.read_text(encoding="utf-8"),
    }


def main() -> None:
    with TemporaryDirectory(prefix="habit-workspace-phase3-") as directory:
        print(json.dumps(demonstrate(Path(directory)), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
