"""File-backed habit operations and read-only temporal projections.

I/O methods are synchronous worker-thread entry points, not GUI slots. Queries
scan once; query_report can reuse an already scanned snapshot without I/O. No
method creates, changes, or infers a canonical check-in.
"""

from dataclasses import dataclass, replace
from datetime import date, datetime
from pathlib import Path
from uuid import UUID, uuid4

from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.documents import DocumentError
from habit_workspace.domain.habits import Habit
from habit_workspace.domain.temporal import PeriodRef, Recurrence, TemporalScope
from habit_workspace.vault.atomic_io import ConflictError
from habit_workspace.vault.habits import habit_document, habit_from_document
from habit_workspace.vault.scanner import FileIssue, LoadedDocument, MissingReference, ScanReport


@dataclass(frozen=True)
class LoadedHabit:
    habit: Habit
    loaded: LoadedDocument


@dataclass(frozen=True)
class RecordedCheckin:
    id: UUID
    habit_id: UUID
    date: date
    state: str
    label_snapshot: str
    recorded_at: datetime
    page_id: UUID


@dataclass(frozen=True)
class Occurrence:
    date: date
    state: str
    record: RecordedCheckin | None = None


@dataclass(frozen=True)
class HabitPeriod:
    habit: Habit
    occurrences: tuple[Occurrence, ...]


@dataclass(frozen=True)
class HabitQuery:
    period: PeriodRef
    habits: tuple[HabitPeriod, ...]
    unscheduled_records: tuple[RecordedCheckin, ...]
    unresolved_records: tuple[RecordedCheckin, ...]
    missing_references: tuple[MissingReference, ...]
    invalid: tuple[FileIssue, ...]
    index_error: str | None = None


class HistoryImpactError(DocumentError):
    def __init__(self, records: tuple[RecordedCheckin, ...]):
        self.records = records
        super().__init__(
            f"Schedule change leaves {len(records)} recorded check-in(s) outside the schedule. "
            "Review and acknowledge_history to preserve these records and continue."
        )


def _records(report: ScanReport) -> tuple[RecordedCheckin, ...]:
    return tuple(
        RecordedCheckin(
            UUID(record["id"]),
            UUID(record["habit_id"]),
            date.fromisoformat(record["date"]),
            record["state"],
            record["label_snapshot"],
            datetime.fromisoformat(record["recorded_at"]),
            loaded.document.id,
        )
        for loaded in report.documents
        for record in loaded.document.metadata["hw"].get("checkins", ())
    )


class HabitService:
    def __init__(self, session: VaultSession):
        self.session = session

    def create(
        self,
        *,
        name: str,
        period: PeriodRef,
        scope: TemporalScope | None = None,
        recurrence: Recurrence | None = None,
        tags: tuple[str, ...] = (),
        origin_page_id: UUID | None = None,
        body: str = "",
        relative: str | Path | None = None,
    ) -> LoadedHabit:
        habit = Habit(
            uuid4(),
            name,
            scope if scope is not None else period.scope,
            recurrence if recurrence is not None else Recurrence.daily(),
            tags,
            origin_page_id,
        )
        loaded = self.session.create_document(
            relative if relative is not None else f"Items/Habits/{habit.id}.md",
            habit_document(habit, body=body),
        )
        return LoadedHabit(habit_from_document(loaded.document), loaded)

    def load(self, identifier: UUID | str) -> LoadedHabit:
        loaded = self.session.load(identifier)
        return LoadedHabit(habit_from_document(loaded.document), loaded)

    def update(
        self,
        loaded: LoadedHabit,
        *,
        scope: TemporalScope | None = None,
        recurrence: Recurrence | None = None,
        acknowledge_history: bool = False,
    ) -> LoadedHabit:
        """Retain the caller's revision; never reload away a stale-edit conflict.

        Acknowledgement affects only the warning. Historical files are never edited.
        The returned definition projects the current schedule, not a versioned schedule.
        """
        current = habit_from_document(loaded.loaded.document)
        if current != loaded.habit:
            raise DocumentError("Loaded habit does not match its document snapshot")
        updated = replace(
            current,
            scope=scope if scope is not None else current.scope,
            recurrence=recurrence if recurrence is not None else current.recurrence,
        )
        affected = tuple(
            record
            for record in _records(self.session.scan())
            if record.habit_id == current.id
            and current.is_scheduled(record.date)
            and not updated.is_scheduled(record.date)
        )
        if affected and not acknowledge_history:
            raise HistoryImpactError(affected)
        saved = self.session.save(loaded.loaded, habit_document(updated, loaded.loaded.document))
        return LoadedHabit(habit_from_document(saved.document), saved)

    def query(self, period: PeriodRef, *, today: date) -> HabitQuery:
        report = self.session.scan()
        return self.query_report(report, period, today=today, index_error=self.session.index_error)

    @staticmethod
    def query_report(
        report: ScanReport,
        period: PeriodRef,
        *,
        today: date,
        index_error: str | None = None,
    ) -> HabitQuery:
        """Bounded immutable result for future data binding; no Qt, I/O or writes.

        Duplicate definitions/check-ins are explicit conflicts, never a chosen winner.
        Archived definitions remain queryable for history; archived_at is exposed on
        each Habit. Archival does not silently rewrite validity or recorded history.
        """
        if type(today) is not date:
            raise ValueError("today must be an explicit civil date")
        interval = period.scope
        definitions = {}
        conflicts = {conflict.document_id for conflict in report.conflicts}
        for loaded in report.documents:
            if loaded.document.kind == "habit":
                if loaded.document.id in conflicts:
                    raise ConflictError(f"Ambiguous habit UUID: {loaded.document.id}")
                habit = habit_from_document(loaded.document)
                definitions[habit.id] = habit
        records = {}
        record_ids = set()
        for record in _records(report):
            if not interval.contains(record.date):
                continue
            key = (record.habit_id, record.date)
            if key in records or record.id in record_ids or record.page_id in conflicts:
                raise ConflictError(f"Ambiguous check-in for {record.habit_id} on {record.date}")
            records[key] = record
            record_ids.add(record.id)
        rows = []
        for habit in sorted(definitions.values(), key=lambda h: (h.name.casefold(), str(h.id))):
            if not habit.scope.intersects(interval):
                continue
            occurrences = []
            for value in habit.recurrence.occurrences(interval, habit.scope):
                record = records.get((habit.id, value))
                state = (
                    record.state
                    if record
                    else (
                        "unrecorded" if value < today else "pending" if value == today else "future"
                    )
                )
                occurrences.append(Occurrence(value, state, record))
            rows.append(HabitPeriod(habit, tuple(occurrences)))
        return HabitQuery(
            period,
            tuple(rows),
            tuple(
                r
                for r in records.values()
                if r.habit_id in definitions and not definitions[r.habit_id].is_scheduled(r.date)
            ),
            tuple(r for r in records.values() if r.habit_id not in definitions),
            report.missing_references,
            report.invalid,
            index_error,
        )
