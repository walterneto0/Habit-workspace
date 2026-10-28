"""Discover supported Markdown anywhere in the vault; never choose a duplicate winner."""

import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from habit_workspace.domain.documents import Document, DocumentError
from habit_workspace.vault.atomic_io import Revision, contained_path, read_bytes
from habit_workspace.vault.format import decode


@dataclass(frozen=True)
class LoadedDocument:
    path: Path
    document: Document
    revision: Revision


@dataclass(frozen=True)
class FileIssue:
    path: Path
    message: str


@dataclass(frozen=True)
class DuplicateIdentity:
    document_id: UUID
    paths: tuple[Path, ...]
    identical: bool


@dataclass(frozen=True)
class MissingReference:
    source_id: UUID
    source_path: Path
    target_id: UUID
    role: str
    reason: str
    version: int | None = None


@dataclass(frozen=True)
class ScanReport:
    documents: tuple[LoadedDocument, ...]
    invalid: tuple[FileIssue, ...]
    conflicts: tuple[DuplicateIdentity, ...]
    missing_references: tuple[MissingReference, ...]
    directories: tuple[Path, ...]


def scan(root: Path) -> ScanReport:
    documents, invalid, directories = [], [], []
    by_id = defaultdict(list)

    def walk_error(error: OSError) -> None:
        invalid.append(FileIssue(Path(error.filename or root), str(error)))

    for current, subdirs, filenames in os.walk(root, followlinks=False, onerror=walk_error):
        directory = Path(current)
        directories.append(directory)
        subdirs.sort()
        for name in subdirs[:]:
            if directory == root and name == ".habit-workspace":
                subdirs.remove(name)
            elif (directory / name).is_symlink():
                subdirs.remove(name)
                invalid.append(FileIssue(directory / name, "Symbolic-link directory skipped"))
        for name in sorted(filenames):
            path = directory / name
            if path.suffix.lower() != ".md":
                continue
            try:
                contained_path(root, path.relative_to(root))
                raw, revision = read_bytes(path)
                loaded = LoadedDocument(path, decode(raw), revision)
                documents.append(loaded)
                by_id[loaded.document.id].append(loaded)
            except (DocumentError, OSError) as error:
                invalid.append(FileIssue(path, str(error)))
    conflicts = tuple(
        DuplicateIdentity(
            identifier,
            tuple(d.path for d in entries),
            len({d.revision.digest for d in entries}) == 1,
        )
        for identifier, entries in by_id.items()
        if len(entries) > 1
    )
    missing = []
    for loaded in documents:
        for reference in loaded.document.references():
            targets = by_id.get(reference.target_id, [])
            reason = None
            if reference.role in ("layout_id", "field_id"):
                reason = "Dependency type unavailable in Phase 1"
            elif not targets:
                reason = "Referenced document is missing or invalid"
            elif len(targets) > 1:
                reason = "Referenced UUID is ambiguous"
            elif reference.role == "habit_id" and targets[0].document.kind != "habit":
                reason = "Referenced document is not a habit"
            if reason:
                missing.append(
                    MissingReference(
                        loaded.document.id,
                        loaded.path,
                        reference.target_id,
                        reference.role,
                        reason,
                        reference.version,
                    )
                )
    return ScanReport(
        tuple(documents), tuple(invalid), conflicts, tuple(missing), tuple(directories)
    )
