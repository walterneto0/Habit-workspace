"""Standalone imports retain original bytes and never replace existing documents."""

from dataclasses import dataclass, field, replace
from pathlib import Path
from uuid import UUID, uuid4

from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.documents import Document, DocumentError
from habit_workspace.vault.atomic_io import ConflictError, read_bytes, writer_lock
from habit_workspace.vault.format import decode
from habit_workspace.vault.scanner import MissingReference, scan


@dataclass(frozen=True)
class ImportEntry:
    source: Path
    document_id: UUID | None = None
    kind: str | None = None
    schema_version: int | None = None
    destination: Path | None = None
    message: str = ""
    missing_references: tuple[MissingReference, ...] = ()


@dataclass
class ImportResult:
    imported: list[ImportEntry] = field(default_factory=list)
    skipped: list[ImportEntry] = field(default_factory=list)
    conflicting: list[ImportEntry] = field(default_factory=list)
    invalid: list[ImportEntry] = field(default_factory=list)
    index_error: str | None = None


class ImportService:
    def __init__(self, session: VaultSession):
        self.session = session

    def import_files(self, sources: list[Path], *, as_note: bool = False) -> ImportResult:
        result = ImportResult()
        with writer_lock(self.session.root):
            for source in sources:
                source = Path(source).absolute()
                try:
                    if source.suffix.lower() != ".md":
                        raise DocumentError("Only standalone .md imports are supported")
                    raw, revision = read_bytes(source)
                    if as_note and not raw.decode("utf-8-sig").startswith("---"):
                        document = Document.from_metadata(
                            {
                                "hw": {
                                    "schema_version": 4,
                                    "kind": "note",
                                    "id": str(uuid4()),
                                    "title": source.stem,
                                }
                            },
                            raw.decode("utf-8"),
                        )
                    else:
                        document = decode(raw)
                    report = scan(self.session.root)
                    if any(d.layout.id == document.id for d in report.layouts) or any(
                        d.id == document.id for d in report.defaults
                    ):
                        raise ConflictError("Document UUID collides with layout/defaults identity")
                    entries = [d for d in report.documents if d.document.id == document.id]
                    details = dict(
                        source=source,
                        document_id=document.id,
                        kind=document.kind.value,
                        schema_version=document.schema_version,
                    )
                    if entries:
                        if len(entries) == 1 and entries[0].revision.digest == revision.digest:
                            result.skipped.append(
                                ImportEntry(
                                    **details,
                                    destination=entries[0].path,
                                    message="Identical file already present",
                                )
                            )
                        else:
                            result.conflicting.append(
                                ImportEntry(
                                    **details,
                                    message="UUID already exists; compare files explicitly",
                                )
                            )
                        continue
                    loaded = self.session.repository.create(f"Imports/{document.id}.md", document)
                    result.imported.append(
                        ImportEntry(
                            **details,
                            destination=loaded.path,
                            message="Imported without changing identity",
                        )
                    )
                except ConflictError as error:
                    result.conflicting.append(ImportEntry(source, message=str(error)))
                except (DocumentError, OSError, UnicodeError) as error:
                    result.invalid.append(ImportEntry(source, message=str(error)))
            report = self.session.scan()
            # Resolve against the whole batch, so importing a dependency later in
            # the same request doesn't leave a stale missing-reference warning.
            for collection in (result.imported, result.skipped):
                collection[:] = [
                    replace(
                        entry,
                        missing_references=tuple(
                            ref
                            for ref in report.missing_references
                            if ref.source_path == entry.destination
                        ),
                    )
                    for entry in collection
                ]
            result.index_error = self.session.index_error
        return result
