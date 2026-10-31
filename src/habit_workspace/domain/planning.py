"""Canonical personal planning; no daily occurrences or inferred progress."""

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from habit_workspace.domain.documents import civil_date, mapping, require, timestamp, uuid_value
from habit_workspace.domain.temporal import TemporalScope

GOAL_STATUSES = ("not_started", "in_progress", "achieved", "paused", "abandoned")


@dataclass(frozen=True)
class PlanningItem:
    id: UUID
    kind: str
    title: str
    scope: TemporalScope
    status: str
    tags: tuple[str, ...]
    due_date: date | None = None
    completed_at: datetime | None = None
    progress_percent: int | None = None


def planning_from_mapping(hw: dict) -> PlanningItem:
    kind = hw.get("kind")
    require(kind in ("task", "goal"), "Expected task or goal")
    title = hw.get("title")
    require(isinstance(title, str) and bool(title.strip()), "Title is required")
    scope = mapping(hw.get("scope"), "scope")
    require("end_exclusive" in scope, "scope requires end_exclusive")
    start = civil_date(scope.get("start"), "scope.start")
    end = (
        civil_date(scope["end_exclusive"], "scope.end_exclusive")
        if scope["end_exclusive"] is not None
        else None
    )
    require(end is None or end > start, "scope.end_exclusive must follow start")
    validity = TemporalScope(start, end)
    status = hw.get("status")
    require(
        status in (("pending", "completed") if kind == "task" else GOAL_STATUSES), "Invalid status"
    )
    due = completed = progress = None
    if kind == "task":
        if hw.get("due_date") is not None:
            due = civil_date(hw["due_date"], "due_date")
        if hw.get("completed_at") is not None:
            completed = timestamp(hw["completed_at"], "completed_at")
            require(status == "completed", "Pending tasks cannot have completed_at")
    else:
        progress = hw.get("progress_percent")
        require(
            progress is None or (type(progress) is int and 0 <= progress <= 100),
            "Progress must be an integer from 0 to 100",
        )
    return PlanningItem(
        uuid_value(hw.get("id"), "id"),
        kind,
        title,
        validity,
        status,
        tuple(hw.get("tags", ())),
        due,
        completed,
        progress,
    )
