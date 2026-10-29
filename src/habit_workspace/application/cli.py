"""Temporary diagnostic interface, not the future user-facing page renderer."""

import argparse
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from uuid import uuid4

from habit_workspace.application.imports import ImportService
from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.documents import Document, DocumentError
from habit_workspace.vault.atomic_io import inspect_lock, recover_lock
from habit_workspace.vault.manager import VaultManager


def configure(parser: argparse.ArgumentParser) -> None:
    commands = parser.add_subparsers(dest="vault_command", required=True)
    for name in (
        "create",
        "open",
        "scan",
        "reindex",
        "import",
        "show",
        "new-note",
        "lock-status",
        "unlock",
    ):
        command = commands.add_parser(name)
        command.add_argument(
            "directory", type=Path, help="Explicit vault folder; no default location"
        )
        if name == "create":
            command.add_argument("--name", default="Habit Workspace")
        elif name == "import":
            command.add_argument("sources", type=Path, nargs="+")
            command.add_argument(
                "--as-note",
                action="store_true",
                help="Wrap plain Markdown as a new note; never repair invalid YAML",
            )
        elif name == "show":
            command.add_argument("id")
        elif name == "new-note":
            command.add_argument("--title", required=True)
            command.add_argument("--body", default="")
        elif name == "unlock":
            command.add_argument(
                "--token",
                required=True,
                help="Token printed by lock-status; recovery is refused unless verified stale",
            )


def _default(value):
    return asdict(value) if is_dataclass(value) else str(value)


def emit(value) -> None:
    print(json.dumps(value, default=_default, ensure_ascii=False, indent=2))


def lock_report(status) -> dict:
    if status is None:
        return {"locked": False}
    return {
        "locked": True,
        "path": status.path,
        "owner": status.owner,
        "entries": status.entries,
        "age_seconds": round(status.age_seconds) if status.age_seconds is not None else None,
        "same_machine": status.same_machine,
        "process": status.process,
        "verified_stale": status.stale,
        "diagnosis": status.describe(),
    }


def run(args: argparse.Namespace) -> int:
    try:
        if args.vault_command in ("lock-status", "unlock"):
            # Read-only diagnosis first; never scans, indexes or edits documents.
            root = VaultManager.open(args.directory).root
            if args.vault_command == "lock-status":
                emit(lock_report(inspect_lock(root)))
                return 0
            emit({"recovered": lock_report(recover_lock(root, args.token))})
            return 0
        session = (
            VaultSession.create(args.directory, args.name)
            if args.vault_command == "create"
            else VaultSession.open(args.directory)
        )
        if args.vault_command == "import":
            result = ImportService(session).import_files(args.sources, as_note=args.as_note)
            emit(result)
            return 1 if result.invalid or result.conflicting or result.index_error else 0
        if args.vault_command == "new-note":
            document = Document.from_metadata(
                {
                    "hw": {
                        "schema_version": 4,
                        "kind": "note",
                        "id": str(uuid4()),
                        "title": args.title,
                    }
                },
                args.body,
            )
            loaded = session.create_document(f"Notes/{document.id}.md", document)
            emit({"id": document.id, "path": loaded.path, "index_error": session.index_error})
            return 0
        if args.vault_command == "show":
            loaded = session.load(args.id)
            emit(
                {
                    "id": loaded.document.id,
                    "path": loaded.path,
                    "metadata": loaded.document.metadata,
                    "body": loaded.document.body,
                    "missing_references": [
                        r for r in session.report.missing_references if r.source_path == loaded.path
                    ],
                    "index_error": session.index_error,
                }
            )
            return 0
        report = session.report
        emit(
            {
                "vault": session.info,
                "documents": [
                    {
                        "id": d.document.id,
                        "kind": d.document.kind,
                        "title": d.document.title,
                        "schema_version": d.document.schema_version,
                        "path": d.path,
                    }
                    for d in report.documents
                ],
                "invalid": report.invalid,
                "conflicts": report.conflicts,
                "missing_references": report.missing_references,
                "index_error": session.index_error,
            }
        )
        return 1 if report.invalid or report.conflicts or session.index_error else 0
    except (DocumentError, OSError, ValueError) as error:
        emit({"error": str(error)})
        return 1
