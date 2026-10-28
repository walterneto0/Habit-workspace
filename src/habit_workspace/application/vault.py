"""Coordinate canonical writes and repairable index refreshes."""

import sqlite3
from pathlib import Path
from uuid import UUID

from habit_workspace.domain.documents import Document, DocumentError
from habit_workspace.indexing.cache import IndexCache
from habit_workspace.vault.atomic_io import ConflictError, writer_lock
from habit_workspace.vault.manager import VaultInfo, VaultManager
from habit_workspace.vault.repositories import DocumentRepository
from habit_workspace.vault.scanner import LoadedDocument, ScanReport, scan


class VaultSession:
    def __init__(self, info: VaultInfo):
        self.info = info
        self.root = info.root
        self.repository = DocumentRepository(self.root)
        self.index = IndexCache(self.root)
        self.index_error: str | None = None
        self.report = self.scan()

    @classmethod
    def create(cls, directory: Path, name: str) -> VaultSession:
        return cls(VaultManager.create(directory, name))

    @classmethod
    def open(cls, directory: Path) -> VaultSession:
        return cls(VaultManager.open(directory))

    def scan(self) -> ScanReport:
        report = scan(self.root)
        self.report = report
        try:
            self.index.rebuild(report)
            self.index_error = None
        except (sqlite3.Error, OSError, DocumentError) as error:
            # Files remain authoritative and readable even if the cache is unavailable.
            self.index_error = f"Index unavailable; canonical files are intact: {error}"
        return report

    def load(self, identifier: UUID | str) -> LoadedDocument:
        identifier = UUID(str(identifier))
        entries = [d for d in self.scan().documents if d.document.id == identifier]
        if len(entries) > 1:
            raise ConflictError(f"Duplicate UUID {identifier}: compare the files explicitly")
        if not entries:
            raise DocumentError(f"Document {identifier} is missing or invalid")
        return entries[0]

    def create_document(self, relative: str | Path, document: Document) -> LoadedDocument:
        document.validate()
        with writer_lock(self.root):
            report = scan(self.root)
            if (
                any(d.document.id == document.id for d in report.documents)
                or any(d.layout.id == document.id for d in report.layouts)
                or any(d.id == document.id for d in report.defaults)
            ):
                raise ConflictError(f"Document UUID already exists: {document.id}")
            loaded = self.repository.create(relative, document)
            self.scan()
        return loaded

    def save(self, loaded: LoadedDocument, document: Document) -> LoadedDocument:
        document.validate()
        with writer_lock(self.root):
            entries = [d for d in scan(self.root).documents if d.document.id == loaded.document.id]
            if len(entries) != 1 or entries[0].path != loaded.path:
                raise ConflictError("Document identity is missing, moved, invalid, or duplicated")
            saved = self.repository.save(loaded, document)
            self.scan()
        return saved
