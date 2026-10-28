"""Vault identity and structural validation, independent of Qt and SQLite."""

import json
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from habit_workspace.domain.documents import DocumentError, uuid_value
from habit_workspace.vault.atomic_io import atomic_write, contained_path, read_bytes

DIRECTORIES = (
    ".habit-workspace/backups",
    "Pages/Days",
    "Pages/Weeks",
    "Pages/Months",
    "Pages/Years",
    "Items/Habits",
    "Items/Metrics",
    "Items/Tasks",
    "Items/Goals",
    "Items/Events",
    "Notes",
    "Imports",
    "Layouts",
    "Assets",
    "Templates",
)


class VaultError(DocumentError):
    """Vault could not be created or its manifest is invalid."""


@dataclass(frozen=True)
class VaultInfo:
    root: Path
    id: UUID
    name: str
    metadata: dict


def _unique_json(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise VaultError(f"Duplicate vault metadata key: {key}")
        result[key] = value
    return result


class VaultManager:
    @staticmethod
    def create(directory: Path, name: str) -> VaultInfo:
        root = Path(directory).expanduser().resolve()
        if not isinstance(name, str) or not name.strip():
            raise VaultError("A vault needs a non-empty name")
        if root.exists() and (not root.is_dir() or any(root.iterdir())):
            raise VaultError(
                "Choose a new or empty directory; existing content will not be adopted"
            )
        root.mkdir(parents=True, exist_ok=True)
        # Exclusive internal directory creation also arbitrates competing creators.
        (root / ".habit-workspace").mkdir()
        for relative in DIRECTORIES:
            contained_path(root, relative, internal=True).mkdir(parents=True, exist_ok=True)
        metadata = {"schema_version": 1, "kind": "vault", "id": str(uuid4()), "name": name}
        atomic_write(
            root / ".habit-workspace/vault.json",
            (json.dumps(metadata, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        )
        return VaultManager.open(root)

    @staticmethod
    def open(directory: Path) -> VaultInfo:
        root = Path(directory).expanduser().resolve()
        try:
            path = contained_path(root, ".habit-workspace/vault.json", internal=True)
            raw, _ = read_bytes(path, limit=64 * 1024)
            metadata = json.loads(
                raw.decode("utf-8"),
                object_pairs_hook=_unique_json,
                parse_constant=lambda value: (_ for _ in ()).throw(
                    VaultError(f"Invalid JSON constant: {value}")
                ),
            )
            if not isinstance(metadata, dict) or metadata.get("kind") != "vault":
                raise VaultError("Invalid vault manifest kind")
            if type(metadata.get("schema_version")) is not int or metadata["schema_version"] != 1:
                raise VaultError("Unsupported vault schema_version")
            identifier = uuid_value(metadata.get("id"), "vault.id")
            name = metadata.get("name")
            if not isinstance(name, str) or not name.strip():
                raise VaultError("Invalid vault name")
            # User-facing folders may be rearranged; internal paths must stay local.
            for relative in ("index.sqlite", "backups", "write.lock"):
                contained_path(root, f".habit-workspace/{relative}", internal=True)
            return VaultInfo(root, identifier, name, metadata)
        except (OSError, ValueError, RecursionError) as error:
            raise VaultError(f"Cannot open vault {root}: {error}") from error
