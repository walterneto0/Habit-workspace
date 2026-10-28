"""Canonical metric records and bounded source/record queries, without analytics/UI.

Queries return only actual observations. They never materialize expected failures.
Weekly values have explicit attribution or are returned separately for disclosure.
"""

from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID, uuid4

from habit_workspace.application.layouts import period_page
from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.documents import Document, DocumentError
from habit_workspace.domain.metrics import FieldDefinition, Observation, SourceSelection, aware
from habit_workspace.domain.temporal import PeriodRef
from habit_workspace.vault.atomic_io import ConflictError, writer_lock
from habit_workspace.vault.metrics import (
    field_document,
    field_from_mapping,
    observation_from_mapping,
    observation_mapping,
)
from habit_workspace.vault.scanner import LoadedDocument, ScanReport, scan


@dataclass(frozen=True)
class MetricQuery:
    period: PeriodRef
    sources: tuple[FieldDefinition, ...]
    records: tuple[Observation, ...]
    eligible_from: tuple[tuple[UUID, date], ...]
    unresolved_records: tuple[Observation, ...] = ()
    separate_weekly: tuple[Observation, ...] = ()
    missing_source_ids: tuple[UUID, ...] = ()
    issues: tuple[str, ...] = ()
    index_error: str | None = None


def _fields(report: ScanReport) -> dict[UUID, FieldDefinition]:
    result = {}
    for d in report.documents:
        if d.document.kind != "metric_definition":
            continue
        if any(c.document_id == d.document.id for c in report.conflicts):
            raise ConflictError(f"Ambiguous metric {d.document.id}")
        result[d.document.id] = field_from_mapping(d.document.metadata["hw"])
    return result


def _records(
    report: ScanReport, fields: dict[UUID, FieldDefinition]
) -> tuple[tuple[Observation, ...], tuple[str, ...]]:
    records, issues = [], []
    ids = {d.document.id for d in report.documents}
    ids.update(d.layout.id for d in report.layouts)
    ids.update(d.id for d in report.defaults)
    ids.update(
        UUID(r["id"])
        for d in report.documents
        for r in d.document.metadata["hw"].get("checkins", [])
    )
    keys = set()
    for loaded in report.documents:
        for raw in loaded.document.metadata["hw"].get("observations", []):
            # Legacy arbitrary values remain readable in the document; unsupported
            # typed projections are disclosed and never rewritten by a query.
            try:
                record = observation_from_mapping(raw)
            except DocumentError as error:
                issues.append(f"{loaded.path}: {error}")
                continue
            period_page(report, PeriodRef.containing("day", record.observed_date))
            source = fields.get(record.field_id)
            key = (
                record.field_id,
                str(record.source_period_ref)
                if source and source.temporal_policy == "weekly"
                else record.observed_date,
            )
            if (
                record.id in ids
                or key in keys
                or any(c.document_id == loaded.document.id for c in report.conflicts)
            ):
                raise ConflictError(
                    f"Ambiguous observation {record.field_id} on {record.observed_date}"
                )
            ids.add(record.id)
            keys.add(key)
            records.append(record)
    return tuple(records), tuple(issues)


class MetricService:
    def __init__(self, session: VaultSession):
        self.session = session

    def create(self, field: FieldDefinition, *, body: str = "") -> LoadedDocument:
        return self.session.create_document(
            f"Items/Metrics/{field.id}.md", field_document(field, body=body)
        )

    def record(self, observation: Observation) -> LoadedDocument:
        """One effective observation per field/day (per source week for weekly fields).

        Same UUID/content retries are no-ops; corrections must be explicit future
        operations. No habit check-in can be written through this metric API.
        """
        with writer_lock(self.session.root):
            report = scan(self.session.root)
            fields = _fields(report)
            field = fields.get(observation.field_id)
            if field is None:
                raise DocumentError("Observation references a missing metric definition")
            observation.validate_field(field)
            records, issues = _records(report, fields)
            if issues:
                raise DocumentError(
                    "Resolve unsupported observation data before recording: " + "; ".join(issues)
                )
            for loaded in report.documents:
                hw = loaded.document.metadata["hw"]
                if loaded.document.id == observation.id or any(
                    r["id"] == str(observation.id) for r in hw.get("checkins", [])
                ):
                    raise ConflictError("Observation UUID collides with existing data")
            for existing in records:
                if existing.id == observation.id:
                    if existing != observation:
                        raise ConflictError("Observation UUID already has different content")
                    page = period_page(report, PeriodRef.containing("day", existing.observed_date))
                    if page is None:
                        raise DocumentError("Canonical observation page is missing")
                    return page
                same_key = existing.field_id == field.id and (
                    existing.source_period_ref == observation.source_period_ref
                    if field.temporal_policy == "weekly"
                    else existing.observed_date == observation.observed_date
                )
                if same_key:
                    raise ConflictError(
                        "Canonical field observation already exists; "
                        "do not duplicate across layouts"
                    )
            period = PeriodRef.containing("day", observation.observed_date)
            page = period_page(report, period)
            if page:
                document = deepcopy(page.document)
                document.metadata["hw"].setdefault("observations", []).append(
                    observation_mapping(observation)
                )
                result = self.session.repository.save(page, document)
            else:
                document = Document.from_metadata(
                    {
                        "hw": {
                            "schema_version": 4,
                            "kind": "day_page",
                            "id": str(uuid4()),
                            "date": observation.observed_date.isoformat(),
                            "observations": [observation_mapping(observation)],
                        }
                    },
                    "",
                )
                result = self.session.repository.create(f"Pages/Days/{document.id}.md", document)
            self.session.scan()
            return result

    def query(
        self, period: PeriodRef, selection: SourceSelection, *, as_of: datetime
    ) -> MetricQuery:
        report = self.session.scan()
        return self.query_report(
            report, period, selection, as_of=as_of, index_error=self.session.index_error
        )

    @staticmethod
    def query_report(
        report: ScanReport,
        period: PeriodRef,
        selection: SourceSelection,
        *,
        as_of: datetime,
        index_error: str | None = None,
    ) -> MetricQuery:
        aware(as_of)
        fields = _fields(report)
        all_records, parse_issues = _records(report, fields)
        sources = tuple(
            sorted(
                (
                    f
                    for f in fields.values()
                    if selection.matches(f)
                    and f.active_from <= as_of
                    and f.active_from.date() <= period.end
                ),
                key=lambda f: str(f.id),
            )
        )
        selected = {f.id for f in sources}
        records, unresolved, separate = [], [], []
        issues = list(parse_issues) + [f"{i.path}: {i.message}" for i in report.invalid]
        for record in all_records:
            if record.recorded_at > as_of:
                continue
            source = fields.get(record.field_id)
            if source is None:
                if period.start <= record.observed_date <= period.end:
                    unresolved.append(record)
                continue
            # Explicit historical entries remain discoverable, even in earlier months.
            if (
                selection.matches(source)
                and source.active_from <= as_of
                and record.historical_entry
                and period.start <= record.observed_date <= period.end
            ):
                selected.add(source.id)
            if record.field_id not in selected:
                continue
            try:
                record.validate_field(source)
            except ValueError as error:
                issues.append(f"Observation {record.id}: {error}")
                unresolved.append(record)
                continue
            attributed_date = record.observed_date
            if source.temporal_policy == "weekly":
                week = record.source_period_ref
                if source.weekly_attribution == "separate":
                    if week.intersects(period):
                        separate.append(record)
                    continue
                if source.weekly_attribution == "start":
                    attributed_date = week.start
                elif source.weekly_attribution == "end":
                    attributed_date = week.end
            if period.start <= attributed_date <= period.end:
                records.append(record)
        sources = tuple(sorted((fields[i] for i in selected), key=lambda f: str(f.id)))
        missing = tuple(v for v in selection.source_ids if v not in fields)
        issues.extend(
            f"Manual source {v} is missing or is not a metric; habit queries use HabitService"
            for v in missing
        )
        eligible = tuple(
            (f.id, max(period.start, f.active_from.date()))
            for f in sources
            if f.active_from.date() <= period.end
        )

        def key(r: Observation):
            return r.observed_date, str(r.id)

        return MetricQuery(
            period,
            sources,
            tuple(sorted(records, key=key)),
            eligible,
            tuple(sorted(unresolved, key=key)),
            tuple(sorted(separate, key=key)),
            missing,
            tuple(issues),
            index_error,
        )
