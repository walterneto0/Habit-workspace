"""Phase 6.5A: unchanged files are not re-parsed or re-indexed; change detection stays.

Every scan still reads and hashes every file. Only the YAML parse of byte-identical
content, the SQLite rebuild of an identical snapshot and the UI refresh of an
unchanged snapshot are skipped.
"""

import os

from PySide6.QtCore import QCoreApplication
from test_vault import note

from habit_workspace.application.vault import VaultSession
from habit_workspace.vault import scanner
from habit_workspace.vault.format import encode
from habit_workspace.vault.watcher import VaultWatcher


def note_id(raw):
    from habit_workspace.vault.format import decode

    return decode(raw).id


def document(report, path):
    return next(d.document for d in report.documents if d.path == path)


def test_unchanged_bytes_reuse_parse_and_any_byte_change_is_detected(tmp_path):
    session = VaultSession.create(tmp_path / "vault", "Reuso")
    one = session.create_document("Notes/one.md", note(body="Antes"))
    two = session.create_document("Notes/two.md", note(body="Outro"))
    first = session.scan()
    second = session.scan()
    assert document(second, one.path) is document(first, one.path)
    # Same size and restored mtime: only the content hash can notice this edit.
    stat = one.path.stat()
    one.path.write_bytes(one.path.read_bytes().replace(b"Antes", b"Agora"))
    os.utime(one.path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    third = session.scan()
    assert document(third, one.path).body == "Agora"
    assert document(third, two.path) is document(first, two.path)


def test_mutated_cached_document_is_parsed_again(tmp_path):
    session = VaultSession.create(tmp_path / "vault", "Reuso")
    loaded = session.create_document("Notes/one.md", note(body="Texto"))
    cached = document(session.scan(), loaded.path)
    cached.metadata["hw"]["title"] = "Alterado em memória"
    fresh = document(session.scan(), loaded.path)
    assert fresh is not cached
    assert fresh.title != "Alterado em memória"


def test_cache_is_bounded():
    raw = encode(note())
    cache = scanner._ParsedCache(limit_bytes=len(raw) + 1)
    cache.decode(raw, "a")
    cache.decode(raw, "b")
    assert list(cache.entries) == ["b"]
    assert cache.size == len(raw)
    oversized = scanner._ParsedCache(limit_bytes=1)
    assert oversized.decode(raw, "a").id == note_id(raw)
    assert not oversized.entries  # too large to keep, still parsed correctly


def test_identical_snapshot_skips_index_rebuild_but_missing_index_is_rebuilt(tmp_path, monkeypatch):
    session = VaultSession.create(tmp_path / "vault", "Índice")
    session.create_document("Notes/one.md", note())
    calls = []
    original = session.index.rebuild
    monkeypatch.setattr(session.index, "rebuild", lambda r: calls.append(1) or original(r))
    session.scan()
    assert calls == []
    session.index.path.unlink()
    session.scan()
    assert calls == [1] and session.index.path.is_file()
    session.request_index_rebuild()
    session.scan()
    assert calls == [1, 1]
    session.create_document("Notes/two.md", note())
    assert len(calls) == 3


def test_failed_index_is_retried_even_without_file_changes(tmp_path, monkeypatch):
    session = VaultSession.create(tmp_path / "vault", "Índice")
    original = session.index.rebuild

    def broken(_report):
        raise OSError("disk full")

    monkeypatch.setattr(session.index, "rebuild", broken)
    session.request_index_rebuild()
    session.scan()
    assert session.index_error
    monkeypatch.setattr(session.index, "rebuild", original)
    session.scan()
    assert session.index_error is None


def test_watcher_announces_only_changes_and_keeps_duplicate_diagnostics(tmp_path):
    QCoreApplication.instance() or QCoreApplication([])
    session = VaultSession.create(tmp_path / "vault", "Watcher")
    loaded = session.create_document("Notes/one.md", note(body="Antes"))
    watcher = VaultWatcher(session)
    observed = []
    watcher.refreshed.connect(observed.append)
    try:
        watcher.refresh()
        watcher.refresh()
        assert len(observed) == 1
        (session.root / "copy.md").write_bytes(loaded.path.read_bytes() + b"diferente")
        watcher.refresh()
        assert len(observed) == 2 and observed[-1].conflicts
        watcher.refresh()
        assert len(observed) == 2
        assert session.report.conflicts  # still disclosed on every scan
        watcher.refresh(force=True)
        assert len(observed) == 3
    finally:
        watcher.stop()


def test_manual_reindex_rebuilds_an_unchanged_vault(tmp_path, monkeypatch):
    from PySide6.QtCore import QSettings

    from habit_workspace.presentation.controllers import WorkspaceController

    QCoreApplication.instance() or QCoreApplication([])
    desktop = WorkspaceController(
        settings=QSettings(str(tmp_path / "p.ini"), QSettings.Format.IniFormat)
    )
    try:
        desktop.createVault(str(tmp_path / "vault"), "Reindex")
        calls = []
        original = desktop.session.index.rebuild
        monkeypatch.setattr(
            desktop.session.index, "rebuild", lambda r: calls.append(1) or original(r)
        )
        desktop.reindex()
        assert calls == [1]
        assert desktop.state["notice"] == "Índice reconstruído a partir dos arquivos."
    finally:
        desktop.close()
