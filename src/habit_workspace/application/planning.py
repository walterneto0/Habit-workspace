"""Revision-aware planning writes and no-I/O projections of canonical scans."""

from copy import deepcopy
from datetime import date, datetime, timedelta
from typing import Any, Literal
from uuid import uuid4

from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.documents import Document, require
from habit_workspace.domain.habits import normalize_tags
from habit_workspace.domain.layouts.components import Component
from habit_workspace.domain.planning import goal_home, planning_from_mapping
from habit_workspace.domain.temporal import PeriodRef, TemporalScope
from habit_workspace.vault.scanner import LoadedDocument, ScanReport


class PlanningService:
    def __init__(self, session: VaultSession):
        self.session = session

    def create(
        self,
        *,
        kind: Literal["task", "goal"],
        title: str,
        period: PeriodRef,
        body: str = "",
        scope: TemporalScope | None = None,
        tags: tuple[str, ...] = (),
        **fields: Any,
    ) -> LoadedDocument:
        require(kind in ("task", "goal"), "Expected task or goal")
        scope = scope or period.scope
        hw = dict(
            schema_version=4,
            kind=kind,
            id=str(uuid4()),
            title=title,
            scope=dict(
                start=scope.start.isoformat(),
                end_exclusive=scope.end_exclusive.isoformat() if scope.end_exclusive else None,
            ),
            tags=list(normalize_tags(tags)),
            status="pending" if kind == "task" else "not_started",
        )
        if "origin_page_id" not in fields:
            from habit_workspace.application.layouts import period_page

            page = period_page(self.session.report, period)
            if page:
                hw["origin_page_id"] = str(page.document.id)
        if kind == "goal":
            hw["home_period_ref"] = str(period)
            hw["tracking"] = {"mode": "home_only"}
        hw.update(self._fields(fields))
        document = Document.from_metadata({"hw": hw}, body)
        folder = "Tasks" if kind == "task" else "Goals"
        return self.session.create_document(f"Items/{folder}/{document.id}.md", document)

    @staticmethod
    def _fields(fields: dict[str, Any]) -> dict[str, Any]:
        allowed = {
            "due_date",
            "status",
            "completed_at",
            "progress_percent",
            "origin_page_id",
            "home_period_ref",
            "tracking",
        }
        require(set(fields) <= allowed, "Unknown planning fields")
        return {
            k: v.isoformat()
            if isinstance(v, (date, datetime))
            else str(v)
            if k == "origin_page_id" and v
            else v
            for k, v in fields.items()
        }

    def update(
        self,
        loaded: LoadedDocument,
        *,
        title: str | None = None,
        body: str | None = None,
        scope: TemporalScope | None = None,
        tags: tuple[str, ...] | None = None,
        **fields: Any,
    ) -> LoadedDocument:
        planning_from_mapping(loaded.document.metadata["hw"])
        document = deepcopy(loaded.document)
        hw = document.metadata["hw"]
        if title is not None:
            hw["title"] = title
        if body is not None:
            document.body = body
        if tags is not None and tuple(normalize_tags(tags)) != tuple(
            normalize_tags(tuple(hw.get("tags", ())))
        ):
            hw["tags"] = list(normalize_tags(tags))
        if scope is not None:
            hw["scope"].update(
                start=scope.start.isoformat(),
                end_exclusive=scope.end_exclusive.isoformat() if scope.end_exclusive else None,
            )
        if "tracking" in fields:
            incoming = fields["tracking"]
            if isinstance(incoming, dict):
                merged = dict(hw.get("tracking", {})) | incoming
                if incoming.get("mode") == "home_only":
                    merged.pop("granularity", None)
                fields["tracking"] = merged
        hw.update(self._fields(fields))
        return self.session.save(loaded, document)

    def followup(self, loaded, period, commentary):
        item = planning_from_mapping(loaded.document.metadata["hw"])
        require(item.kind == "goal", "Expected goal")
        require(isinstance(commentary, str), "Commentary must be Markdown")
        doc = deepcopy(loaded.document)
        hw = doc.metadata["hw"]
        records = hw.setdefault("followups", [])
        record = next((r for r in records if r["period"] == str(period)), None)
        if record is None:
            tracking = hw.get("tracking", {})
            require(
                tracking.get("mode") == "periodic" and tracking.get("granularity") == period.scale,
                "Período incompatível com acompanhamento.",
            )
            require(item.scope.intersects(period.scope), "Período fora do escopo.")
            record = dict(id=str(uuid4()), goal_id=str(item.id), period=str(period))
            records.append(record)
        record["commentary"] = commentary
        return self.session.save(loaded, doc)

    def complete(self, loaded: LoadedDocument, completed: bool, now: datetime) -> LoadedDocument:
        require(type(completed) is bool, "Completion must be boolean")
        item = planning_from_mapping(loaded.document.metadata["hw"])
        require(item.kind == "task", "Only tasks can be completed")
        status = "completed" if completed else "pending"
        # Even no-ops go through revision checking, retaining the original timestamp.
        return self.update(
            loaded,
            status=status,
            completed_at=(item.completed_at if item.status == status else now)
            if completed
            else None,
        )


def query_report(
    report: ScanReport, period: PeriodRef | None, today: date, query: str = ""
) -> list[dict[str, Any]]:
    """Current state in a historical context; no fabricated status history."""
    duplicates = {c.document_id for c in report.conflicts}
    rows = []
    for loaded in report.documents:
        doc = loaded.document
        if doc.kind not in ("task", "goal"):
            continue
        item = planning_from_mapping(doc.metadata["hw"])
        if (
            query.casefold()
            not in " ".join(
                (
                    item.title,
                    doc.body,
                    *item.tags,
                    str(item.id),
                    *(r["commentary"] for r in doc.metadata["hw"].get("followups", [])),
                )
            ).casefold()
        ):
            continue
        start, end = item.scope.start, item.scope.end_exclusive
        intersects = period is None or (
            start < period.scope.end_exclusive and (end is None or end > period.start)
        )
        home = None
        if item.kind == "goal":
            home = goal_home(doc.metadata["hw"], item.scope)
            tracking = doc.metadata["hw"].get("tracking", {})
            followup = bool(
                period
                and period != home
                and (
                    (
                        tracking.get("mode") == "periodic"
                        and tracking.get("granularity") == period.scale
                        and item.scope.intersects(period.scope)
                    )
                    or any(
                        r["period"] == str(period) for r in doc.metadata["hw"].get("followups", [])
                    )
                )
            )
            intersects = period is None or period == home or followup
        deadline = bool(period and item.due_date and period.start <= item.due_date <= period.end)
        overdue = (
            item.kind == "task"
            and item.status == "pending"
            and item.due_date is not None
            and item.due_date < today
        )
        carry = (
            item.kind == "task"
            and item.status == "pending"
            and end is not None
            and end <= (period.start if period else today)
        )
        current = period is None or period.start <= today <= period.end
        if not (intersects or deadline or (current and (carry or overdue))):
            continue
        category = (
            "Do período"
            if period
            and start >= period.start
            and end is not None
            and end <= period.scope.end_exclusive
            else "Contextual · escopo mais amplo"
        )
        if period is None:
            category = "Pendente de período anterior" if carry else "Todos os períodos"
        if not intersects:
            category = "Prazo neste período" if deadline else "Pendente de período anterior"
        if item.kind == "goal" and home is None:
            category = "Objetivo legado · período não definido"
        if item.kind == "goal" and period and followup:
            category = (
                "Acompanhamento "
                + {"month": "mensal", "week": "semanal", "day": "diário"}[period.scale]
                + " do objetivo"
            )
        display_start, display_end = start, end
        if item.kind == "goal" and period and followup:
            eligible = item.scope.intersection(period.scope)
            if eligible:
                display_start, display_end = eligible.start, eligible.end_exclusive
        rows.append(
            dict(
                home_period_ref=str(home) if home else "",
                followup_period=str(period) if item.kind == "goal" and period and followup else "",
                id=str(item.id),
                kind=item.kind,
                title=item.title,
                body=doc.body,
                tags=", ".join(item.tags),
                start=start.isoformat(),
                end=(end.isoformat() if end else ""),
                scope=(
                    f"{display_start.isoformat()} → "
                    + (
                        (display_end - timedelta(days=1)).isoformat() + " (inclusivo)"
                        if display_end
                        else "sem término"
                    )
                ),
                status=item.status,
                progress=item.progress_percent,
                due=item.due_date.isoformat() if item.due_date else "",
                overdue=overdue,
                category=category,
                conflict=item.id in duplicates,
                token=loaded.revision.digest,
            )
        )
    return sorted(rows, key=lambda r: (not r["overdue"], r["kind"], r["title"].casefold(), r["id"]))


def block_rows(
    block: Component, report: ScanReport, period: PeriodRef | None, today: date | None
) -> list[dict[str, Any]]:
    """Task projections for existing lists/checklists, with visible unresolved IDs."""
    if block.type not in ("list", "checklist"):
        return []
    today = today or date.today()
    selection = getattr(block.config, "selection", None)
    binding = block.binding
    if binding and binding.kind != "task":
        return []
    if not binding and (selection is None or "task" not in selection.value_types):
        return []
    all_rows = query_report(report, None, today)
    by_id = {r["id"]: r for r in all_rows if r["kind"] == "task"}
    if binding or selection.mode == "manual":
        ids = (binding.source_id,) if binding else selection.source_ids
        known_other = {str(d.document.id) for d in report.documents if d.document.kind != "task"}
        rows = []
        for identifier in ids:
            key = str(identifier)
            if not binding and key in known_other:
                continue
            rows.append(
                by_id.get(
                    key,
                    dict(
                        id=key,
                        kind="task",
                        title="Referência indisponível · " + key,
                        conflict=True,
                        status="",
                        category="",
                        scope="",
                        token="",
                    ),
                )
            )
        return rows
    rows = [r for r in query_report(report, period, today) if r["kind"] == "task"]
    return [
        r
        for r in rows
        if selection.mode != "by_tags" or set(selection.tags).intersection(r["tags"].split(", "))
    ]
