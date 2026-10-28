"""Rebuild a complete SQLite generation in a transaction and publish atomically."""

import os
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

from habit_workspace.vault.atomic_io import contained_path, sync_directory
from habit_workspace.vault.scanner import ScanReport


class IndexCache:
    def __init__(self, root: Path):
        self.root = root
        self.path = root / ".habit-workspace/index.sqlite"

    def rebuild(self, report: ScanReport) -> None:
        contained_path(self.root, ".habit-workspace/index.sqlite", internal=True)
        descriptor, filename = tempfile.mkstemp(prefix=".index-", dir=self.path.parent)
        os.close(descriptor)
        temporary = Path(filename)
        try:
            with closing(sqlite3.connect(temporary)) as connection, connection:
                connection.executescript("""
                    PRAGMA user_version = 1;
                    CREATE TABLE documents (
                        path TEXT PRIMARY KEY, id TEXT NOT NULL, kind TEXT NOT NULL,
                        schema_version INTEGER NOT NULL, title TEXT NOT NULL,
                        digest TEXT NOT NULL, size INTEGER NOT NULL, mtime_ns INTEGER NOT NULL
                    );
                    CREATE INDEX document_identity ON documents(id);
                    CREATE TABLE references_cache (
                        source_path TEXT, target_id TEXT, role TEXT, version INTEGER
                    );
                    CREATE TABLE issues (path TEXT, message TEXT);
                """)
                connection.executemany(
                    "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    [
                        (
                            str(d.path.relative_to(self.root)),
                            str(d.document.id),
                            d.document.kind.value,
                            d.document.schema_version,
                            d.document.title,
                            d.revision.digest,
                            d.revision.size,
                            d.revision.mtime_ns,
                        )
                        for d in report.documents
                    ],
                )
                connection.executemany(
                    "INSERT INTO references_cache VALUES (?, ?, ?, ?)",
                    [
                        (
                            str(d.path.relative_to(self.root)),
                            str(ref.target_id),
                            ref.role,
                            ref.version,
                        )
                        for d in report.documents
                        for ref in d.document.references()
                    ],
                )
                connection.executemany(
                    "INSERT INTO issues VALUES (?, ?)",
                    [
                        (str(issue.path.relative_to(self.root)), issue.message)
                        for issue in report.invalid
                    ],
                )
            with temporary.open("rb") as stream:
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            sync_directory(self.path.parent)
        finally:
            temporary.unlink(missing_ok=True)

    def documents(self, identifier: str | None = None) -> list[dict]:
        """Cache lookup only. Call session.scan() to refresh external changes."""
        contained_path(self.root, ".habit-workspace/index.sqlite", internal=True)
        connection = sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True)
        try:
            connection.row_factory = sqlite3.Row
            if identifier is None:
                rows = connection.execute("SELECT * FROM documents ORDER BY path")
            else:
                rows = connection.execute(
                    "SELECT * FROM documents WHERE id=? ORDER BY path", (identifier,)
                )
            return [dict(row) for row in rows]
        finally:
            connection.close()
