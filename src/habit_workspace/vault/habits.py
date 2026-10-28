"""Map canonical habit fields without rebuilding or discarding document extensions."""

from copy import deepcopy
from datetime import date
from uuid import UUID

from habit_workspace.domain.documents import Document, DocumentError, timestamp
from habit_workspace.domain.habits import Habit
from habit_workspace.domain.temporal import Recurrence, RecurrenceKind, TemporalScope


def habit_from_document(document: Document) -> Habit:
    document.validate()
    if document.kind != "habit":
        raise DocumentError("Document is not a habit")
    hw = document.metadata["hw"]
    scope, recurrence = hw["scope"], hw["recurrence"]
    return Habit(
        id=document.id,
        name=hw["name"],
        scope=TemporalScope(
            date.fromisoformat(scope["start"]),
            date.fromisoformat(scope["end_exclusive"]) if scope["end_exclusive"] else None,
        ),
        recurrence=Recurrence(
            RecurrenceKind(recurrence["kind"]),
            tuple(recurrence["days"]) if recurrence["kind"] == "weekdays" else (),
        ),
        tags=tuple(hw.get("tags", ())),
        origin_page_id=UUID(hw["origin_page_id"]) if hw.get("origin_page_id") else None,
        archived_at=timestamp(hw["archived_at"], "archived_at") if hw.get("archived_at") else None,
    )


def habit_document(habit: Habit, original: Document | None = None, *, body: str = "") -> Document:
    """New documents use v4. Updates preserve the existing version, notes and extensions."""
    previous = habit_from_document(original) if original is not None else None
    if previous is not None and previous.id != habit.id:
        raise DocumentError("Saving cannot change a habit's UUID")
    document = (
        deepcopy(original)
        if original is not None
        else Document.from_metadata(
            {
                "hw": {
                    "schema_version": 4,
                    "kind": "habit",
                    "id": str(habit.id),
                    "name": habit.name,
                    "scope": {"start": habit.scope.start.isoformat(), "end_exclusive": None},
                    "recurrence": {"kind": "daily"},
                }
            },
            body,
        )
    )
    hw = document.metadata["hw"]
    if previous is None or previous.name != habit.name:
        hw["name"] = habit.name
    if previous is None or previous.tags != habit.tags:
        hw["tags"] = list(habit.tags)
    if previous is None or previous.scope != habit.scope:
        hw["scope"]["start"] = habit.scope.start.isoformat()
        hw["scope"]["end_exclusive"] = (
            habit.scope.end_exclusive.isoformat() if habit.scope.end_exclusive else None
        )
    if previous is None or previous.recurrence != habit.recurrence:
        hw["recurrence"]["kind"] = habit.recurrence.kind.value
        if habit.recurrence.kind == RecurrenceKind.WEEKDAYS:
            hw["recurrence"]["days"] = list(habit.recurrence.days)
        else:
            hw["recurrence"].pop("days", None)
    if previous is None or previous.origin_page_id != habit.origin_page_id:
        if habit.origin_page_id is not None or "origin_page_id" in hw:
            hw["origin_page_id"] = str(habit.origin_page_id) if habit.origin_page_id else None
    if previous is None or previous.archived_at != habit.archived_at:
        if habit.archived_at is not None or "archived_at" in hw:
            hw["archived_at"] = habit.archived_at.isoformat() if habit.archived_at else None
    document.validate()
    return document
