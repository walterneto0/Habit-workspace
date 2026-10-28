"""Worker-callable layout operations; Qt adapters can consume immutable resolutions.

Publication order: definitions -> immutable revision -> page assignment -> cache.
A failed final assignment leaves discoverable unused dependencies, never a dangling
new assignment. Retrying the same IDs/content/activation is idempotent. No rollback
removes user data. All application writers share the existing vault writer lock.
"""

import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.documents import Document, DocumentError
from habit_workspace.domain.layouts import (
    Assignment,
    AssignmentHistory,
    InputConfig,
    LayoutResolution,
    LayoutTemplate,
    TableConfig,
    resolve_layout,
)
from habit_workspace.domain.metrics import FieldDefinition
from habit_workspace.domain.temporal import PeriodRef, PeriodScale
from habit_workspace.vault.atomic_io import (
    ConflictError,
    atomic_write,
    contained_path,
    read_bytes,
    writer_lock,
)
from habit_workspace.vault.layouts import (
    LoadedLayout,
    decode_layout,
    encode_layout,
    json_data,
    layout_references,
)
from habit_workspace.vault.metrics import field_document, field_from_mapping
from habit_workspace.vault.scanner import LoadedDocument, ScanReport, reference_problem, scan


def period_page(report: ScanReport, period: PeriodRef) -> LoadedDocument | None:
    entries = [
        d
        for d in report.documents
        if d.document.kind == f"{period.scale}_page"
        and d.document.metadata["hw"].get(
            "period", "day/" + d.document.metadata["hw"].get("date", "")
        )
        == str(period)
    ]
    if len(entries) > 1 or any(
        d.document.id == c.document_id for d in entries for c in report.conflicts
    ):
        raise ConflictError(f"Ambiguous canonical page for {period}")
    return entries[0] if entries else None


def history(page: LoadedDocument | None) -> AssignmentHistory:
    return (
        AssignmentHistory(
            tuple(
                Assignment.from_mapping(v)
                for v in page.document.metadata["hw"].get("layout_history", [])
            )
        )
        if page
        else AssignmentHistory()
    )


def unique_layout(report: ScanReport, identifier: UUID, version: int) -> LoadedLayout | None:
    if any(c.document_id == identifier for c in report.conflicts):
        raise ConflictError(f"Ambiguous layout identity {identifier}")
    if any(d.document.id == identifier for d in report.documents) or any(
        d.id == identifier for d in report.defaults
    ):
        raise ConflictError("Layout UUID collides with a canonical document")
    matches = [
        d for d in report.layouts if (d.layout.id, d.layout.version) == (identifier, version)
    ]
    if len(matches) > 1:
        raise ConflictError("Duplicate layout revision")
    return matches[0] if matches else None


def binding_issues(layout: LayoutTemplate, report: ScanReport) -> tuple[str, ...]:
    issues = [
        f"{r.role} {r.target_id}: {problem}"
        for r in layout_references(layout)
        if (problem := reference_problem(report, r))
    ]
    fields = {
        d.document.id: field_from_mapping(d.document.metadata["hw"])
        for d in report.documents
        if d.document.kind == "metric_definition"
    }
    for b in layout.walk():
        if b.binding and b.binding.kind == "metric" and b.binding.source_id in fields:
            field = fields[b.binding.source_id]
            if isinstance(b.config, InputConfig):
                accepted = {b.config.value_type}
                if b.config.value_type == "number":
                    accepted.add("integer")
                if field.value_type not in accepted:
                    issues.append(f"Input {b.id} has incompatible field type {field.value_type}")
            if b.type == "checklist" and field.value_type != "boolean":
                issues.append(f"Checklist {b.id} requires a boolean metric")
        if isinstance(b.config, TableConfig):
            for c in b.config.columns:
                if c.field_id in fields and fields[c.field_id].value_type != c.value_type:
                    issues.append(f"Column {c.id} has incompatible field type")
    return tuple(issues)


class LayoutService:
    def __init__(self, session: VaultSession):
        self.session = session

    def load(self, identifier: UUID, version: int) -> LoadedLayout:
        result = unique_layout(self.session.scan(), identifier, version)
        if result is None:
            raise DocumentError(f"Missing layout {identifier} v{version}")
        return result

    def _publish(self, layout: LayoutTemplate, *, raw: bytes | None = None) -> LoadedLayout:
        report = scan(self.session.root)
        existing = unique_layout(report, layout.id, layout.version)
        if existing:
            if (raw is not None and raw != existing.raw) or (
                raw is None and existing.layout != layout
            ):
                raise ConflictError(
                    "Immutable layout revision already exists with different content"
                )
            return existing
        parent = (
            unique_layout(report, layout.id, layout.version - 1) if layout.version > 1 else None
        )
        if raw is None and layout.version > 1 and parent is None:
            raise DocumentError("Creating a revision requires its preceding revision")
        encoded = raw if raw is not None else encode_layout(layout, parent)
        path = contained_path(self.session.root, f"Layouts/{layout.id}.v{layout.version}.json")
        atomic_write(path, encoded)
        data, revision = read_bytes(path)
        return LoadedLayout(path, layout, revision, data)

    def save_template(self, layout: LayoutTemplate) -> LoadedLayout:
        with writer_lock(self.session.root):
            loaded = self._publish(layout)
            self.session.scan()
            return loaded

    def import_template(self, source: Path) -> LoadedLayout:
        if Path(source).suffix.lower() != ".json":
            raise DocumentError("Layout imports require .json")
        raw, _ = read_bytes(Path(source))
        parsed = decode_layout(raw)
        with writer_lock(self.session.root):
            loaded = self._publish(parsed.layout, raw=raw)
            self.session.scan()
            return loaded

    def export_template(self, identifier: UUID, version: int, destination: Path) -> Path:
        """Exact selected revision only. Does not implicitly include personal dependencies."""
        loaded = self.load(identifier, version)
        if Path(destination).suffix.lower() != ".json":
            raise DocumentError("Layout exports require .json")
        atomic_write(Path(destination), loaded.raw)
        return Path(destination)

    def _assign(
        self, period: PeriodRef, assignment: Assignment, expected_page: LoadedDocument | None = None
    ) -> LoadedDocument:
        report = scan(self.session.root)
        layout = unique_layout(report, assignment.layout_id, assignment.version)
        if layout is None:
            raise DocumentError("Cannot assign a missing layout revision")
        page = period_page(report, period)
        if expected_page is not None and (
            page is None
            or page.path != expected_page.path
            or page.revision != expected_page.revision
        ):
            raise ConflictError("Page changed since editing began; reload or compare")
        try:
            updated = history(page).add(assignment)
        except ValueError as error:
            raise ConflictError(str(error)) from error
        if page and updated == history(page):
            return page
        if page:
            document = deepcopy(page.document)
            # Preserve metadata attached to earlier assignments, even if inserted historically.
            originals = {
                Assignment.from_mapping(v).effective_at: v
                for v in document.metadata["hw"].get("layout_history", [])
            }
            document.metadata["hw"]["layout_history"] = [
                originals.get(e.effective_at, e.to_mapping()) for e in updated.entries
            ]
            return self.session.repository.save(page, document)
        document = Document.from_metadata(
            {
                "hw": {
                    "schema_version": 4,
                    "kind": f"{period.scale}_page",
                    "id": str(uuid4()),
                    "period": str(period),
                    "layout_history": [v.to_mapping() for v in updated.entries],
                }
            },
            "",
        )
        return self.session.repository.create(
            f"Pages/{period.scale.title()}s/{document.id}.md", document
        )

    def assign(
        self,
        period: PeriodRef,
        assignment: Assignment,
        *,
        expected_page: LoadedDocument | None = None,
    ) -> LoadedDocument:
        with writer_lock(self.session.root):
            result = self._assign(period, assignment, expected_page)
            self.session.scan()
            return result

    def save_revision(
        self,
        period: PeriodRef,
        layout: LayoutTemplate,
        effective_at: datetime,
        *,
        new_fields: tuple[FieldDefinition, ...] = (),
        expected_page: LoadedDocument | None = None,
        expected_report: ScanReport | None = None,
        original_layout: LoadedLayout | None = None,
    ) -> LoadedDocument:
        assignment = Assignment(layout.id, layout.version, effective_at)
        with writer_lock(self.session.root):
            report = scan(self.session.root)
            page = period_page(report, period)
            if expected_report is not None:
                before = period_page(expected_report, period)
                if (None if page is None else (page.path, page.revision)) != (
                    None if before is None else (before.path, before.revision)
                ):
                    raise ConflictError(
                        "Página alterada; descarte e reabra o Studio para comparar."
                    )
                if {(d.path, d.revision) for d in report.defaults} != {
                    (d.path, d.revision) for d in expected_report.defaults
                }:
                    raise ConflictError("Padrões alterados; reabra o Studio para comparar.")
                for loaded in (*expected_report.layouts, *expected_report.defaults):
                    if read_bytes(loaded.path)[1] != loaded.revision:
                        raise ConflictError(
                            "Layout ou padrão alterado externamente; reabra o Studio."
                        )
            if expected_page and (
                page is None
                or page.path != expected_page.path
                or page.revision != expected_page.revision
            ):
                raise ConflictError("Page changed since editing began")
            try:
                history(page).add(assignment)
            except ValueError as error:
                raise ConflictError(str(error)) from error
            if len({f.id for f in new_fields}) != len(new_fields):
                raise DocumentError("Duplicate new field identity")
            documents = list(report.documents)
            for field in new_fields:
                if field.active_from != effective_at:
                    raise DocumentError("New field activation must match revision activation")
                if not any(r.target_id == field.id for r in layout_references(layout)):
                    raise DocumentError("New field must be referenced by the saved layout")
                existing = [d for d in documents if d.document.id == field.id]
                if (
                    any(c.document_id == field.id for c in report.conflicts)
                    or any(d.layout.id == field.id for d in report.layouts)
                    or any(d.id == field.id for d in report.defaults)
                ):
                    raise ConflictError("Field identity collision")
                if existing:
                    if (
                        len(existing) != 1
                        or existing[0].document.kind != "metric_definition"
                        or field_from_mapping(existing[0].document.metadata["hw"]) != field
                    ):
                        raise ConflictError("Field identity already has different content")
                else:
                    # Validate the whole binding plan before publishing any files.
                    from habit_workspace.vault.atomic_io import Revision

                    documents.append(
                        LoadedDocument(
                            self.session.root / "planned",
                            field_document(field),
                            Revision("", 0, 0, 0, 0),
                        )
                    )
            from dataclasses import replace

            problems = binding_issues(layout, replace(report, documents=tuple(documents)))
            if problems:
                raise DocumentError("; ".join(problems))
            # Check immutable revision collisions before creating any new definitions.
            existing_layout = unique_layout(report, layout.id, layout.version)
            if existing_layout and existing_layout.layout != layout:
                raise ConflictError("Immutable revision content conflict")
            for field in new_fields:
                if not any(d.document.id == field.id for d in report.documents):
                    self.session.repository.create(
                        f"Items/Metrics/{field.id}.md", field_document(field)
                    )
            self._publish(
                layout, raw=encode_layout(layout, original_layout) if original_layout else None
            )
            result = self._assign(period, assignment, expected_page or page)
            self.session.scan()
            return result

    def set_default(self, scale: PeriodScale | str, assignment: Assignment) -> None:
        scale = PeriodScale(scale)
        with writer_lock(self.session.root):
            report = scan(self.session.root)
            if unique_layout(report, assignment.layout_id, assignment.version) is None:
                raise DocumentError("Default references a missing revision")
            if len(report.defaults) > 1:
                raise ConflictError("Multiple default registries")
            loaded = report.defaults[0] if report.defaults else None
            if loaded and any(c.document_id == loaded.id for c in report.conflicts):
                raise ConflictError("Ambiguous defaults identity")
            try:
                updated = (loaded.history(scale) if loaded else AssignmentHistory()).add(assignment)
            except ValueError as error:
                raise ConflictError(str(error)) from error
            value = (
                json_data(loaded.raw)
                if loaded
                else {
                    "schema_version": 4,
                    "kind": "layout_defaults",
                    "id": str(uuid4()),
                    "histories": {},
                }
            )
            originals = {
                Assignment.from_mapping(e).effective_at: e
                for e in value["histories"].get(scale.value, [])
            }
            value["histories"][scale.value] = [
                originals.get(e.effective_at, e.to_mapping()) for e in updated.entries
            ]
            path = contained_path(
                self.session.root,
                loaded.path.relative_to(self.session.root) if loaded else "Templates/defaults.json",
            )
            raw = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
            from habit_workspace.vault.atomic_io import Revision
            from habit_workspace.vault.layouts import decode_defaults

            decode_defaults(path, raw, Revision("", 0, 0, 0, 0))
            if not loaded or raw != loaded.raw:
                atomic_write(
                    path,
                    raw,
                    expected=loaded.revision if loaded else None,
                    backup_directory=contained_path(
                        self.session.root, ".habit-workspace/backups", internal=True
                    ),
                )
            self.session.scan()

    def resolve(self, period: PeriodRef, instant: datetime) -> LayoutResolution:
        return self.resolve_report(self.session.scan(), period, instant)

    @staticmethod
    def resolve_report(
        report: ScanReport, period: PeriodRef, instant: datetime
    ) -> LayoutResolution:
        from dataclasses import replace

        page = period_page(report, period)
        if len(report.defaults) > 1:
            raise ConflictError("Multiple default registries")
        defaults = (
            report.defaults[0].history(period.scale) if report.defaults else AssignmentHistory()
        )
        if report.defaults and any(
            c.document_id == report.defaults[0].id for c in report.conflicts
        ):
            raise ConflictError("Ambiguous defaults identity")
        for h in (history(page), defaults):
            active = h.at(instant)
            if active:
                unique_layout(report, active.layout_id, active.version)
        resolved = resolve_layout(
            period, instant, history(page), defaults, tuple(d.layout for d in report.layouts)
        )
        issues = resolved.issues + binding_issues(resolved.layout, report)
        issues += tuple(f"{i.path}: {i.message}" for i in report.invalid)
        return replace(resolved, issues=issues)
