"""Canonical file reads/writes. The caller serializes application writers."""

from pathlib import Path

from habit_workspace.domain.documents import Document, DocumentError
from habit_workspace.vault.atomic_io import atomic_write, contained_path, read_bytes
from habit_workspace.vault.format import decode, encode
from habit_workspace.vault.scanner import LoadedDocument


class DocumentRepository:
    def __init__(self, root: Path):
        self.root = root

    def read(self, relative: str | Path) -> LoadedDocument:
        path = contained_path(self.root, relative)
        raw, revision = read_bytes(path)
        return LoadedDocument(path, decode(raw), revision)

    def create(self, relative: str | Path, document: Document) -> LoadedDocument:
        path = contained_path(self.root, relative)
        if path.suffix.lower() != ".md":
            raise DocumentError("Document paths must have a .md extension")
        raw = encode(document)
        atomic_write(path, raw)
        return self.read(relative)

    def save(self, loaded: LoadedDocument, document: Document) -> LoadedDocument:
        if document.id != loaded.document.id:
            raise DocumentError("Saving cannot change a document's UUID")
        relative = loaded.path.relative_to(self.root)
        path = contained_path(self.root, relative)
        backup = contained_path(self.root, ".habit-workspace/backups", internal=True)
        atomic_write(path, encode(document), expected=loaded.revision, backup_directory=backup)
        return self.read(relative)
