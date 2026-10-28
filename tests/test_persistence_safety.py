import os
import shutil
from uuid import uuid4

import pytest
from test_vault import day, habit, note

from habit_workspace.application.imports import ImportService
from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.documents import DocumentError
from habit_workspace.vault import atomic_io
from habit_workspace.vault.atomic_io import ConflictError, writer_lock
from habit_workspace.vault.format import decode, encode


@pytest.fixture
def session(tmp_path):
    return VaultSession.create(tmp_path / "vault", "Safety")


@pytest.mark.parametrize("value", [[], {}, None, 42, True])
def test_malformed_kind_is_a_document_error(value):
    document = note()
    document.metadata["hw"]["kind"] = value
    with pytest.raises(DocumentError):
        encode(document)


def test_merge_keys_are_rejected():
    raw = encode(note()).replace(b"hw:\n", b"hw:\n  <<: {extra: value}\n")
    with pytest.raises(DocumentError, match="merge"):
        decode(raw)


def test_failed_replace_preserves_original_and_recovery_copy(session, monkeypatch):
    loaded = session.create_document("Notes/save.md", note())
    original = loaded.path.read_bytes()
    actual_replace = os.replace

    def fail_document_replace(source, target):
        if target == loaded.path:
            raise OSError("Simulated interrupted replacement")
        return actual_replace(source, target)

    monkeypatch.setattr(atomic_io.os, "replace", fail_document_replace)
    with pytest.raises(OSError, match="interrupted"):
        session.save(loaded, note(identifier=loaded.document.id, body="New"))
    assert loaded.path.read_bytes() == original
    assert not list(loaded.path.parent.glob(".hw-write-*"))
    assert not (session.root / ".habit-workspace/write.lock").exists()
    assert any(
        p.read_bytes() == original for p in (session.root / ".habit-workspace/backups").glob("*.md")
    )


def test_create_collision_at_publication_does_not_overwrite(session, monkeypatch):
    target = session.root / "Notes/race.md"
    real_link = os.link

    def concurrent_create(source, destination):
        if destination == target:
            destination.write_bytes(b"External creation")
        return real_link(source, destination)

    monkeypatch.setattr(atomic_io.os, "link", concurrent_create)
    with pytest.raises(ConflictError):
        session.create_document("Notes/race.md", note())
    assert target.read_bytes() == b"External creation"


def test_edit_while_staging_is_detected(session, monkeypatch):
    loaded = session.create_document("Notes/stage.md", note())
    external = loaded.path.read_bytes() + b"External change"
    real_fsync = os.fsync
    changed = False

    def concurrent_edit(descriptor):
        nonlocal changed
        if not changed:
            changed = True
            loaded.path.write_bytes(external)
        return real_fsync(descriptor)

    monkeypatch.setattr(atomic_io.os, "fsync", concurrent_edit)
    with pytest.raises(ConflictError):
        session.save(loaded, note(identifier=loaded.document.id, body="App changes"))
    assert loaded.path.read_bytes() == external


def test_index_failure_does_not_make_successful_document_write_fail(session, monkeypatch):
    def fail_cache(report):
        raise OSError("Read-only cache")

    monkeypatch.setattr(session.index, "rebuild", fail_cache)
    loaded = session.create_document("Notes/cache-failure.md", note())
    assert loaded.path.exists()
    assert session.index_error and "Read-only cache" in session.index_error
    assert session.load(loaded.document.id).document.body == loaded.document.body


def test_corrupt_cache_and_copied_vault_rebuild(session, tmp_path):
    loaded = session.create_document("Notes/copy.md", note())
    session.index.path.write_bytes(b"Not SQLite")
    reopened = VaultSession.open(session.root)
    assert reopened.index.documents()[0]["id"] == str(loaded.document.id)
    copy = tmp_path / "portable"
    shutil.copytree(session.root, copy, ignore=shutil.ignore_patterns("index.sqlite"))
    destination = VaultSession.open(copy)
    assert destination.info.id == session.info.id
    assert destination.load(loaded.document.id).path.is_relative_to(copy)


def test_application_lock_and_duplicate_save_are_not_silent(session):
    loaded = session.create_document("Notes/one.md", note())
    with writer_lock(session.root), pytest.raises(ConflictError, match="locked"):
        session.save(loaded, loaded.document)
    (session.root / "duplicate.md").write_bytes(loaded.path.read_bytes())
    assert session.scan().conflicts[0].identical
    with pytest.raises(ConflictError):
        session.save(loaded, loaded.document)


def test_batch_import_reports_all_categories_and_final_dependencies(session, tmp_path):
    existing = session.create_document("Notes/existing.md", note())
    duplicate = tmp_path / "duplicate.md"
    duplicate.write_bytes(encode(note(identifier=existing.document.id, body="Different")))
    broken = tmp_path / "broken.md"
    broken.write_bytes(b"---\ninvalid: [\n---\n")
    habit_id = uuid4()
    daily, definition = tmp_path / "daily.md", tmp_path / "habit.md"
    daily.write_bytes(encode(day(habit_id)))
    definition.write_bytes(encode(habit(habit_id)))
    result = ImportService(session).import_files(
        [existing.path, duplicate, broken, daily, definition]
    )
    assert len(result.imported) == 2
    assert len(result.skipped) == len(result.invalid) == len(result.conflicting) == 1
    assert all(not entry.missing_references for entry in result.imported)


def test_missing_layout_is_disclosed_without_touching_unknown_blocks(session, tmp_path):
    document = note()
    document.metadata["hw"]["layout_history"] = [
        {"layout_id": str(uuid4()), "version": 2, "effective_at": "2026-10-29T10:00:00-03:00"}
    ]
    source = tmp_path / "layout-page.md"
    source.write_bytes(encode(document))
    result = ImportService(session).import_files([source])
    assert result.imported[0].missing_references[0].role == "layout_id"
    assert "missing or invalid" in result.imported[0].missing_references[0].reason


def test_invalid_and_symlinked_manifest_are_not_modified(session, tmp_path):
    manifest = session.root / ".habit-workspace/vault.json"
    outside = tmp_path / "metadata.json"
    manifest.rename(outside)
    raw = outside.read_bytes()
    manifest.symlink_to(outside)
    with pytest.raises(DocumentError):
        VaultSession.open(session.root)
    assert outside.read_bytes() == raw
