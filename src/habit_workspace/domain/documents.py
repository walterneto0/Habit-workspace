"""Versioned document storage validation; inert extensions remain intact."""

import math
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from habit_workspace.domain.temporal import PeriodRef


class DocumentError(ValueError):
    """Invalid or unsupported document; original bytes must be preserved."""


class DocumentKind(StrEnum):
    TASK = "task"
    GOAL = "goal"
    NOTE = "note"
    PAGE = "page"
    DAY = "day_page"
    WEEK = "week_page"
    MONTH = "month_page"
    YEAR = "year_page"
    HABIT = "habit"
    METRIC = "metric_definition"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DocumentError(message)


def uuid_value(value: Any, label: str) -> UUID:
    require(isinstance(value, str), f"{label} must be a UUID string")
    try:
        return UUID(value)
    except ValueError as error:
        raise DocumentError(f"{label} must be a UUID string") from error


def mapping(value: Any, label: str) -> dict:
    require(isinstance(value, dict), f"{label} must be a mapping")
    return value


def sequence(value: Any, label: str) -> list:
    require(isinstance(value, list), f"{label} must be a list")
    return value


def civil_date(value: Any, label: str) -> date:
    require(
        isinstance(value, str) and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)),
        f"{label} must be an ISO date string",
    )
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise DocumentError(f"Invalid {label}: {value}") from error


def timestamp(value: Any, label: str) -> datetime:
    require(isinstance(value, str) and "T" in value, f"{label} must be an ISO timestamp")
    try:
        result = datetime.fromisoformat(value)
    except ValueError as error:
        raise DocumentError(f"Invalid {label}") from error
    require(result.tzinfo is not None, f"{label} must include a timezone")
    return result


def validate_tree(value: Any, depth: int = 0, budget: list[int] | None = None) -> None:
    """Bound even programmatically constructed trees, including accidental cycles."""
    budget = [20000] if budget is None else budget
    budget[0] -= 1
    require(depth <= 32 and budget[0] >= 0, "Metadata exceeds complexity limit")
    if isinstance(value, dict):
        for key, child in value.items():
            require(
                isinstance(key, str) and key != "<<", "Metadata keys must be strings; no merges"
            )
            validate_tree(child, depth + 1, budget)
    elif isinstance(value, list):
        for child in value:
            validate_tree(child, depth + 1, budget)
    else:
        require(
            value is None or isinstance(value, (str, bool, int, float, date, datetime)),
            "Unsupported metadata value",
        )
        if isinstance(value, float):
            require(math.isfinite(value), "Non-finite numbers are not supported")


@dataclass(frozen=True)
class Reference:
    target_id: UUID
    role: str
    version: int | None = None


@dataclass
class Document:
    """Metadata stays intact; typed identity is always derived from validated data."""

    metadata: dict[str, Any]
    body: str
    # Serialization hints, not canonical domain values.
    original_bytes: bytes | None = field(default=None, repr=False, compare=False)
    original_signature: Any = field(default=None, repr=False, compare=False)
    newline: str = field(default="\n", repr=False, compare=False)
    bom: bool = field(default=False, repr=False, compare=False)

    @classmethod
    def from_metadata(cls, metadata: dict, body: str) -> Document:
        result = cls(metadata, body)
        result.validate()
        return result

    @property
    def id(self) -> UUID:
        return uuid_value(self.metadata["hw"]["id"], "hw.id")

    @property
    def kind(self) -> DocumentKind:
        return DocumentKind(self.metadata["hw"]["kind"])

    @property
    def schema_version(self) -> int:
        return self.metadata["hw"]["schema_version"]

    @property
    def title(self) -> str:
        hw = self.metadata["hw"]
        return hw.get("title", hw.get("name", ""))

    def validate(self) -> None:
        validate_tree(self.metadata)
        hw = mapping(mapping(self.metadata, "metadata").get("hw"), "hw")
        uuid_value(hw.get("id"), "hw.id")
        require(
            isinstance(hw.get("kind"), str) and hw["kind"] in set(DocumentKind),
            "Unsupported document kind",
        )
        version = hw.get("schema_version")
        supported = (1, 4) if hw["kind"] == "habit" else (4,)
        require(
            type(version) is int and version in supported, "Unsupported document schema_version"
        )
        require(isinstance(self.body, str), "Markdown body must be text")
        for key in ("title", "name"):
            if key in hw:
                require(isinstance(hw[key], str), f"hw.{key} must be text")
        if "tags" in hw:
            require(
                all(isinstance(tag, str) for tag in sequence(hw["tags"], "tags")),
                "tags must contain strings",
            )
        if "origin_page_id" in hw and hw["origin_page_id"] is not None:
            uuid_value(hw["origin_page_id"], "origin_page_id")
        self._validate_period(hw)
        if self.kind == DocumentKind.HABIT:
            require(
                isinstance(hw.get("name"), str) and bool(hw["name"].strip()), "Habit needs name"
            )
            scope = mapping(hw.get("scope"), "scope")
            start = civil_date(scope.get("start"), "scope.start")
            require("end_exclusive" in scope, "scope requires end_exclusive (null for open scope)")
            if scope["end_exclusive"] is not None:
                require(
                    civil_date(scope["end_exclusive"], "scope.end_exclusive") > start,
                    "scope.end_exclusive must follow start",
                )
            recurrence = mapping(hw.get("recurrence"), "recurrence")
            require(recurrence.get("kind") in ("daily", "weekdays"), "Unsupported recurrence")
            if recurrence["kind"] == "weekdays":
                days = sequence(recurrence.get("days"), "recurrence.days")
                require(
                    bool(days) and all(type(d) is int and 1 <= d <= 7 for d in days),
                    "Weekdays must be integers 1–7",
                )
                require(len(days) == len(set(days)), "Weekdays must be unique")
            if hw.get("archived_at") is not None:
                timestamp(hw["archived_at"], "archived_at")
        if self.kind in (DocumentKind.TASK, DocumentKind.GOAL):
            from habit_workspace.domain.planning import planning_from_mapping

            planning_from_mapping(hw)
        if self.kind == DocumentKind.METRIC:
            from habit_workspace.domain.metrics import field_from_mapping

            try:
                field_from_mapping(hw)
            except (ValueError, TypeError, KeyError, AttributeError) as error:
                raise DocumentError(f"Invalid metric definition: {error}") from error
        previous = None
        for entry in sequence(hw.get("layout_history", []), "layout_history"):
            entry = mapping(entry, "layout assignment")
            uuid_value(entry.get("layout_id"), "layout_id")
            require(
                type(entry.get("version")) is int and entry["version"] > 0,
                "Layout version must be positive integer",
            )
            effective = timestamp(entry.get("effective_at"), "effective_at")
            require(
                previous is None or effective > previous,
                "layout_history must have strictly increasing activation times",
            )
            previous = effective
        self._validate_records(hw)

    def _validate_period(self, hw: dict) -> None:
        scale = self.kind.value.removesuffix("_page") if self.kind.value.endswith("_page") else None
        period = hw.get("period")
        if period is not None:
            require(isinstance(period, str), "period must be an ISO period string")
            try:
                parsed = PeriodRef.parse(period)
                require(
                    scale is None or parsed.scale == scale, "Period does not match document kind"
                )
            except ValueError as error:
                raise DocumentError(f"Invalid period: {period}") from error
        if "date" in hw:
            civil_date(hw["date"], "date")
            if scale == "day" and period is not None:
                require(period == "day/" + hw["date"], "date and period disagree")
        if scale:
            require(
                period is not None or (scale == "day" and "date" in hw),
                "Period page requires period (or date for a day)",
            )

    def _validate_records(self, hw: dict) -> None:
        ids: set[UUID] = set()
        habits: set[UUID] = set()
        for collection, target in (("checkins", "habit_id"), ("observations", "field_id")):
            records = sequence(hw.get(collection, []), collection)
            require(not records or self.kind == DocumentKind.DAY, "Records belong in daily pages")
            for record in records:
                record = mapping(record, collection)
                identifier = uuid_value(record.get("id"), "record.id")
                require(identifier not in ids, "Duplicate record UUID")
                ids.add(identifier)
                target_id = uuid_value(record.get(target), target)
                timestamp(record.get("recorded_at"), "recorded_at")
                key = "date" if collection == "checkins" else "observed_date"
                record_date = civil_date(record.get(key), key)
                page_date = hw.get("date", hw.get("period", "").removeprefix("day/"))
                require(
                    record_date == civil_date(page_date, "page date"),
                    "Record date must match its canonical daily page",
                )
                if collection == "checkins":
                    require(
                        record.get("state") in ("done", "missed", "skipped"),
                        "Check-in state must be an explicit result",
                    )
                    require(target_id not in habits, "Duplicate habit check-in for this day")
                    habits.add(target_id)
                    label = "label_snapshot"
                else:
                    require("value" in record, "Observation requires value")
                    label = "field_label_snapshot"
                require(isinstance(record.get(label), str), f"{label} must be text")
                if "source_period_ref" in record:
                    try:
                        PeriodRef(record["source_period_ref"])
                    except ValueError as error:
                        raise DocumentError("Invalid source_period_ref") from error
                if "historical_entry" in record:
                    require(
                        type(record["historical_entry"]) is bool, "historical_entry must be boolean"
                    )
                    require(
                        not record["historical_entry"]
                        or (
                            isinstance(record.get("provenance"), str)
                            and bool(record["provenance"].strip())
                        ),
                        "Historical entry requires provenance",
                    )
                if "source_block_id" in record:
                    uuid_value(record["source_block_id"], "source_block_id")

    def references(self) -> tuple[Reference, ...]:
        hw = self.metadata["hw"]
        result = []
        if hw.get("origin_page_id"):
            result.append(Reference(UUID(hw["origin_page_id"]), "origin_page_id"))
        for entry in hw.get("layout_history", []):
            result.append(Reference(UUID(entry["layout_id"]), "layout_id", entry["version"]))
        for collection, key in (("checkins", "habit_id"), ("observations", "field_id")):
            result.extend(Reference(UUID(entry[key]), key) for entry in hw.get(collection, []))
        return tuple(dict.fromkeys(result))
