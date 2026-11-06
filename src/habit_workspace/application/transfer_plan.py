"""Read-only Markdown dependency planning, not a copy-ready transfer preflight.

Reports are snapshots. Copying must later revalidate paths, bytes, locks, assets,
layout revisions and vault identities. This module never performs IO.
"""

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from habit_workspace.domain.documents import DocumentError
from habit_workspace.vault.scanner import ScanReport


@dataclass(frozen=True)
class DocumentCandidate:
    identifier: UUID
    selected: bool
    status: Literal["new", "identical", "conflict", "missing", "ambiguous", "unsupported"]
    version: int | None = None


def plan_documents(
    source: ScanReport, destination: ScanReport, selected: list[UUID], *, limit: int = 256
) -> tuple[DocumentCandidate, ...]:
    """Discover references without auto-selecting dependencies or resolving conflicts."""
    if not selected or not 1 <= limit <= 256:
        raise DocumentError("Select documents and use a limit between 1 and 256")
    roots = set(selected)
    pending = deque((identifier, None) for identifier in dict.fromkeys(selected))
    seen, result = set(), []
    sources, targets = defaultdict(list), defaultdict(list)
    for loaded in source.documents:
        sources[loaded.document.id].append(loaded)
    for loaded in destination.documents:
        targets[loaded.document.id].append(loaded)
    source_conflicts = {c.document_id for c in source.conflicts}
    target_conflicts = {c.document_id for c in destination.conflicts}
    target_other_ids = {d.layout.id for d in destination.layouts} | {
        d.id for d in destination.defaults
    }
    while pending:
        identifier, version = pending.popleft()
        key = identifier, version
        if key in seen:
            continue
        if len(seen) >= limit:
            raise DocumentError("Dependency limit exceeded; no complete plan produced")
        seen.add(key)
        matches, existing = sources[identifier], targets[identifier]
        if version is not None:
            status = "unsupported"
        elif identifier in source_conflicts or len(matches) > 1:
            status = "ambiguous"
        elif not matches:
            status = "missing"
        else:
            if identifier in target_conflicts or identifier in target_other_ids:
                status = "conflict"
            elif not existing:
                status = "new"
            elif len(existing) == 1 and existing[0].revision.digest == matches[0].revision.digest:
                status = "identical"
            else:
                status = "conflict"
            pending.extend((r.target_id, r.version) for r in matches[0].document.references())
        result.append(
            DocumentCandidate(identifier, identifier in roots and version is None, status, version)
        )
    return tuple(result)
