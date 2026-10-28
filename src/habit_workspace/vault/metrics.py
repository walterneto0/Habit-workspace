"""Metric/observation adapters over canonical Markdown metadata."""

from dataclasses import asdict
from datetime import date, datetime
from uuid import UUID

from habit_workspace.domain.documents import Document, DocumentError
from habit_workspace.domain.metrics import FieldDefinition, Observation
from habit_workspace.domain.metrics import field_from_mapping as field_from_mapping
from habit_workspace.domain.temporal import PeriodRef


def field_document(field: FieldDefinition, *, body: str = "") -> Document:
    hw = asdict(field)
    hw.update(
        schema_version=4,
        kind="metric_definition",
        id=str(field.id),
        active_from=field.active_from.isoformat(),
    )
    hw["tags"], hw["options"] = list(field.tags), list(field.options)
    hw["validation"] = {"minimum": hw.pop("minimum"), "maximum": hw.pop("maximum")}
    return Document.from_metadata({"hw": hw}, body)


def observation_from_mapping(value: dict) -> Observation:
    try:
        return Observation(
            UUID(value["id"]),
            UUID(value["field_id"]),
            value["field_label_snapshot"],
            date.fromisoformat(value["observed_date"]),
            datetime.fromisoformat(value["recorded_at"]),
            value["value"],
            PeriodRef(value["source_period_ref"]) if value.get("source_period_ref") else None,
            UUID(value["source_block_id"]) if value.get("source_block_id") else None,
            value.get("historical_entry", False),
            value.get("provenance", ""),
        )
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise DocumentError(f"Invalid observation: {error}") from error


def observation_mapping(record: Observation) -> dict:
    result = asdict(record)
    result.update(
        id=str(record.id),
        field_id=str(record.field_id),
        observed_date=record.observed_date.isoformat(),
        recorded_at=record.recorded_at.isoformat(),
    )
    result["source_period_ref"] = (
        str(record.source_period_ref) if record.source_period_ref else None
    )
    result["source_block_id"] = str(record.source_block_id) if record.source_block_id else None
    return {k: v for k, v in result.items() if v is not None}
