"""Exercise real Qt events without launching a GUI or depending on pytest-qt."""

import time

from PySide6.QtCore import QCoreApplication
from test_vault import note

from habit_workspace.application.vault import VaultSession
from habit_workspace.vault.watcher import VaultWatcher


def wait_for(app, predicate, timeout=4):
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    assert predicate()


def test_watcher_external_replace_rename_nested_creation_and_fallback(tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    session = VaultSession.create(tmp_path / "vault", "Watcher")
    loaded = session.create_document("Notes/watch.md", note(body="Before"))
    watcher = VaultWatcher(session, debounce_ms=10, rescan_ms=100)
    observed = []
    errors = []
    watcher.refreshed.connect(observed.append)
    watcher.failed.connect(errors.append)
    watcher.start()
    try:
        replacement = loaded.path.with_suffix(".tmp")
        replacement.write_bytes(loaded.path.read_bytes().replace(b"Before", b"After!"))
        replacement.replace(loaded.path)
        wait_for(app, lambda: any(r.documents[0].document.body == "After!" for r in observed))
        moved = session.root / "Reorganized/Nested/moved.md"
        moved.parent.mkdir(parents=True)
        loaded.path.rename(moved)
        wait_for(app, lambda: any(r.documents[0].path == moved for r in observed))
        assert str(moved) in watcher.paths
        moved.write_bytes(moved.read_bytes().replace(b"After!", b"Again!"))
        wait_for(app, lambda: any(r.documents[0].document.body == "Again!" for r in observed))
        # Even missed OS notifications are covered by periodic rescan.
        watcher.clear_paths()
        session.index.path.unlink()
        moved.write_bytes(moved.read_bytes().replace(b"Again!", b"Final!"))
        wait_for(app, lambda: any(r.documents[0].document.body == "Final!" for r in observed))
        assert session.index.path.exists()
        assert not errors
    finally:
        watcher.stop()


def test_watcher_preserves_corrupt_file_and_recovers(tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    session = VaultSession.create(tmp_path / "vault", "Watcher")
    loaded = session.create_document("Notes/watch.md", note())
    raw = loaded.path.read_bytes()
    watcher = VaultWatcher(session, debounce_ms=10, rescan_ms=100)
    watcher.start()
    try:
        loaded.path.write_bytes(b"corrupted")
        wait_for(app, lambda: bool(session.report.invalid))
        assert loaded.path.read_bytes() == b"corrupted"
        loaded.path.write_bytes(raw)
        wait_for(app, lambda: bool(session.report.documents))
        assert not session.report.invalid
    finally:
        watcher.stop()
