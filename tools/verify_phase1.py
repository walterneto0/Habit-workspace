"""Repeatable portability demonstration using only generated temporary data."""

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from habit_workspace.application.imports import ImportService
from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.documents import Document


def main() -> None:
    with TemporaryDirectory(prefix="habit-workspace-phase1-") as directory:
        base = Path(directory)
        source = VaultSession.create(base / "computer-a", "Computer A")
        target = VaultSession.create(base / "computer-b", "Computer B")
        identifier = uuid4()
        document = Document.from_metadata(
            {
                "hw": {
                    "schema_version": 4,
                    "kind": "note",
                    "id": str(identifier),
                    "title": "Portable note",
                    "extension": {"preserve": True},
                }
            },
            "# Portable note\n\nOlá — owned by the user.\n",
        )
        original = source.create_document("Notes/portable.md", document)
        imported = ImportService(target).import_files([original.path])
        assert len(imported.imported) == 1
        received = target.load(identifier)
        assert received.path.read_bytes() == original.path.read_bytes()
        renamed = target.root / "Reorganized/renamed.md"
        renamed.parent.mkdir()
        received.path.rename(renamed)
        assert target.load(identifier).path == renamed
        raw = renamed.read_bytes()
        target.index.path.unlink()
        target = VaultSession.open(target.root)
        assert target.load(identifier).path.read_bytes() == raw
        assert len(target.index.documents()) == 1
        renamed.write_bytes(raw + b"\nEdited externally.\n")
        assert target.load(identifier).document.body.endswith("Edited externally.\n")
        print(
            json.dumps(
                {
                    "result": "PASS",
                    "temporary_vaults": 2,
                    "import_preserved_bytes": True,
                    "uuid_preserved_after_rename": str(identifier),
                    "index_deleted_and_rebuilt": True,
                    "canonical_sha256_before_and_after_rebuild": hashlib.sha256(raw).hexdigest(),
                    "external_edit_refreshed": True,
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
