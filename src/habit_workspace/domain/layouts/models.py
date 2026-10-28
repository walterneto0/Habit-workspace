"""Immutable layout revisions, temporal histories and deterministic resolution."""

from dataclasses import dataclass, replace
from datetime import datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from habit_workspace.domain.layouts.components import (
    Component,
    NoteConfig,
    Placement,
    flow,
    validate_grid,
)
from habit_workspace.domain.metrics import aware, check, identity, text
from habit_workspace.domain.temporal import PeriodRef, PeriodScale


@dataclass(frozen=True)
class Grid:
    columns: int = 1
    gap: int = 16

    def __post_init__(self) -> None:
        check(type(self.columns) is int and self.columns in (1, 2), "Grid needs one or two columns")
        check(
            type(self.gap) is int and self.gap in (4, 8, 12, 16, 24, 32),
            "Unsupported spacing token",
        )


@dataclass(frozen=True)
class LayoutTemplate:
    id: UUID
    version: int
    name: str
    blocks: tuple[Component, ...] = ()
    description: str = ""
    grid: Grid = Grid()
    schema_version: int = 4

    def __post_init__(self) -> None:
        identity(self.id)
        check(type(self.version) is int and self.version > 0, "Revision must be positive integer")
        text(self.name, nonempty=True)
        text(self.description)
        check(
            type(self.schema_version) is int and self.schema_version == 4,
            "Unsupported layout schema version",
        )
        check(isinstance(self.grid, Grid), "Layout needs typed grid")
        validate_grid(self.blocks, self.grid.columns)

    def positions(self) -> tuple[Placement, ...]:
        return validate_grid(self.blocks, self.grid.columns)

    def walk(self):
        for block in self.blocks:
            yield from block.walk()

    def new_revision(self, **changes) -> LayoutTemplate:
        check(
            not {"id", "version", "schema_version"}.intersection(changes),
            "Revision identity is controlled",
        )
        return replace(self, version=self.version + 1, **changes)

    def duplicate(self, identifier: UUID, name: str) -> LayoutTemplate:
        """Independent template identity; bindings and content IDs intentionally survive."""
        check(identifier != self.id, "Duplicate needs a new identity")
        return replace(self, id=identifier, version=1, name=name)

    def insert(self, index: int, block: Component) -> LayoutTemplate:
        check(type(index) is int and 0 <= index <= len(self.blocks), "Invalid insertion index")
        return replace(self, blocks=flow(self.blocks[:index] + (block,) + self.blocks[index:]))

    def remove(self, identifier: UUID) -> LayoutTemplate:
        check(any(b.id == identifier for b in self.blocks), "Component not found")
        return replace(self, blocks=flow(tuple(b for b in self.blocks if b.id != identifier)))

    def move(self, identifier: UUID, index: int) -> LayoutTemplate:
        check(type(index) is int and 0 <= index < len(self.blocks), "Invalid destination index")
        block = next((b for b in self.blocks if b.id == identifier), None)
        check(block is not None, "Component not found")
        return self.remove(identifier).insert(index, block)


@dataclass(frozen=True)
class Assignment:
    layout_id: UUID
    version: int
    effective_at: datetime

    def __post_init__(self) -> None:
        identity(self.layout_id)
        check(type(self.version) is int and self.version > 0, "Invalid assignment revision")
        aware(self.effective_at)

    def to_mapping(self) -> dict:
        return {
            "layout_id": str(self.layout_id),
            "version": self.version,
            "effective_at": self.effective_at.isoformat(),
        }

    @classmethod
    def from_mapping(cls, value: dict) -> Assignment:
        return cls(
            UUID(value["layout_id"]),
            value["version"],
            datetime.fromisoformat(value["effective_at"]),
        )


@dataclass(frozen=True)
class AssignmentHistory:
    entries: tuple[Assignment, ...] = ()

    def __post_init__(self) -> None:
        check(
            isinstance(self.entries, tuple)
            and all(isinstance(e, Assignment) for e in self.entries),
            "Invalid assignment history",
        )
        check(
            all(
                a.effective_at < b.effective_at
                for a, b in zip(self.entries, self.entries[1:], strict=False)
            ),
            "Assignment times must strictly increase; collision or overlap",
        )

    def at(self, instant: datetime) -> Assignment | None:
        aware(instant)
        return next((e for e in reversed(self.entries) if e.effective_at <= instant), None)

    def add(self, entry: Assignment) -> AssignmentHistory:
        same = next((e for e in self.entries if e.effective_at == entry.effective_at), None)
        check(same is None or same == entry, "Assignment activation collision")
        return (
            self
            if same
            else AssignmentHistory(
                tuple(sorted((*self.entries, entry), key=lambda e: e.effective_at))
            )
        )


@dataclass(frozen=True)
class LayoutResolution:
    period: PeriodRef
    instant: datetime
    layout: LayoutTemplate
    origin: str
    assignment: Assignment | None
    issues: tuple[str, ...] = ()


def builtin(scale: PeriodScale | str) -> LayoutTemplate:
    scale = PeriodScale(scale)
    identifier = uuid5(NAMESPACE_URL, f"habit-workspace:builtin:{scale}:v4")
    block_id = uuid5(identifier, "notes")
    return LayoutTemplate(
        identifier,
        1,
        f"{scale.title()} — basic",
        (Component(block_id, "note", "Notes", NoteConfig()),),
    )


def resolve_layout(
    period: PeriodRef,
    instant: datetime,
    explicit: AssignmentHistory,
    default: AssignmentHistory,
    templates: tuple[LayoutTemplate, ...],
) -> LayoutResolution:
    """Missing active dependencies are disclosed; never resurrect an older assignment."""
    aware(instant)
    issues = []
    for origin, history in (("explicit", explicit), ("default", default)):
        assignment = history.at(instant)
        if assignment is None:
            continue
        matches = [
            t for t in templates if (t.id, t.version) == (assignment.layout_id, assignment.version)
        ]
        check(len(matches) <= 1, "Ambiguous layout revision")
        if matches:
            return LayoutResolution(period, instant, matches[0], origin, assignment, tuple(issues))
        issues.append(f"Missing {origin} layout {assignment.layout_id} v{assignment.version}")
    return LayoutResolution(period, instant, builtin(period.scale), "builtin", None, tuple(issues))
