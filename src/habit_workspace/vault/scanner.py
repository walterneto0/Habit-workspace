"""Discover supported Markdown anywhere in the vault; never choose a duplicate winner."""

import os
import threading
from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from habit_workspace.domain.documents import Document, DocumentError
from habit_workspace.vault.atomic_io import Revision, contained_path, read_bytes
from habit_workspace.vault.format import decode
from habit_workspace.vault.layouts import (
    LoadedDefaults,
    LoadedLayout,
    decode_defaults,
    decode_layout,
    json_data,
)


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
    layouts: tuple[LoadedLayout, ...] = ()
    defaults: tuple[LoadedDefaults, ...] = ()


class _ParsedCache:
    """Reuse parsed documents for byte-identical files between scans.

    Every scan still reads and hashes every file, so change detection is unchanged;
    only the YAML parse of unchanged bytes is skipped. Entries are keyed by SHA-256
    and verified against the exact bytes. Documents in a report are read-only by
    contract (writers deep-copy first); a cached document whose metadata or body was
    mutated anyway no longer equals its parse signature and is parsed again.
    """

    def __init__(self, limit_bytes: int = 64 * 1024 * 1024):
        self.limit = limit_bytes
        self.size = 0
        self.entries: OrderedDict[str, Document] = OrderedDict()
        self.lock = threading.Lock()

    def decode(self, raw: bytes, digest: str) -> Document:
        with self.lock:
            cached = self.entries.get(digest)
            if cached is not None:
                self.entries.move_to_end(digest)
        if (
            cached is not None
            and cached.original_bytes == raw
            and (cached.metadata, cached.body) == cached.original_signature
        ):
            return cached
        document = decode(raw)
        with self.lock:
            if digest in self.entries:
                self.size -= len(self.entries.pop(digest).original_bytes)
            self.entries[digest] = document
            self.size += len(raw)
            while self.size > self.limit and self.entries:
                self.size -= len(self.entries.popitem(last=False)[1].original_bytes)
        return document


PARSED = _ParsedCache()


def fingerprint(report: ScanReport) -> tuple:
    """Everything the index and the UI derive from: file identities, revisions, issues."""
    return (
        tuple((d.path, d.revision) for d in report.documents),
        tuple((d.path, d.revision) for d in report.layouts),
        tuple((d.path, d.revision) for d in report.defaults),
        report.invalid,
    )


def scan(root: Path) -> ScanReport:
    documents, invalid, directories = [], [], []
    by_id = defaultdict(list)
    layouts, defaults = [], []
    revisions = defaultdict(list)

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
            if path.suffix.lower() not in (".md", ".json"):
                continue
            try:
                contained_path(root, path.relative_to(root))
                raw, revision = read_bytes(path)
                if path.suffix.lower() == ".json":
                    data = json_data(raw)
                    if data.get("kind") == "layout_defaults":
                        defaults.append(decode_defaults(path, raw, revision))
                    else:
                        parsed = decode_layout(raw)
                        loaded_layout = LoadedLayout(path, parsed.layout, revision, raw)
                        layouts.append(loaded_layout)
                        revisions[(parsed.layout.id, parsed.layout.version)].append(loaded_layout)
                    continue
                loaded = LoadedDocument(path, PARSED.decode(raw, revision.digest), revision)
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
    conflicts += tuple(
        DuplicateIdentity(
            identifier,
            tuple(d.path for d in entries),
            len({d.revision.digest for d in entries}) == 1,
        )
        for (identifier, _), entries in revisions.items()
        if len(entries) > 1
    )
    # Layout IDs have multiple legitimate versions, but cannot identify documents/defaults.
    identities = defaultdict(list)
    for d in documents:
        identities[d.document.id].append(("document", d.path))
    for d in layouts:
        identities[d.layout.id].append(("layout", d.path))
    for d in defaults:
        identities[d.id].append(("defaults", d.path))
    conflicts += tuple(
        DuplicateIdentity(identifier, tuple(path for _, path in entries), False)
        for identifier, entries in identities.items()
        if len({kind for kind, _ in entries}) > 1
        or (entries[0][0] == "defaults" and len(entries) > 1)
    )
    if len(defaults) > 1:
        invalid.extend(
            FileIssue(d.path, "Multiple default registries; resolve explicitly") for d in defaults
        )
    for d in defaults:
        if d.id in by_id:
            invalid.append(FileIssue(d.path, "Default registry UUID collides with document"))
    report = ScanReport(
        tuple(documents),
        tuple(invalid),
        conflicts,
        (),
        tuple(directories),
        tuple(layouts),
        tuple(defaults),
    )
    missing = []
    for loaded in documents:
        for reference in loaded.document.references():
            reason = reference_problem(report, reference)
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
    for loaded in (*layouts, *defaults):
        identifier = loaded.layout.id if isinstance(loaded, LoadedLayout) else loaded.id
        for reference in loaded.references():
            reason = reference_problem(report, reference)
            if reason:
                missing.append(
                    MissingReference(
                        identifier,
                        loaded.path,
                        reference.target_id,
                        reference.role,
                        reason,
                        reference.version,
                    )
                )
    return ScanReport(
        tuple(documents),
        tuple(invalid),
        conflicts,
        tuple(missing),
        tuple(directories),
        tuple(layouts),
        tuple(defaults),
    )


def reference_problem(report: ScanReport, reference) -> str | None:
    if any(c.document_id == reference.target_id for c in report.conflicts):
        return "Referenced UUID is ambiguous"
    if reference.role == "layout_id":
        targets = [
            d
            for d in report.layouts
            if d.layout.id == reference.target_id and d.layout.version == reference.version
        ]
        return None if len(targets) == 1 else "Referenced layout revision is missing or invalid"
    targets = [d.document for d in report.documents if d.document.id == reference.target_id]
    if len(targets) != 1:
        return "Referenced document is missing, invalid, or ambiguous"
    expected = {
        "habit_id": ("habit",),
        "field_id": ("metric_definition",),
        "note_id": ("note", "page", "year_page", "month_page", "week_page", "day_page"),
        "source_id": ("habit", "metric_definition"),
    }.get(reference.role)
    if expected and targets[0].kind not in expected:
        return f"Referenced document has wrong kind; expected {expected}"
    return None
