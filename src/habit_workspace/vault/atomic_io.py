"""Bounded reads, optimistic revisions, and same-volume atomic publication."""

import hashlib
import json
import os
import socket
import stat
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

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


class LockedError(ConflictError):
    """Another writer holds, or an interrupted writer left, ``write.lock``."""


@dataclass(frozen=True)
class LockStatus:
    """Read-only diagnosis of ``.habit-workspace/write.lock``; never changes it."""

    path: Path
    owner: dict | None  # None: missing/unreadable owner record (e.g. crash after mkdir)
    entries: tuple[str, ...]
    age_seconds: float | None
    same_machine: bool
    process: str  # running, not_running, reused_pid, unknown

    @property
    def stale(self) -> bool:
        """Ownership is *verified* as ended: never true from age or presence alone."""
        return (
            self.owner is not None
            and self.entries == (LOCK_OWNER,)
            and self.same_machine
            and self.process in ("not_running", "reused_pid")
        )

    def describe(self) -> str:
        owner = self.owner or {}
        if owner:
            since = owner.get("created_at", "?")
            holder = f"processo {owner.get('pid', '?')} em {owner.get('host', '?')}, desde {since}"
        else:
            holder = "dono não identificado (gravação interrompida logo ao iniciar?)"
        state = {
            "running": "esse processo ainda está em execução",
            "not_running": "esse processo não está mais em execução neste computador",
            "reused_pid": "o número do processo foi reutilizado por outro programa",
            "unknown": "não foi possível verificar o processo",
        }[self.process]
        return f"{holder}; {state}"


LOCK_OWNER = "owner.json"


def _boot_id() -> str | None:
    try:
        return Path("/proc/sys/kernel/random/boot_id").read_text().strip() or None
    except OSError:
        return None


def _process_started(pid: int) -> str | None:
    """Linux start time in clock ticks; distinguishes a reused PID. None elsewhere."""
    try:
        stat_line = Path(f"/proc/{pid}/stat").read_text()
    except OSError:
        return None
    return stat_line.rsplit(")", 1)[1].split()[19]


def _owner_record(token: str) -> dict:
    return {
        "app": "habit-workspace",
        "token": token,
        "pid": os.getpid(),
        "host": socket.gethostname(),
        "boot_id": _boot_id(),
        "process_started": _process_started(os.getpid()),
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }


def inspect_lock(root: Path) -> LockStatus | None:
    path = contained_path(root, ".habit-workspace/write.lock", internal=True)
    try:
        entries = tuple(sorted(os.listdir(path)))
        age = max(0.0, time.time() - path.stat().st_mtime)
    except FileNotFoundError:
        return None
    except NotADirectoryError:
        return LockStatus(path, None, (), None, False, "unknown")
    owner = None
    try:
        raw, _ = read_bytes(path / LOCK_OWNER, limit=4096)
        value = json.loads(raw)
        if (
            isinstance(value, dict)
            and value.get("app") == "habit-workspace"
            and isinstance(value.get("token"), str)
            and type(value.get("pid")) is int
            and value["pid"] > 0
        ):
            owner = value
    except OSError, ValueError, DocumentError:
        owner = None
    same = bool(
        owner and owner.get("host") == socket.gethostname() and owner.get("boot_id") == _boot_id()
    )
    process = "unknown"
    if owner and same and os.name == "posix":
        try:
            os.kill(owner["pid"], 0)
        except ProcessLookupError:
            process = "not_running"
        except PermissionError:
            process = "running"  # exists, owned by someone else
        else:
            process = "running"
        if process == "running" and owner.get("process_started"):
            started = _process_started(owner["pid"])
            if started is not None and started != owner["process_started"]:
                process = "reused_pid"
    return LockStatus(path, owner, entries, age, same, process)


def recover_lock(root: Path, token: str) -> LockStatus:
    """Remove an interrupted writer's lock only after verifying it is stale.

    ``token`` must be the one shown by :func:`inspect_lock`, proving the person
    reviewed this exact lock. Refuses unidentified owners, other machines or boots,
    running processes, unexpected contents and any lock not proven stale.
    Canonical documents are never touched.
    """
    status = inspect_lock(root)
    if status is None:
        raise DocumentError("Não há bloqueio de gravação neste cofre.")
    if not status.owner or status.owner.get("token") != token:
        raise ConflictError(
            "Recuperação recusada: o bloqueio não corresponde ao código informado ou não "
            "tem dono identificável. Feche todos os aplicativos que usam o cofre e "
            "inspecione .habit-workspace/write.lock manualmente."
        )
    if not status.stale:
        raise ConflictError(
            "Recuperação recusada: não foi possível comprovar que a gravação terminou ("
            + status.describe()
            + "). Nada foi removido."
        )
    (status.path / LOCK_OWNER).unlink()
    status.path.rmdir()
    sync_directory(status.path.parent)
    return status


@contextmanager
def writer_lock(root: Path):
    """Exclusive directory lock shared by every application writer.

    The owner record is diagnostic only: presence, age or PID never release a lock
    automatically. Only the holder (matching token) removes its own lock.
    """
    path = contained_path(root, ".habit-workspace/write.lock", internal=True)
    try:
        path.mkdir()
    except FileExistsError as error:
        status = inspect_lock(root)
        detail = status.describe() if status else "liberado em seguida; tente novamente"
        raise LockedError(
            "Cofre bloqueado por outra gravação (.habit-workspace/write.lock): "
            + detail
            + ". Nada foi salvo. Se outra janela estiver salvando, tente novamente em "
            "instantes; se uma gravação foi interrompida, veja o diagnóstico com "
            "'habit-workspace vault lock-status <cofre>'."
        ) from error
    token = uuid4().hex
    owner = path / LOCK_OWNER
    try:
        try:
            owner.write_text(json.dumps(_owner_record(token)) + "\n", encoding="utf-8")
        except OSError:
            pass  # Diagnostics degrade to "unknown owner"; the lock itself still holds.
        yield
    finally:
        try:
            if json.loads(owner.read_text(encoding="utf-8")).get("token") == token:
                owner.unlink()
        except OSError, ValueError:
            pass
        path.rmdir()
