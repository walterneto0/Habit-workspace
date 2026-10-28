"""Phase 1 contracts; all canonical data lives in isolated temporary vaults."""

import os
import socket
from uuid import uuid4

import pytest

from habit_workspace.application.imports import ImportService
from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.documents import Document, DocumentError
from habit_workspace.vault.atomic_io import ConflictError
from habit_workspace.vault.format import decode, encode
from habit_workspace.vault.manager import VaultError, VaultManager


def note(*, identifier=None, body="# Olá\n\nKeep **my** Markdown.\n", **fields):
    return Document.from_metadata(
        {
            "hw": {
                "schema_version": 4,
                "kind": "note",
                "id": str(identifier or uuid4()),
                "title": "My note",
                **fields,
            }
        },
        body,
    )


def habit(identifier):
    return Document.from_metadata(
        {
            "hw": {
                "schema_version": 1,
                "kind": "habit",
                "id": str(identifier),
                "name": "Read",
                "scope": {"start": "2026-10-01", "end_exclusive": None},
                "recurrence": {"kind": "weekdays", "days": [1, 2, 3, 4, 5]},
            }
        },
        "# Read\n",
    )


def day(habit_id):
    return Document.from_metadata(
        {
            "hw": {
                "schema_version": 4,
                "kind": "day_page",
                "id": str(uuid4()),
                "date": "2026-10-29",
                "checkins": [
                    {
                        "id": str(uuid4()),
                        "habit_id": str(habit_id),
                        "date": "2026-10-29",
                        "state": "done",
                        "label_snapshot": "Read",
                        "recorded_at": "2026-10-29T12:00:00-03:00",
                    }
                ],
            }
        },
        "# My day\n\nRead even without the referenced habit.\n",
    )


@pytest.fixture
def vault(tmp_path):
    return VaultSession.create(tmp_path / "vault", "Test vault")


def test_create_reopen_and_validate(vault):
    reopened = VaultSession.open(vault.root)
    assert reopened.info.id == vault.info.id
    assert reopened.info.name == "Test vault"
    for directory in ("Pages/Days", "Items/Habits", "Layouts", "Assets", "Templates"):
        assert (vault.root / directory).is_dir()
    assert reopened.scan().documents == ()
    with pytest.raises(VaultError):
        VaultSession.create(vault.root, "Do not overwrite")
    config = vault.root / ".habit-workspace/vault.json"
    config.write_text('{"schema_version": 999}', encoding="utf-8")
    with pytest.raises(VaultError):
        VaultSession.open(vault.root)
    assert config.read_text() == '{"schema_version": 999}'


def test_roundtrip_unknown_metadata_comments_and_content(vault):
    identifier = uuid4()
    raw = (
        f"\ufeff---\r\nhw:\r\n  schema_version: 4\r\n  kind: note\r\n"
        f'  id: "{identifier}" # identity\r\n  vendor: [one, two]\r\n'
        'author: "Me"\r\n---\r\n# Olá\r\n\r\n<!-- unknown block -->\r\n  text  \r\n'
    ).encode()
    parsed = decode(raw)
    assert encode(parsed) == raw
    parsed.metadata["hw"]["title"] = "Changed"
    loaded = vault.create_document("Notes/roundtrip.md", parsed)
    reread = vault.load(identifier)
    assert reread.document.body == parsed.body
    assert reread.document.metadata["author"] == "Me"
    assert reread.document.metadata["hw"]["vendor"] == ["one", "two"]
    assert b"# identity" in loaded.path.read_bytes()


def test_rename_references_and_cache_rebuild(vault):
    target = note()
    source = note(origin_page_id=str(target.id))
    original = vault.create_document("Notes/target.md", target)
    vault.create_document("Pages/source.md", source)
    before = vault.scan()
    moved = vault.root / "Anything/renamed.md"
    moved.parent.mkdir()
    original.path.rename(moved)
    after = vault.scan()
    assert after.missing_references == ()
    assert vault.load(target.id).path == moved
    canonical = {entry.path: entry.path.read_bytes() for entry in after.documents}
    vault.index.path.unlink()
    rebuilt = VaultSession.open(vault.root).scan()
    assert {d.document.id for d in rebuilt.documents} == {d.document.id for d in before.documents}
    assert {p: p.read_bytes() for p in canonical} == canonical
    assert len(vault.index.documents()) == 2


def test_import_portability_missing_reference_then_resolution(vault, tmp_path):
    other = VaultSession.create(tmp_path / "other", "Other computer")
    identifier = uuid4()
    source = other.create_document("Pages/Days/today.md", day(identifier))
    result = ImportService(vault).import_files([source.path])
    assert len(result.imported) == 1
    assert result.imported[0].missing_references[0].target_id == identifier
    assert result.imported[0].destination.read_bytes() == source.path.read_bytes()
    assert vault.load(source.document.id).document.body == source.document.body
    definition = other.create_document("Items/Habits/read.md", habit(identifier))
    ImportService(vault).import_files([definition.path])
    assert vault.scan().missing_references == ()
    vault.index.path.unlink()
    assert VaultSession.open(vault.root).scan().missing_references == ()


def test_duplicate_import_and_conflicts(vault, tmp_path):
    source = tmp_path / "source.md"
    document = note()
    source.write_bytes(encode(document))
    importer = ImportService(vault)
    assert len(importer.import_files([source]).imported) == 1
    assert len(importer.import_files([source]).skipped) == 1
    original = vault.load(document.id).path.read_bytes()
    source.write_bytes(encode(note(identifier=document.id, body="Divergent!")))
    assert len(importer.import_files([source]).conflicting) == 1
    assert vault.load(document.id).path.read_bytes() == original
    (vault.root / "duplicate.md").write_bytes(source.read_bytes())
    report = vault.scan()
    assert len(report.conflicts) == 1
    with pytest.raises(ConflictError):
        vault.load(document.id)
    assert len(importer.import_files([source]).conflicting) == 1


@pytest.mark.parametrize(
    "raw",
    [
        b"---\nhw: [oops\n---\nDo not delete",
        b"---\nhw: !!python/object:bad {}\n---\n",
        b"---\na: &a [*a]\n---\n",
        b"---\na: 1\na: 2\n---\n",
        b"---\nhw: {}\n---\n",
        b"\xff",
        b"not a structured document",
    ],
)
def test_invalid_import_preserves_original(vault, tmp_path, raw):
    source = tmp_path / "invalid.md"
    source.write_bytes(raw)
    assert len(ImportService(vault).import_files([source]).invalid) == 1
    assert source.read_bytes() == raw
    (vault.root / "corrupt.md").write_bytes(raw)
    assert len(vault.scan().invalid) == 1
    assert (vault.root / "corrupt.md").read_bytes() == raw


def test_external_edits_and_stale_write(vault):
    loaded = vault.create_document("Notes/edit.md", note(body="Original"))
    old_stat = loaded.path.stat()
    external = loaded.path.read_bytes().replace(b"Original", b"External")
    loaded.path.write_bytes(external)
    os.utime(loaded.path, ns=(old_stat.st_atime_ns, old_stat.st_mtime_ns))
    refreshed = vault.scan()
    assert refreshed.documents[0].document.body == "External"
    with pytest.raises(ConflictError):
        vault.save(loaded, note(identifier=loaded.document.id, body="App edit"))
    assert loaded.path.read_bytes() == external
    current = vault.load(loaded.document.id)
    saved = vault.save(current, note(identifier=current.document.id, body="New edit"))
    assert saved.document.body == "New edit"
    assert any(
        p.read_bytes() == external for p in (vault.root / ".habit-workspace/backups").glob("*.md")
    )


def test_symlinks_traversal_and_existing_path_are_rejected(vault, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (vault.root / "linked").symlink_to(outside, target_is_directory=True)
    for path in (
        "../escape.md",
        str(outside / "absolute.md"),
        "linked/escape.md",
        ".habit-workspace/hidden.md",
    ):
        with pytest.raises((VaultError, DocumentError)):
            vault.create_document(path, note())
    assert not list(outside.iterdir())
    original = vault.create_document("Notes/existing.md", note())
    with pytest.raises(ConflictError):
        vault.create_document("Notes/existing.md", note())
    assert original.path.read_bytes() == encode(original.document)


def test_offline_core(vault, tmp_path, monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("Network must never be used")

    monkeypatch.setattr(socket, "socket", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)
    document = vault.create_document("Notes/offline.md", note())
    destination = VaultSession.create(tmp_path / "offline", "Offline")
    assert ImportService(destination).import_files([document.path]).imported
    destination.index.path.unlink()
    assert VaultSession.open(destination.root).load(document.document.id).document.body


def test_plain_markdown_requires_explicit_note_conversion(vault, tmp_path):
    source = tmp_path / "plain.md"
    source.write_bytes("# Plain\r\n\r\nOlá!\r\n".encode())
    assert ImportService(vault).import_files([source]).invalid
    result = ImportService(vault).import_files([source], as_note=True)
    assert result.imported
    assert vault.load(result.imported[0].document_id).document.body.encode() == source.read_bytes()


def test_nonempty_directory_not_adopted_or_overwritten(tmp_path):
    (tmp_path / "personal.md").write_text("Preserve")
    with pytest.raises(VaultError):
        VaultManager.create(tmp_path, "Personal")
    assert (tmp_path / "personal.md").read_text() == "Preserve"
