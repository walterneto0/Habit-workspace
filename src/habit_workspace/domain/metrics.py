"""Typed sources and dated facts. No layout, filesystem, Qt, or cache ownership."""

import math
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from habit_workspace.domain.habits import normalize_tags
from habit_workspace.domain.temporal import PeriodRef

ValueType = Literal[
    "text", "integer", "number", "date", "duration", "boolean", "selection", "rating", "time"
]
VALUE_TYPES = (
    "text",
    "integer",
    "number",
    "date",
    "duration",
    "boolean",
    "selection",
    "rating",
    "time",
)
type Scalar = str | int | float | bool


def check(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def aware(value: datetime) -> None:
    check(isinstance(value, datetime) and value.utcoffset() is not None, "Timestamp needs timezone")


def identity(value: UUID) -> None:
    check(isinstance(value, UUID), "Identity must be a UUID")


def text(value: str, *, nonempty: bool = False) -> None:
    check(isinstance(value, str) and (not nonempty or bool(value.strip())), "Expected text")


def typed_value(kind: str, value: Scalar) -> None:
    check(kind in VALUE_TYPES, "Unsupported value_type")
    if kind in ("number", "duration", "rating"):
        check(type(value) in (int, float), "Value must be numeric, not boolean")
        check(math.isfinite(value), "Value must be finite")
        if kind == "duration":
            check(value >= 0, "Duration cannot be negative")
    elif kind == "integer":
        check(type(value) is int, "Value must be integer")
    elif kind == "boolean":
        check(type(value) is bool, "Value must be boolean")
    else:
        text(value)
        if kind == "date":
            check(date.fromisoformat(value).isoformat() == value, "Expected ISO civil date")
        elif kind == "time":
            from datetime import time

            parsed = time.fromisoformat(value)
            check(parsed.tzinfo is None, "Time value is local wall time")


@dataclass(frozen=True)
class FieldDefinition:
    id: UUID
    name: str
    value_type: ValueType
    active_from: datetime
    tags: tuple[str, ...] = ()
    unit: str | None = None
    aggregation: str = "none"
    options: tuple[str, ...] = ()
    minimum: float | None = None
    maximum: float | None = None
    temporal_policy: str = "daily"
    weekly_attribution: str = "separate"

    def __post_init__(self) -> None:
        identity(self.id)
        text(self.name, nonempty=True)
        aware(self.active_from)
        check(self.value_type in VALUE_TYPES, "Unsupported value_type")
        object.__setattr__(self, "tags", normalize_tags(self.tags))
        if self.unit is not None:
            text(self.unit, nonempty=True)
        check(self.temporal_policy in ("daily", "weekly"), "Invalid temporal policy")
        check(
            self.weekly_attribution in ("separate", "start", "end", "completion"),
            "Invalid weekly attribution",
        )
        check(
            self.temporal_policy == "weekly" or self.weekly_attribution == "separate",
            "Only weekly fields need attribution",
        )
        check(
            isinstance(self.options, tuple) and all(isinstance(v, str) and v for v in self.options),
            "Options must be text tuple",
        )
        check(len(set(self.options)) == len(self.options), "Duplicate selection options")
        check(
            bool(self.options) == (self.value_type == "selection"),
            "Selection fields require options; other types cannot have options",
        )
        numeric = self.value_type in ("integer", "number", "duration", "rating")
        allowed = ("none", "sum", "mean", "min", "max") if numeric else ("none", "count")
        check(self.aggregation in allowed, "Aggregation incompatible with field type")
        for bound in (self.minimum, self.maximum):
            if bound is not None:
                check(
                    numeric and type(bound) in (int, float) and math.isfinite(bound),
                    "Invalid numeric bound",
                )
        check(
            self.minimum is None or self.maximum is None or self.minimum <= self.maximum,
            "Reversed bounds",
        )

    def validate_value(self, value: Scalar) -> None:
        typed_value(self.value_type, value)
        if self.value_type == "selection":
            check(value in self.options, "Value is not a selection option")
        if self.minimum is not None:
            check(value >= self.minimum, "Value below minimum")
        if self.maximum is not None:
            check(value <= self.maximum, "Value above maximum")


@dataclass(frozen=True)
class Observation:
    id: UUID
    field_id: UUID
    field_label_snapshot: str
    observed_date: date
    recorded_at: datetime
    value: Scalar
    source_period_ref: PeriodRef | None = None
    source_block_id: UUID | None = None
    historical_entry: bool = False
    provenance: str = ""

    def __post_init__(self) -> None:
        identity(self.id)
        identity(self.field_id)
        text(self.field_label_snapshot)
        check(type(self.observed_date) is date, "Observation needs civil date")
        aware(self.recorded_at)
        check(type(self.value) in (str, int, float, bool), "Observation needs a scalar value")
        if type(self.value) is float:
            check(math.isfinite(self.value), "Value must be finite")
        check(
            self.source_period_ref is None or isinstance(self.source_period_ref, PeriodRef),
            "Invalid source period",
        )
        if self.source_block_id is not None:
            identity(self.source_block_id)
        check(type(self.historical_entry) is bool, "historical_entry must be boolean")
        text(self.provenance)
        check(
            not self.historical_entry or bool(self.provenance.strip()),
            "Historical entry requires provenance",
        )

    def validate_field(self, field: FieldDefinition) -> None:
        check(self.field_id == field.id, "Wrong field reference")
        field.validate_value(self.value)
        check(self.recorded_at >= field.active_from, "Recorded before source activation")
        check(
            self.observed_date >= field.active_from.date() or self.historical_entry,
            "Pre-activation entry requires explicit historical provenance",
        )
        if field.temporal_policy == "weekly":
            check(
                self.source_period_ref is not None and self.source_period_ref.scale == "week",
                "Weekly record requires its source week",
            )
            check(
                self.source_period_ref.start <= self.observed_date <= self.source_period_ref.end,
                "Weekly record date must be within its source week",
            )


@dataclass(frozen=True)
class SourceSelection:
    mode: Literal["manual", "by_tags", "all"]
    source_ids: tuple[UUID, ...] = ()
    tags: tuple[str, ...] = ()
    value_types: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        check(self.mode in ("manual", "by_tags", "all"), "Invalid selection mode")
        check(isinstance(self.source_ids, tuple), "Source IDs must be immutable")
        for value in self.source_ids:
            identity(value)
        check(len(set(self.source_ids)) == len(self.source_ids), "Duplicate source IDs")
        object.__setattr__(self, "tags", normalize_tags(self.tags))
        check(
            isinstance(self.value_types, tuple)
            and all(v in (*VALUE_TYPES, "habit", "task") for v in self.value_types),
            "Invalid source types",
        )
        check(len(set(self.value_types)) == len(self.value_types), "Duplicate value types")
        check(
            not self.source_ids or self.mode == "manual",
            "Dynamic selection cannot contain manual IDs",
        )
        check(not self.tags or self.mode == "by_tags", "Tags require by_tags mode")
        check(self.mode != "by_tags" or bool(self.tags), "by_tags needs at least one tag")

    def matches(self, source: FieldDefinition) -> bool:
        return (
            (not self.value_types or source.value_type in self.value_types)
            and (self.mode != "manual" or source.id in self.source_ids)
            and (self.mode != "by_tags" or bool(set(self.tags).intersection(source.tags)))
        )


def field_from_mapping(hw: dict) -> FieldDefinition:
    try:
        validation = hw.get("validation", {})
        check(isinstance(validation, dict), "Validation must be an object")
        check(isinstance(hw.get("options", []), list), "Options must be an array")
        check(isinstance(hw.get("tags", []), list), "Tags must be an array")
        return FieldDefinition(
            UUID(hw["id"]),
            hw["name"],
            hw["value_type"],
            datetime.fromisoformat(hw["active_from"]),
            tuple(hw.get("tags", ())),
            hw.get("unit"),
            hw.get("aggregation", "none"),
            tuple(hw.get("options", ())),
            float(validation["minimum"])
            if isinstance(validation.get("minimum"), (int, float))
            and not isinstance(validation["minimum"], bool)
            else validation.get("minimum"),
            float(validation["maximum"])
            if isinstance(validation.get("maximum"), (int, float))
            and not isinstance(validation["maximum"], bool)
            else validation.get("maximum"),
            hw.get("temporal_policy", "daily"),
            hw.get("weekly_attribution", "separate"),
        )
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise ValueError(f"Invalid metric definition: {error}") from error
