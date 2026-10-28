"""Bounded inert layout JSON. Unsupported files remain untouched and report errors.

Loaded bytes are retained for exact export/no-op round trips. Unknown metadata
is retained in new revisions by overlaying known fields onto the prior tree.
"""

import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from habit_workspace.domain.documents import DocumentError, Reference, validate_tree
from habit_workspace.domain.layouts import (
    REGISTRY,
    AssignmentHistory,
    Binding,
    ChartConfig,
    ChecklistConfig,
    Component,
    Grid,
    ImageConfig,
    InputConfig,
    LayoutTemplate,
    ListConfig,
    NoteConfig,
    Placement,
    SectionConfig,
    TableColumn,
    TableConfig,
)
from habit_workspace.domain.layouts.models import Assignment
from habit_workspace.domain.metrics import SourceSelection, check
from habit_workspace.domain.temporal import PeriodRef, PeriodScale
from habit_workspace.vault.atomic_io import Revision
from habit_workspace.vault.format import MAX_DOCUMENT_BYTES


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        check(key not in result, f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def json_data(raw: bytes) -> dict:
    try:
        check(len(raw) <= MAX_DOCUMENT_BYTES, "JSON exceeds size limit")
        value = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_pairs)
        validate_tree(value)
        check(isinstance(value, dict), "Expected JSON object")
        check(
            type(value.get("schema_version")) is int and value["schema_version"] == 4,
            "Unsupported layout schema_version",
        )
        return value
    except (ValueError, TypeError, UnicodeError, RecursionError) as error:
        raise DocumentError(f"Invalid layout JSON: {error}") from error


def selection_mapping(value: SourceSelection) -> dict:
    return {
        "mode": value.mode,
        "source_ids": [str(v) for v in value.source_ids],
        "tags": list(value.tags),
        "value_types": list(value.value_types),
    }


def selection_from_mapping(value: dict) -> SourceSelection:
    check(isinstance(value, dict), "Source selection must be object")
    for key in ("source_ids", "tags", "value_types"):
        check(isinstance(value.get(key, []), list), f"{key} must be array")
    # Documented schema-v4 illustrative checklist shorthand.
    mode = value["mode"]
    return SourceSelection(
        "by_tags" if mode == "habits_by_tags" else mode,
        tuple(UUID(v) for v in value.get("source_ids", [])),
        tuple(value.get("tags", [])),
        ("habit",) if mode == "habits_by_tags" else tuple(value.get("value_types", [])),
    )


def component_mapping(block: Component) -> dict:
    c = block.config
    config = {}
    if isinstance(c, (ChecklistConfig, ListConfig)):
        if c.selection:
            config["selection"] = selection_mapping(c.selection)
        if isinstance(c, ListConfig):
            config["ordered"] = c.ordered
    elif isinstance(c, TableConfig):
        config["columns"] = [
            {
                "id": str(v.id),
                "label": v.label,
                "value_type": v.value_type,
                "field_id": str(v.field_id),
            }
            for v in c.columns
        ]
    elif isinstance(c, ChartConfig):
        config = {
            "selection": selection_mapping(c.selection),
            "period": str(c.period) if c.period else None,
            "follow_page_period": c.follow_page_period,
            "aggregation": c.aggregation,
            "visualization": c.visualization,
        }
    elif isinstance(c, NoteConfig):
        if c.content_id:
            config["content_id"] = str(c.content_id)
    elif isinstance(c, ImageConfig):
        config = {"path": c.path, "alt": c.alt, "fit": c.fit}
    elif isinstance(c, InputConfig):
        config = {"value_type": c.value_type, "required": c.required, "placeholder": c.placeholder}
    elif isinstance(c, SectionConfig):
        config = {"columns": c.columns, "children": [component_mapping(v) for v in c.children]}
    value = {
        "id": str(block.id),
        "type": block.type,
        "title": block.title,
        "width": block.placement.width,
        "config": config,
    }
    if block.placement.row is not None:
        value["position"] = {"row": block.placement.row, "column": block.placement.column}
    if block.binding:
        value["binding"] = {"kind": block.binding.kind, "source_id": str(block.binding.source_id)}
    return value


def component_from_mapping(value: dict) -> Component:
    check(isinstance(value, dict), "Block must be object")
    check(
        not {"checkins", "observations"}.intersection(value), "Records cannot belong to components"
    )
    kind = value["type"]
    REGISTRY.get(kind)  # Unknown components fail closed; their original file is preserved.
    config = value.get("config", {})
    check(isinstance(config, dict), "Component config must be object")
    check(
        not {"checkins", "observations"}.intersection(config),
        "Records cannot belong to component config",
    )
    binding = value.get("binding")
    if "field_id" in value:
        check(binding is None, "Multiple component bindings")
        binding = {"kind": "metric", "source_id": value["field_id"]}
    bound = Binding(UUID(binding["source_id"]), binding["kind"]) if binding is not None else None
    selection = config.get("selection", value.get("source"))
    query = selection_from_mapping(selection) if selection is not None else None
    match kind:
        case "checklist":
            typed = ChecklistConfig(query)
        case "list":
            typed = ListConfig(query, config.get("ordered", False))
        case "table":
            columns = config.get("columns", [])
            check(isinstance(columns, list), "Columns must be array")
            typed = TableConfig(
                tuple(
                    TableColumn(UUID(c["id"]), c["label"], c["value_type"], UUID(c["field_id"]))
                    for c in columns
                )
            )
        case "chart":
            typed = ChartConfig(
                query,
                PeriodRef(config["period"]) if config.get("period") else None,
                config.get("follow_page_period", True),
                config.get("aggregation", "count"),
                config.get("visualization", "bar"),
            )
        case "note":
            typed = NoteConfig(UUID(config["content_id"]) if config.get("content_id") else None)
        case "image":
            typed = ImageConfig(config["path"], config.get("alt", ""), config.get("fit", "contain"))
        case "section":
            children = config.get("children", [])
            check(isinstance(children, list), "Children must be array")
            typed = SectionConfig(
                tuple(component_from_mapping(v) for v in children), config.get("columns", 1)
            )
        case _:
            typed = InputConfig(
                config.get("value_type", kind.removesuffix("_input")),
                config.get("required", False),
                config.get("placeholder", ""),
            )
    position = value.get("position", {})
    check(isinstance(position, dict), "Position must be object")
    return Component(
        UUID(value["id"]),
        kind,
        value.get("title", ""),
        typed,
        Placement(value.get("width", 1), position.get("row"), position.get("column")),
        bound,
    )


@dataclass(frozen=True)
class ParsedLayout:
    layout: LayoutTemplate
    raw: bytes


@dataclass(frozen=True)
class LoadedLayout:
    path: Path
    layout: LayoutTemplate
    revision: Revision
    raw: bytes

    def references(self) -> tuple[Reference, ...]:
        return layout_references(self.layout)


def layout_references(layout: LayoutTemplate) -> tuple[Reference, ...]:
    refs = []
    for block in layout.walk():
        if block.binding:
            role = {"metric": "field_id", "habit": "habit_id", "note": "note_id"}[
                block.binding.kind
            ]
            refs.append(Reference(block.binding.source_id, role))
        if isinstance(block.config, TableConfig):
            refs.extend(Reference(c.field_id, "field_id") for c in block.config.columns)
        selection = getattr(block.config, "selection", None)
        if selection:
            refs.extend(Reference(v, "source_id") for v in selection.source_ids)
    return tuple(dict.fromkeys(refs))


def decode_layout(raw: bytes) -> ParsedLayout:
    value = json_data(raw)
    try:
        check(value.get("kind") == "layout_template", "Unsupported JSON kind")
        check(
            not {"checkins", "observations"}.intersection(value),
            "Canonical records cannot belong to layouts",
        )
        grid = value.get("grid", {})
        check(
            isinstance(grid, dict) and isinstance(value.get("blocks"), list), "Invalid grid/blocks"
        )
        layout = LayoutTemplate(
            UUID(value["id"]),
            value["version"],
            value["name"],
            tuple(component_from_mapping(v) for v in value["blocks"]),
            value.get("description", ""),
            Grid(grid.get("columns", 1), grid.get("gap", 16)),
        )
        return ParsedLayout(layout, raw)
    except (KeyError, ValueError, TypeError, AttributeError, RecursionError) as error:
        raise DocumentError(f"Invalid layout: {error}") from error


def _overlay(old: dict, new: dict) -> dict:
    result = deepcopy(old)
    for key, value in new.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _overlay(result[key], value)
        else:
            result[key] = value
    return result


def _merge_block(block: Component, old: dict) -> dict:
    new = component_mapping(block)
    for key in ("position", "binding", "field_id", "source"):
        if key not in new:
            old.pop(key, None)
    # A type change cannot retain old known config semantics.
    if old.get("type") != block.type:
        old.pop("config", None)
    result = _overlay(old, new)
    for key in ("selection", "content_id"):
        if key not in new["config"]:
            result["config"].pop(key, None)
    if isinstance(block.config, TableConfig):
        prior_columns = {c["id"]: c for c in old.get("config", {}).get("columns", [])}
        result["config"]["columns"] = [
            _overlay(prior_columns.get(c["id"], {}), c) for c in new["config"]["columns"]
        ]
    if isinstance(block.config, SectionConfig):
        prior = {c["id"]: c for c in old.get("config", {}).get("children", [])}
        result["config"]["children"] = [
            _merge_block(c, deepcopy(prior.get(str(c.id), {}))) for c in block.config.children
        ]
    return result


def encode_layout(
    layout: LayoutTemplate, original: ParsedLayout | LoadedLayout | None = None
) -> bytes:
    if original is not None and layout == original.layout:
        return original.raw
    old = json_data(original.raw) if original else {}
    previous = {b["id"]: b for b in old.get("blocks", [])}
    value = _overlay(
        old,
        {
            "schema_version": 4,
            "kind": "layout_template",
            "id": str(layout.id),
            "version": layout.version,
            "name": layout.name,
            "description": layout.description,
            "grid": {"columns": layout.grid.columns, "gap": layout.grid.gap},
        },
    )
    value["blocks"] = [
        _merge_block(b, deepcopy(previous.get(str(b.id), {}))) for b in layout.blocks
    ]
    raw = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    decode_layout(raw)
    return raw


@dataclass(frozen=True)
class LoadedDefaults:
    path: Path
    id: UUID
    histories: tuple[tuple[PeriodScale, AssignmentHistory], ...]
    revision: Revision
    raw: bytes

    def history(self, scale: PeriodScale) -> AssignmentHistory:
        return dict(self.histories).get(scale, AssignmentHistory())

    def references(self) -> tuple[Reference, ...]:
        return tuple(
            Reference(e.layout_id, "layout_id", e.version)
            for _, h in self.histories
            for e in h.entries
        )


def decode_defaults(path: Path, raw: bytes, revision: Revision) -> LoadedDefaults:
    value = json_data(raw)
    try:
        check(value.get("kind") == "layout_defaults", "Invalid defaults kind")
        check(isinstance(value["histories"], dict), "Defaults histories must be object")
        histories = []
        for scale, entries in value["histories"].items():
            check(isinstance(entries, list), "Defaults history must be array")
            histories.append(
                (
                    PeriodScale(scale),
                    AssignmentHistory(tuple(Assignment.from_mapping(v) for v in entries)),
                )
            )
        return LoadedDefaults(path, UUID(value["id"]), tuple(histories), revision, raw)
    except (KeyError, ValueError, TypeError, AttributeError) as error:
        raise DocumentError(f"Invalid defaults: {error}") from error
