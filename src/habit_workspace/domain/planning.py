"""Canonical personal planning; no daily occurrences or inferred progress."""

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from habit_workspace.domain.documents import civil_date, mapping, require, timestamp, uuid_value
from habit_workspace.domain.temporal import PeriodRef, TemporalScope

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
        if "home_period_ref" in hw:
            PeriodRef(hw["home_period_ref"])
        if "tracking" in hw:
            tracking = mapping(hw["tracking"], "tracking")
            require(tracking.get("mode") in ("home_only", "periodic"), "Invalid tracking mode")
            if tracking["mode"] == "periodic":
                home = goal_home(hw, validity)
                require(home is not None, "Escolha o período do objetivo.")
                scales = ("year", "month", "week", "day")
                cadence = tracking.get("granularity")
                require(
                    cadence in scales[scales.index(home.scale) + 1 :],
                    "Cadência deve ser menor que o período.",
                )
            else:
                require("granularity" not in tracking, "Home-only tracking has no granularity")
        records = hw.get("followups", [])
        require(isinstance(records, list), "followups must be a list")
        seen, identifiers = set(), set()
        for record in records:
            record = mapping(record, "followup")
            identifier = uuid_value(record.get("id"), "followup.id")
            require(identifier not in identifiers, "Duplicate followup UUID")
            identifiers.add(identifier)
            require(record.get("goal_id") == hw["id"], "Invalid followup goal reference")
            ref = PeriodRef(record.get("period"))
            require(ref.scale != "year", "Followup must be month, week or day")
            period = str(ref)
            require(period not in seen, "Duplicate followup period")
            seen.add(period)
            require(isinstance(record.get("commentary"), str), "Commentary must be Markdown")
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


def goal_home(hw, scope):
    if hw.get("home_period_ref"):
        return PeriodRef(hw["home_period_ref"])
    for scale in ("year", "month", "week", "day"):
        candidate = PeriodRef.containing(scale, scope.start)
        if candidate.scope == scope:
            return candidate
    return None
