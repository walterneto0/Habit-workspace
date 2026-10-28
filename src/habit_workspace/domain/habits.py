"""Canonical habit definition; occurrences never imply a recorded completion."""

import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from habit_workspace.domain.temporal import Recurrence, TemporalScope


def normalize_tags(tags: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(tags, tuple) or any(not isinstance(tag, str) for tag in tags):
        raise ValueError("Tags must be a tuple of strings")
    return tuple(
        dict.fromkeys(
            normalized
            for tag in tags
            if (normalized := unicodedata.normalize("NFC", tag.strip().casefold()))
        )
    )


@dataclass(frozen=True)
class Habit:
    id: UUID
    name: str
    scope: TemporalScope
    recurrence: Recurrence
    tags: tuple[str, ...] = ()
    origin_page_id: UUID | None = None
    archived_at: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID):
            raise ValueError("Habit identity must be a UUID")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Habit needs a name")
        if not isinstance(self.scope, TemporalScope) or not isinstance(self.recurrence, Recurrence):
            raise ValueError("Habit needs a typed scope and recurrence")
        if self.origin_page_id is not None and not isinstance(self.origin_page_id, UUID):
            raise ValueError("Origin page must be a UUID")
        if self.archived_at is not None and (
            not isinstance(self.archived_at, datetime) or self.archived_at.utcoffset() is None
        ):
            raise ValueError("archived_at must include a timezone")
        object.__setattr__(self, "tags", normalize_tags(self.tags))

    def is_scheduled(self, value: date) -> bool:
        return self.scope.contains(value) and self.recurrence.matches(value)
