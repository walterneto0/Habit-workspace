"""Phase 6.5A: interrupted writers, lock diagnostics and conservative recovery.

Interruptions are real: a child process takes the writer lock (and optionally
starts a canonical or multi-file layout write) and dies with ``os._exit``, which
skips every ``finally`` block, just like a crash or a killed process.
"""

import json
import os
import subprocess
import sys
from copy import deepcopy
from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest
from test_layouts import ACTIVE, START, WEEK
from test_vault import note

from habit_workspace.application.layouts import LayoutService
from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.documents import DocumentError
from habit_workspace.domain.layouts import Binding, Component, InputConfig, LayoutTemplate
from habit_workspace.domain.metrics import FieldDefinition
from habit_workspace.vault.atomic_io import (
    LOCK_OWNER,
    ConflictError,
    LockedError,
    inspect_lock,
    recover_lock,
    writer_lock,
)
from habit_workspace.vault.layouts import encode_layout
from habit_workspace.vault.metrics import field_document

LOCK_AND_DIE = """
import os, sys
from pathlib import Path
from habit_workspace.vault.atomic_io import writer_lock
with writer_lock(Path(sys.argv[1])):
    os._exit(3)
"""

SAVE_AND_DIE = """
import copy, os, sys
from pathlib import Path
from habit_workspace.application.vault import VaultSession
session = VaultSession.open(Path(sys.argv[1]))
loaded = session.load(sys.argv[2])
document = copy.deepcopy(loaded.document)
document.body = "Texto novo que nunca foi publicado"
os.replace = lambda *args: os._exit(4)  # killed right before the atomic replace
session.save(loaded, document)
"""

LAYOUT_AND_DIE = """
import json, os, sys
from pathlib import Path
from habit_workspace.application.layouts import LayoutService
from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.metrics import field_from_mapping
from habit_workspace.domain.temporal import PeriodRef
from habit_workspace.vault.layouts import decode_layout
from datetime import datetime
plan = json.loads(Path(sys.argv[2]).read_text())
service = LayoutService(VaultSession.open(Path(sys.argv[1])))
service._assign = lambda *args, **kwargs: os._exit(5)  # killed before the page write
service.save_revision(
    PeriodRef(plan["period"]),
    decode_layout(plan["layout"].encode()).layout,
    datetime.fromisoformat(plan["effective_at"]),
    new_fields=(field_from_mapping(plan["field"]),),
)
"""


def child(code: str, *args) -> int:
    return subprocess.run(
        [sys.executable, "-c", code, *map(str, args)], capture_output=True, timeout=60
    ).returncode


def canonical_bytes(root: Path) -> dict:
    return {
        p.relative_to(root): p.read_bytes()
        for p in root.rglob("*.md")
        if ".habit-workspace" not in p.parts
    }


@pytest.fixture
def session(tmp_path):
    return VaultSession.create(tmp_path / "vault", "Bloqueio")


def test_normal_lock_records_owner_and_releases(session):
    lock = session.root / ".habit-workspace/write.lock"
    with writer_lock(session.root):
        status = inspect_lock(session.root)
        assert status.owner["pid"] == os.getpid()
        assert status.process == "running" and not status.stale
        with pytest.raises(LockedError, match="ainda está em execução"):
            session.create_document("Notes/blocked.md", note())
    assert not lock.exists()
    assert inspect_lock(session.root) is None
    session.create_document("Notes/after.md", note())


def test_exception_inside_lock_still_releases(session):
    with pytest.raises(RuntimeError), writer_lock(session.root):
        raise RuntimeError("falha comum")
    assert inspect_lock(session.root) is None


def test_killed_writer_is_diagnosed_and_blocks_without_damage(session):
    loaded = session.create_document("Notes/one.md", note(body="Original"))
    before = canonical_bytes(session.root)
    assert child(LOCK_AND_DIE, session.root) == 3
    status = inspect_lock(session.root)
    assert status.process == "not_running" and status.same_machine and status.stale
    assert status.entries == (LOCK_OWNER,)
    with pytest.raises(LockedError, match="não está mais em execução") as error:
        session.save(loaded, loaded.document)
    assert "lock-status" in str(error.value) and "Nada foi salvo" in str(error.value)
    assert canonical_bytes(session.root) == before
    # Nothing is released automatically, however many times writers retry.
    with pytest.raises(LockedError):
        session.create_document("Notes/two.md", note())
    assert inspect_lock(session.root).stale


def test_unsafe_recovery_is_refused_and_leaves_the_lock(session):
    lock = session.root / ".habit-workspace/write.lock"
    # 1. Live owner (this process), however old the lock looks.
    with writer_lock(session.root):
        os.utime(lock, (0, 0))
        token = inspect_lock(session.root).owner["token"]
        with pytest.raises(ConflictError, match="Recuperação recusada"):
            recover_lock(session.root, token)
        assert lock.is_dir()
    # 2. Unidentified owner: crash between mkdir and the owner record.
    lock.mkdir()
    status = inspect_lock(session.root)
    assert status.owner is None and "dono não identificado" in status.describe()
    with pytest.raises(ConflictError, match="Recuperação recusada"):
        recover_lock(session.root, "qualquer")
    lock.rmdir()
    # 3. Dead owner, but wrong token / other machine / unexpected contents.
    assert child(LOCK_AND_DIE, session.root) == 3
    owner = json.loads((lock / LOCK_OWNER).read_text())
    with pytest.raises(ConflictError, match="código informado"):
        recover_lock(session.root, "outro-token")
    (lock / LOCK_OWNER).write_text(json.dumps(owner | {"host": "outro-computador"}))
    assert not inspect_lock(session.root).same_machine
    with pytest.raises(ConflictError, match="Recuperação recusada"):
        recover_lock(session.root, owner["token"])
    (lock / LOCK_OWNER).write_text(json.dumps(owner))
    (lock / "inesperado.txt").write_text("?")
    with pytest.raises(ConflictError, match="Recuperação recusada"):
        recover_lock(session.root, owner["token"])
    assert lock.is_dir() and (lock / "inesperado.txt").exists()


@pytest.mark.skipif(not Path("/proc/self/stat").exists(), reason="Linux process start times")
def test_reused_pid_is_recognised_as_stale(session):
    lock = session.root / ".habit-workspace/write.lock"
    assert child(LOCK_AND_DIE, session.root) == 3
    owner = json.loads((lock / LOCK_OWNER).read_text())
    # A live, unrelated process now has the recorded PID (simulated with ours).
    (lock / LOCK_OWNER).write_text(json.dumps(owner | {"pid": os.getpid()}))
    status = inspect_lock(session.root)
    assert status.process == "reused_pid" and status.stale


def test_verified_recovery_then_retry_succeeds(session):
    loaded = session.create_document("Notes/one.md", note(body="Original"))
    assert child(LOCK_AND_DIE, session.root) == 3
    token = inspect_lock(session.root).owner["token"]
    recovered = recover_lock(session.root, token)
    assert recovered.process == "not_running"
    assert inspect_lock(session.root) is None
    with pytest.raises(DocumentError, match="Não há bloqueio"):
        recover_lock(session.root, token)
    document = deepcopy(loaded.document)
    document.body = "Depois da recuperação"
    assert session.save(loaded, document).document.body == "Depois da recuperação"


def test_killed_canonical_write_preserves_original_bytes(session):
    loaded = session.create_document("Notes/one.md", note(body="Original"))
    original = loaded.path.read_bytes()
    assert child(SAVE_AND_DIE, session.root, loaded.document.id) == 4
    assert loaded.path.read_bytes() == original
    leftovers = list(loaded.path.parent.glob(".hw-write-*"))
    assert leftovers  # orphaned temporary kept for inspection, never parsed
    report = session.scan()
    assert not report.invalid and len(report.documents) == 1
    backups = list((session.root / ".habit-workspace/backups").iterdir())
    assert [b.read_bytes() for b in backups] == [original]
    recover_lock(session.root, inspect_lock(session.root).owner["token"])
    document = deepcopy(session.load(loaded.document.id).document)
    document.body = "Gravado na nova tentativa"
    session.save(session.load(loaded.document.id), document)
    assert b"Gravado na nova tentativa" in loaded.path.read_bytes()


def test_killed_layout_publication_never_assigns_missing_dependencies(session, tmp_path):
    service = LayoutService(session)
    v1 = LayoutTemplate(uuid4(), 1, "Semana", ())
    page = service.save_revision(WEEK, v1, START)
    page_bytes = page.path.read_bytes()
    field = FieldDefinition(uuid4(), "Páginas lidas", "integer", ACTIVE)
    v2 = v1.new_revision(
        blocks=(
            Component(
                uuid4(),
                "integer_input",
                field.name,
                InputConfig("integer"),
                binding=Binding(field.id, "metric"),
            ),
        )
    )
    plan = tmp_path / "plan.json"
    plan.write_text(
        json.dumps(
            {
                "period": str(WEEK),
                "layout": encode_layout(v2, service.load(v1.id, 1)).decode(),
                "effective_at": ACTIVE.isoformat(),
                "field": field_document(field).metadata["hw"],
            },
            default=str,
        )
    )
    assert child(LAYOUT_AND_DIE, session.root, plan) == 5
    report = session.scan()
    # Dependencies were published first and stay discoverable; no assignment points
    # to them yet, and nothing dangling was assigned.
    assert page.path.read_bytes() == page_bytes
    assert {(d.layout.id, d.layout.version) for d in report.layouts} == {(v1.id, 1), (v1.id, 2)}
    assert any(d.document.id == field.id for d in report.documents)
    assert not report.missing_references
    assert LayoutService.resolve_report(report, WEEK, ACTIVE).layout == v1
    status = inspect_lock(session.root)
    assert status.stale
    recover_lock(session.root, status.owner["token"])
    for _ in range(2):  # idempotent retries
        service.save_revision(WEEK, v2, ACTIVE, new_fields=(field,))
    report = session.scan()
    assert LayoutService.resolve_report(report, WEEK, ACTIVE).layout == v2
    assert LayoutService.resolve_report(report, WEEK, START).layout == v1
    assert sum(d.document.kind == "metric_definition" for d in report.documents) == 1
    assert len(report.layouts) == 2 and not report.conflicts


def test_gui_capture_explains_a_stale_lock_and_writes_nothing(tmp_path):
    from PySide6.QtCore import QCoreApplication, QSettings

    from habit_workspace.application.habits import HabitService
    from habit_workspace.domain.temporal import PeriodRef
    from habit_workspace.presentation.controllers import WorkspaceController

    QCoreApplication.instance() or QCoreApplication([])
    desktop = WorkspaceController(
        settings=QSettings(str(tmp_path / "p.ini"), QSettings.Format.IniFormat),
        today=date(2026, 10, 29),
    )
    try:
        desktop.createVault(str(tmp_path / "vault"), "GUI")
        habit = HabitService(desktop.session).create(name="Ler", period=PeriodRef("day/2026-10-29"))
        desktop.navigate("day", "2026-10-29")
        before = canonical_bytes(desktop.session.root)
        assert child(LOCK_AND_DIE, desktop.session.root) == 3
        assert not desktop.setCheckin(str(habit.habit.id), "done", "null")
        notice = desktop.state["notice"]
        assert desktop.state["noticeError"]
        assert notice.startswith("Não salvo: Cofre bloqueado")
        assert "lock-status" in notice
        assert canonical_bytes(desktop.session.root) == before
    finally:
        desktop.close()


def test_cli_lock_status_and_unlock(session):
    def cli(*args):
        result = subprocess.run(
            [sys.executable, "-m", "habit_workspace", "vault", *map(str, args)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return result.returncode, json.loads(result.stdout)

    assert cli("lock-status", session.root) == (0, {"locked": False})
    assert child(LOCK_AND_DIE, session.root) == 3
    code, status = cli("lock-status", session.root)
    assert code == 0 and status["locked"] and status["verified_stale"]
    code, refused = cli("unlock", session.root, "--token", "errado")
    assert code == 1 and "Recuperação recusada" in refused["error"]
    assert inspect_lock(session.root) is not None
    code, done = cli("unlock", session.root, "--token", status["owner"]["token"])
    assert code == 0 and done["recovered"]["process"] == "not_running"
    assert inspect_lock(session.root) is None
