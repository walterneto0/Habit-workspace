"""Read-only first contract for selective transfer; never authorizes copying."""

from uuid import uuid4

import pytest

from habit_workspace.application.transfer_plan import plan_documents
from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.documents import Document, DocumentError
from habit_workspace.vault.scanner import scan


def note(identifier, origin=None, body="Keep this text"):
    fields = dict(schema_version=4, kind="note", id=str(identifier), title="Note")
    if origin:
        fields["origin_page_id"] = str(origin)
    return Document.from_metadata({"hw": fields}, body)


def test_transitive_cycle_selection_and_no_writes(tmp_path):
    source = VaultSession.create(tmp_path / "source", "Source")
    target = VaultSession.create(tmp_path / "target", "Target")
    a, b, unrelated = uuid4(), uuid4(), uuid4()
    source.create_document("a.md", note(a, b))
    source.create_document("b.md", note(b, a))
    source.create_document("unrelated.md", note(unrelated))
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    plan = plan_documents(scan(source.root), scan(target.root), [a])
    assert [(e.identifier, e.selected, e.status) for e in plan] == [
        (a, True, "new"),
        (b, False, "new"),
    ]
    assert {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before


def test_missing_duplicate_and_destination_conflict(tmp_path):
    source = VaultSession.create(tmp_path / "source", "Source")
    target = VaultSession.create(tmp_path / "target", "Target")
    a, missing = uuid4(), uuid4()
    loaded = source.create_document("a.md", note(a, missing))
    target.create_document("same.md", note(a, missing))
    assert [e.status for e in plan_documents(scan(source.root), scan(target.root), [a])] == [
        "identical",
        "missing",
    ]
    (target.root / "same.md").write_bytes(loaded.path.read_bytes() + b"\nChanged")
    assert plan_documents(scan(source.root), scan(target.root), [a])[0].status == "conflict"
    (source.root / "duplicate.md").write_bytes(loaded.path.read_bytes())
    assert plan_documents(scan(source.root), scan(target.root), [a])[0].status == "ambiguous"


def test_empty_and_bounded_dependency_walk(tmp_path):
    source = VaultSession.create(tmp_path / "source", "Source")
    target = VaultSession.create(tmp_path / "target", "Target")
    a, b = uuid4(), uuid4()
    source.create_document("a.md", note(a, b))
    with pytest.raises(DocumentError):
        plan_documents(scan(source.root), scan(target.root), [])
    with pytest.raises(DocumentError):
        plan_documents(scan(source.root), scan(target.root), [a], limit=1)
