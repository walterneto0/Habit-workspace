"""Bounded reads, optimistic revisions, and same-volume atomic publication."""

import hashlib
import os
import stat
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from habit_workspace.domain.documents import DocumentError
from habit_workspace.vault.format import MAX_DOCUMENT_BYTES


class ConflictError(DocumentError):
    """User action is required; no automatic overwrite or lock recovery."""


@dataclass(frozen=True)
class Revision:
    digest: str
    size: int
    mtime_ns: int
    device: int
    inode: int


def contained_path(root: Path, relative: str | Path, *, internal: bool = False) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise DocumentError("Path must be relative and contained in the vault")
    if not internal and path.parts[0] == ".habit-workspace":
        raise DocumentError("Canonical documents cannot be stored in the internal directory")
    current = root
    for part in path.parts:
        current /= part
        if current.is_symlink():
            raise DocumentError(f"Symbolic links are not supported: {current}")
    if not current.resolve().is_relative_to(root.resolve()):
        raise DocumentError("Path escapes the vault")
    return current


def read_bytes(path: Path, *, limit: int = MAX_DOCUMENT_BYTES) -> tuple[bytes, Revision]:
    if path.is_symlink():
        raise DocumentError(f"Symbolic links are not supported: {path}")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise DocumentError(f"Not a regular file: {path}")
        if before.st_size > limit:
            raise DocumentError(f"File exceeds {limit} byte limit: {path}")
        raw = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    if len(raw) > limit:
        raise DocumentError(f"File exceeds {limit} byte limit: {path}")
    if (before.st_mtime_ns, before.st_size, before.st_ctime_ns) != (
        after.st_mtime_ns,
        after.st_size,
        after.st_ctime_ns,
    ):
        raise ConflictError(f"File changed while reading: {path}")
    return raw, Revision(
        hashlib.sha256(raw).hexdigest(), len(raw), after.st_mtime_ns, after.st_dev, after.st_ino
    )


def sync_directory(path: Path) -> None:
    if os.name == "posix":
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def atomic_write(
    path: Path,
    raw: bytes,
    *,
    expected: Revision | None = None,
    backup_directory: Path | None = None,
) -> None:
    """None means create-only. Existing writes require the exact loaded revision.

    External editors do not honor our lock. We check again immediately before
    replace, but portable filesystems offer no atomic compare-and-swap of a path.
    Recovery copies retain the previous revision before any replacement.
    """
    old = None
    if expected is not None:
        try:
            old, actual = read_bytes(path)
        except FileNotFoundError as error:
            raise ConflictError(f"Document was moved or deleted: {path}") from error
        if actual != expected:
            raise ConflictError(f"External edits detected; reload or compare: {path}")
    elif path.exists() or path.is_symlink():
        raise ConflictError(f"Destination already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".hw-write-", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if expected is None:
            # Hard-link publication is atomic and fails if ANY destination appears.
            try:
                os.link(temporary_path, path)
            except FileExistsError as error:
                raise ConflictError(f"Destination already exists: {path}") from error
        else:
            if backup_directory is None:
                raise DocumentError("Replacing a document requires a recovery directory")
            backup_directory.mkdir(parents=True, exist_ok=True)
            backup = backup_directory / f"{expected.digest}.md"
            if not backup.exists():
                atomic_write(backup, old)
            elif read_bytes(backup)[0] != old:
                raise ConflictError(f"Recovery copy has been changed: {backup}")
            try:
                _, actual = read_bytes(path)
            except FileNotFoundError as error:
                raise ConflictError(f"Document was moved or deleted: {path}") from error
            if actual != expected:
                raise ConflictError(f"External edits detected; reload or compare: {path}")
            os.replace(temporary_path, path)
        sync_directory(path.parent)
    finally:
        temporary_path.unlink(missing_ok=True)


@contextmanager
def writer_lock(root: Path):
    path = contained_path(root, ".habit-workspace/write.lock", internal=True)
    try:
        path.mkdir()
    except FileExistsError as error:
        raise ConflictError(
            "Vault is locked by another writer; inspect write.lock before recovery"
        ) from error
    try:
        yield
    finally:
        path.rmdir()
