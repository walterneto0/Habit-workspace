"""Reference lookup must stay conservative while scaling with files + references."""

from dataclasses import replace
from uuid import uuid4

from test_vault import note

from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.documents import Reference
from habit_workspace.vault.scanner import ReferenceLookup, reference_problem


def test_lookup_retains_missing_wrong_kind_and_duplicate_diagnostics(tmp_path):
    session = VaultSession.create(tmp_path / "vault", "References")
    loaded = session.create_document("note.md", note())
    report = session.report
    lookup = ReferenceLookup(report)
    for role in ("habit_id", "field_id", "note_id", "source_id", "origin_page_id", "layout_id"):
        for identifier in (loaded.document.id, uuid4()):
            ref = Reference(identifier, role, 1 if role == "layout_id" else None)
            assert lookup.problem(ref) == reference_problem(report, ref)
    (session.root / "duplicate.md").write_bytes(loaded.path.read_bytes())
    report = session.scan()
    lookup = ReferenceLookup(report)
    assert (
        lookup.problem(Reference(loaded.document.id, "note_id")) == "Referenced UUID is ambiguous"
    )
    # Even if the caller supplies an incomplete conflict list, never choose a winner.
    lookup = ReferenceLookup(replace(report, conflicts=()))
    assert lookup.problem(Reference(loaded.document.id, "note_id"))


def test_lookup_does_not_revisit_all_documents_for_each_reference(tmp_path, monkeypatch):
    from habit_workspace.domain.documents import Document

    session = VaultSession.create(tmp_path / "vault", "References")
    loaded = session.create_document("note.md", note())
    lookup = ReferenceLookup(session.report)
    identifier = loaded.document.id

    def forbidden(_):
        raise AssertionError("identity must be resolved once, not for every reference")

    monkeypatch.setattr(Document, "id", property(forbidden))
    for _ in range(100):
        assert lookup.problem(Reference(identifier, "note_id")) is None
