"""Finite declarative component registry. Nothing in a vault can register executable code."""

from dataclasses import dataclass, replace
from pathlib import PurePosixPath
from typing import Literal
from uuid import UUID

from habit_workspace.domain.metrics import VALUE_TYPES, SourceSelection, check, identity, text
from habit_workspace.domain.temporal import PeriodRef


@dataclass(frozen=True)
class Binding:
    source_id: UUID
    kind: Literal["metric", "habit", "note", "task"]

    def __post_init__(self) -> None:
        identity(self.source_id)
        check(self.kind in ("metric", "habit", "note", "task"), "Unsupported binding kind")


@dataclass(frozen=True)
class Placement:
    width: int = 1
    row: int | None = None
    column: int | None = None

    def __post_init__(self) -> None:
        check(type(self.width) is int and self.width in (1, 2), "Width must be one or two columns")
        check(
            (self.row is None) == (self.column is None), "Row and column must be supplied together"
        )
        if self.row is not None:
            check(type(self.row) is int and 0 <= self.row <= 10000, "Invalid grid row")
            check(type(self.column) is int and self.column in (0, 1), "Invalid grid column")


@dataclass(frozen=True)
class ChecklistConfig:
    selection: SourceSelection | None = None

    def __post_init__(self) -> None:
        check(
            self.selection is None or isinstance(self.selection, SourceSelection),
            "Invalid checklist query",
        )
        if self.selection is not None:
            check(
                bool(self.selection.value_types)
                and set(self.selection.value_types) <= {"boolean", "habit", "task"},
                "Checklist sources must be boolean metrics or habits",
            )


@dataclass(frozen=True)
class ListConfig:
    selection: SourceSelection | None = None
    ordered: bool = False

    def __post_init__(self) -> None:
        check(
            self.selection is None or isinstance(self.selection, SourceSelection),
            "Invalid list query",
        )
        check(type(self.ordered) is bool, "ordered must be boolean")


@dataclass(frozen=True)
class TableColumn:
    id: UUID
    label: str
    value_type: str
    field_id: UUID

    def __post_init__(self) -> None:
        identity(self.id)
        identity(self.field_id)
        text(self.label)
        check(self.value_type in VALUE_TYPES, "Invalid column type")


@dataclass(frozen=True)
class TableConfig:
    columns: tuple[TableColumn, ...] = ()

    def __post_init__(self) -> None:
        check(
            isinstance(self.columns, tuple)
            and all(isinstance(c, TableColumn) for c in self.columns),
            "Invalid columns",
        )
        check(len({c.id for c in self.columns}) == len(self.columns), "Duplicate column ID")


@dataclass(frozen=True)
class ChartConfig:
    selection: SourceSelection
    period: PeriodRef | None = None
    follow_page_period: bool = True
    aggregation: str = "count"
    visualization: str = "bar"

    def __post_init__(self) -> None:
        check(
            isinstance(self.selection, SourceSelection), "Chart needs structured source selection"
        )
        check("task" not in self.selection.value_types, "Tasks cannot feed charts")
        check(
            self.selection.mode in ("manual", "by_tags"),
            "Charts require fixed IDs or dynamic tags",
        )
        check(type(self.follow_page_period) is bool, "Invalid follow_page_period")
        check(
            (self.period is None) == self.follow_page_period,
            "Choose a concrete chart period or follow page",
        )
        check(
            self.period is None
            or (isinstance(self.period, PeriodRef) and self.period.scale != "day"),
            "Chart period must be year/month/week",
        )
        check(
            self.aggregation in ("count", "sum", "mean", "min", "max", "states"),
            "Unsupported aggregation",
        )
        check(self.visualization in ("bar", "line", "total"), "Unsupported chart visualization")
        if self.aggregation in ("sum", "mean", "min", "max"):
            check(
                bool(self.selection.value_types)
                and set(self.selection.value_types) <= {"integer", "number", "duration", "rating"},
                "Numeric charts require explicit numeric source types",
            )


@dataclass(frozen=True)
class NoteConfig:
    content_id: UUID | None = None

    def __post_init__(self) -> None:
        if self.content_id is not None:
            identity(self.content_id)


@dataclass(frozen=True)
class ImageConfig:
    path: str
    alt: str = ""
    fit: str = "contain"

    def __post_init__(self) -> None:
        text(self.path, nonempty=True)
        text(self.alt)
        path = PurePosixPath(self.path)
        check(
            not path.is_absolute()
            and not {"..", ".habit-workspace"}.intersection(path.parts)
            and ":" not in self.path
            and "\\" not in self.path
            and "\x00" not in self.path,
            "Image must be a contained local path",
        )
        check(
            path.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".gif"),
            "Unsupported image extension",
        )
        check(self.fit in ("contain", "cover"), "Invalid image fit")


@dataclass(frozen=True)
class InputConfig:
    value_type: str
    required: bool = False
    placeholder: str = ""

    def __post_init__(self) -> None:
        check(self.value_type in VALUE_TYPES, "Invalid input type")
        check(type(self.required) is bool, "required must be boolean")
        text(self.placeholder)


@dataclass(frozen=True)
class SectionConfig:
    children: tuple[Component, ...] = ()
    columns: int = 1

    def __post_init__(self) -> None:
        check(type(self.columns) is int and self.columns in (1, 2), "Invalid section columns")
        validate_grid(self.children, self.columns)


type Configuration = (
    ChecklistConfig
    | ListConfig
    | TableConfig
    | ChartConfig
    | NoteConfig
    | ImageConfig
    | InputConfig
    | SectionConfig
)


@dataclass(frozen=True)
class ComponentDefinition:
    kind: str
    config_type: type
    bindings: tuple[str, ...] = ()


class ComponentRegistry:
    def __init__(self, definitions: tuple[ComponentDefinition, ...]):
        self._definitions = {d.kind: d for d in definitions}
        check(len(self._definitions) == len(definitions), "Duplicate component registration")

    @property
    def kinds(self) -> tuple[str, ...]:
        return tuple(self._definitions)

    def get(self, kind: str) -> ComponentDefinition:
        check(
            isinstance(kind, str) and kind in self._definitions,
            f"Unsupported component type: {kind}",
        )
        return self._definitions[kind]


REGISTRY = ComponentRegistry(
    (
        ComponentDefinition("checklist", ChecklistConfig, ("habit", "metric", "task")),
        ComponentDefinition("list", ListConfig, ("metric", "habit", "task")),
        ComponentDefinition("table", TableConfig),
        ComponentDefinition("chart", ChartConfig),
        ComponentDefinition("note", NoteConfig, ("note",)),
        ComponentDefinition("image", ImageConfig),
        ComponentDefinition("section", SectionConfig),
        *(ComponentDefinition(f"{t}_input", InputConfig, ("metric",)) for t in VALUE_TYPES),
    )
)


@dataclass(frozen=True)
class Component:
    id: UUID
    type: str
    title: str
    config: Configuration
    placement: Placement = Placement()
    binding: Binding | None = None

    def __post_init__(self) -> None:
        identity(self.id)
        text(self.title)
        definition = REGISTRY.get(self.type)
        check(
            type(self.config) is definition.config_type,
            "Component configuration does not match type",
        )
        check(isinstance(self.placement, Placement), "Invalid placement")
        if self.binding is not None:
            check(
                isinstance(self.binding, Binding) and self.binding.kind in definition.bindings,
                "Unsupported binding for component",
            )
        if isinstance(self.config, InputConfig):
            check(self.type == f"{self.config.value_type}_input", "Input kind/type mismatch")
            check(self.binding is not None, "Inputs must bind a separately defined metric")
        if isinstance(self.config, (ChecklistConfig, ListConfig)):
            check(
                self.binding is None or self.config.selection is None,
                "Choose binding or source query",
            )

    def walk(self):
        yield self
        if isinstance(self.config, SectionConfig):
            for child in self.config.children:
                yield from child.walk()


def validate_grid(blocks: tuple[Component, ...], columns: int) -> tuple[Placement, ...]:
    check(
        isinstance(blocks, tuple) and all(isinstance(b, Component) for b in blocks),
        "Components must be an immutable tuple",
    )
    check(len(blocks) <= 1000, "Too many components")
    identifiers = [b.id for root in blocks for b in root.walk()]
    check(len(identifiers) == len(set(identifiers)), "Duplicate component ID in visual tree")
    occupied = set()
    result = []
    cursor = 0
    for block in blocks:
        p = block.placement
        check(p.width <= columns, "Component exceeds grid columns")
        if p.row is None:
            while True:
                row, column = divmod(cursor, columns)
                cells = {(row, c) for c in range(column, column + p.width)}
                if column + p.width <= columns and not cells.intersection(occupied):
                    break
                cursor += 1
        else:
            row, column = p.row, p.column
            check(column + p.width <= columns, "Grid position exceeds columns")
            cells = {(row, c) for c in range(column, column + p.width)}
            check(not cells.intersection(occupied), "Grid position collision")
        occupied.update(cells)
        cursor = max(cursor, row * columns + column + p.width)
        result.append(Placement(p.width, row, column))
    return tuple(result)


def flow(blocks: tuple[Component, ...]) -> tuple[Component, ...]:
    """Editor order changes deliberately reflow explicit positions; identities survive."""
    return tuple(replace(b, placement=Placement(b.placement.width)) for b in blocks)
