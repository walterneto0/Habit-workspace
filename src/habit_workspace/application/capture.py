"""Canonical daily capture: habit check-ins and typed field observations.

A habit-bound control writes only ``checkins`` (keyed by habit_id/date); a field-bound
control writes only ``observations`` (keyed by field_id/observed_date). Both live in
the day's canonical page. Writes are upserts: repeating the same value is a no-op,
a different value revises the same record UUID, and clearing removes the record.
Callers pass the value they displayed as ``expected``; a mismatch means the file
changed (for example, an external edit) and nothing is written.

Never writes future records, unscheduled check-ins, or pre-activation observations,
and never infers ``missed``. Missing or out-of-schedule records stay untouched.
"""

import math
import re
from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import date, datetime, time
from typing import Any
from uuid import UUID, uuid4

from habit_workspace.application.layouts import period_page
from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.documents import Document, DocumentError
from habit_workspace.domain.habits import Habit
from habit_workspace.domain.layouts import ChecklistConfig, Component, InputConfig
from habit_workspace.domain.metrics import FieldDefinition, Scalar, aware
from habit_workspace.domain.temporal import PeriodRef
from habit_workspace.vault.atomic_io import ConflictError, writer_lock
from habit_workspace.vault.habits import habit_from_document
from habit_workspace.vault.metrics import field_from_mapping, observation_from_mapping
from habit_workspace.vault.scanner import LoadedDocument, ScanReport, scan

CHECKIN_STATES = ("done", "skipped", "missed")
UNCHECKED: Any = object()


@dataclass(frozen=True)
class CaptureResult:
    action: str  # created, updated, cleared, unchanged
    page: LoadedDocument | None
    record: dict | None


@dataclass(frozen=True)
class HabitCell:
    habit_id: UUID
    name: str
    state: str  # done/skipped/missed, or not_scheduled/future/pending/unrecorded
    recorded: str | None
    editable: bool
    note: str = ""


@dataclass(frozen=True)
class FieldCell:
    field_id: UUID
    name: str
    value_type: str
    value: Scalar | None
    editable: bool
    note: str = ""
    unit: str | None = None
    options: tuple[str, ...] = ()
    minimum: float | None = None
    maximum: float | None = None


def parse_value(field: FieldDefinition, raw: str) -> Scalar:
    """Strict text-to-typed conversion for GUI input; validation stays in the domain."""
    text = raw.strip()
    if field.value_type == "text":
        value: Scalar = raw
    elif not text:
        raise ValueError("Informe um valor ou use Limpar")
    elif field.value_type == "boolean":
        if text.casefold() not in ("true", "false"):
            raise ValueError("Use verdadeiro ou falso")
        value = text.casefold() == "true"
    elif field.value_type == "integer":
        if not re.fullmatch(r"[+-]?\d{1,15}", text):
            raise ValueError("Informe um número inteiro")
        value = int(text)
    elif field.value_type in ("number", "duration", "rating"):
        normalized = text.replace(",", ".")
        if not re.fullmatch(r"[+-]?(\d{1,15}(\.\d*)?|\.\d+)", normalized):
            raise ValueError("Informe um número (use vírgula ou ponto decimal)")
        number = float(normalized)
        value = int(number) if re.fullmatch(r"[+-]?\d+", normalized) else number
        if not math.isfinite(number):
            raise ValueError("Número inválido")
    elif field.value_type == "date":
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            raise ValueError("Use AAAA-MM-DD")
        value = date.fromisoformat(text).isoformat()
    elif field.value_type == "time":
        if not re.fullmatch(r"\d{2}:\d{2}(:\d{2})?", text):
            raise ValueError("Use HH:MM")
        value = time.fromisoformat(text).isoformat(timespec="minutes")
    else:
        value = text
    field.validate_value(value)
    return value


def habits_in(report: ScanReport) -> dict[UUID, Habit]:
    conflicts = {c.document_id for c in report.conflicts}
    result = {}
    for loaded in report.documents:
        if loaded.document.kind == "habit":
            if loaded.document.id in conflicts:
                raise ConflictError(f"Ambiguous habit UUID: {loaded.document.id}")
            result[loaded.document.id] = habit_from_document(loaded.document)
    return result


def fields_in(report: ScanReport) -> dict[UUID, FieldDefinition]:
    conflicts = {c.document_id for c in report.conflicts}
    result = {}
    for loaded in report.documents:
        if loaded.document.kind == "metric_definition":
            if loaded.document.id in conflicts:
                raise ConflictError(f"Ambiguous metric UUID: {loaded.document.id}")
            result[loaded.document.id] = field_from_mapping(loaded.document.metadata["hw"])
    return result


def _matching(records: list, key: str, target: UUID) -> list[dict]:
    return [r for r in records if r.get(key) == str(target)]


def _record_ids(report: ScanReport) -> set[str]:
    ids = {str(d.document.id) for d in report.documents}
    ids.update(str(d.layout.id) for d in report.layouts)
    ids.update(str(d.id) for d in report.defaults)
    for loaded in report.documents:
        hw = loaded.document.metadata["hw"]
        ids.update(r["id"] for r in (*hw.get("checkins", ()), *hw.get("observations", ())))
    return ids


def _new_id(report: ScanReport) -> UUID:
    used = _record_ids(report)
    while str(identifier := uuid4()) in used:
        pass
    return identifier


class CaptureService:
    def __init__(self, session: VaultSession):
        self.session = session

    def _write_day(self, report: ScanReport, day: date, collection: str, records: list):
        page = period_page(report, PeriodRef.containing("day", day))
        if page is not None:
            document = deepcopy(page.document)
            if records:
                document.metadata["hw"][collection] = records
            else:
                document.metadata["hw"].pop(collection, None)
            return self.session.repository.save(page, document)
        document = Document.from_metadata(
            {
                "hw": {
                    "schema_version": 4,
                    "kind": "day_page",
                    "id": str(_new_id(report)),
                    "date": day.isoformat(),
                    collection: records,
                }
            },
            "",
        )
        return self.session.repository.create(f"Pages/Days/{document.id}.md", document)

    def set_checkin(
        self,
        habit_id: UUID,
        day: date,
        state: str | None,
        *,
        today: date,
        recorded_at: datetime,
        expected: str | None = UNCHECKED,
    ) -> CaptureResult:
        """state None clears the explicit record; absence is shown as unrecorded."""
        aware(recorded_at)
        if type(day) is not date or type(today) is not date:
            raise ValueError("Capture needs civil dates")
        if state is not None and state not in CHECKIN_STATES:
            raise DocumentError("Estado de check-in não suportado")
        if day > today:
            raise DocumentError("Datas futuras não recebem check-in")
        with writer_lock(self.session.root):
            report = scan(self.session.root)
            habit = habits_in(report).get(habit_id)
            if habit is None:
                raise DocumentError("Hábito ausente ou inválido; nada foi registrado")
            if not habit.is_scheduled(day):
                raise DocumentError(
                    "O hábito não está programado nesta data; registros existentes são preservados"
                )
            page = period_page(report, PeriodRef.containing("day", day))
            records = deepcopy(page.document.metadata["hw"].get("checkins", [])) if page else []
            current = _matching(records, "habit_id", habit_id)
            existing = current[0] if current else None
            if expected is not UNCHECKED and (existing or {}).get("state") != expected:
                raise ConflictError(
                    "O registro mudou desde a exibição (edição externa?). Revise e tente novamente."
                )
            if (existing or {}).get("state") == state:
                return CaptureResult("unchanged", page, existing)
            if state is None:
                records.remove(existing)
                action, record = "cleared", None
            elif existing is not None:
                # Unknown keys and the record UUID survive a correction.
                existing.update(
                    state=state, label_snapshot=habit.name, recorded_at=recorded_at.isoformat()
                )
                action, record = "updated", existing
            else:
                record = {
                    "id": str(_new_id(report)),
                    "habit_id": str(habit_id),
                    "date": day.isoformat(),
                    "state": state,
                    "label_snapshot": habit.name,
                    "recorded_at": recorded_at.isoformat(),
                }
                records.append(record)
                action = "created"
            saved = self._write_day(report, day, "checkins", records)
            self.session.scan()
            return CaptureResult(action, saved, record)

    def set_observation(
        self,
        field_id: UUID,
        day: date,
        value: Scalar | None,
        *,
        today: date,
        recorded_at: datetime,
        source_period: PeriodRef | None = None,
        source_block_id: UUID | None = None,
        expected: Scalar | None = UNCHECKED,
    ) -> CaptureResult:
        """value None clears. Daily fields only; weekly policy needs a later contract."""
        aware(recorded_at)
        if type(day) is not date or type(today) is not date:
            raise ValueError("Capture needs civil dates")
        if day > today:
            raise DocumentError("Datas futuras não recebem valores")
        with writer_lock(self.session.root):
            report = scan(self.session.root)
            if any(
                d.document.id == field_id and d.document.kind == "habit" for d in report.documents
            ):
                raise DocumentError("Hábitos registram check-ins, não observações")
            field = fields_in(report).get(field_id)
            if field is None:
                raise DocumentError("Campo ausente ou inválido; nada foi registrado")
            if field.temporal_policy != "daily":
                raise DocumentError("Campos semanais ainda não têm captura nesta versão")
            if value is not None:
                field.validate_value(value)
            page = period_page(report, PeriodRef.containing("day", day))
            records = deepcopy(page.document.metadata["hw"].get("observations", [])) if page else []
            current = _matching(records, "field_id", field_id)
            if len(current) > 1:
                raise ConflictError("Observações duplicadas para este campo e dia; compare")
            existing = current[0] if current else None
            if existing is not None:
                # Refuse to rewrite a record we cannot interpret.
                observation_from_mapping(existing)
            elif value is not None and day < field.active_from.date():
                raise DocumentError(
                    "Data anterior à ativação do campo; nenhum valor ou falha é inferido"
                )
            previous = None if existing is None else existing.get("value")
            if expected is not UNCHECKED and (
                previous != expected or type(previous) is not type(expected)
            ):
                raise ConflictError(
                    "O valor mudou desde a exibição (edição externa?). Revise e tente novamente."
                )
            if existing is not None and value is not None:
                if previous == value and type(previous) is type(value):
                    return CaptureResult("unchanged", page, existing)
            if existing is None and value is None:
                return CaptureResult("unchanged", page, None)
            if value is None:
                records.remove(existing)
                action, record = "cleared", None
            elif existing is not None:
                existing.update(
                    value=value,
                    field_label_snapshot=field.name,
                    recorded_at=recorded_at.isoformat(),
                )
                observation_from_mapping(existing).validate_field(field)
                action, record = "updated", existing
            else:
                record = {
                    "id": str(_new_id(report)),
                    "field_id": str(field_id),
                    "field_label_snapshot": field.name,
                    "observed_date": day.isoformat(),
                    "recorded_at": recorded_at.isoformat(),
                    "value": value,
                }
                if source_period is not None:
                    record["source_period_ref"] = str(source_period)
                if source_block_id is not None:
                    record["source_block_id"] = str(source_block_id)
                observation_from_mapping(record).validate_field(field)
                records.append(record)
                action = "created"
            saved = self._write_day(report, day, "observations", records)
            self.session.scan()
            return CaptureResult(action, saved, record)


class CaptureSnapshot:
    """Read-only per-day projection of layout blocks; no I/O and no writes."""

    def __init__(self, report: ScanReport, day: date, today: date):
        self.day, self.today = day, today
        self.error = ""
        try:
            self.habits = habits_in(report)
            self.fields = fields_in(report)
            page = period_page(report, PeriodRef.containing("day", day))
        except (ConflictError, ValueError) as error:
            self.habits, self.fields, page = {}, {}, None
            self.error = str(error)
        hw = page.document.metadata["hw"] if page else {}
        self.checkins = {r["habit_id"]: r for r in hw.get("checkins", ())}
        self.observations: dict[str, list[dict]] = {}
        for record in hw.get("observations", ()):
            self.observations.setdefault(record["field_id"], []).append(record)

    def habit_cell(self, habit_id: UUID) -> HabitCell:
        record = self.checkins.get(str(habit_id))
        habit = self.habits.get(habit_id)
        recorded = record["state"] if record else None
        if self.error:
            return HabitCell(habit_id, str(habit_id), "unrecorded", recorded, False, self.error)
        if habit is None:
            label = record["label_snapshot"] if record else str(habit_id)
            return HabitCell(
                habit_id,
                label,
                recorded or "unrecorded",
                recorded,
                False,
                "Hábito ausente neste cofre; o rótulo salvo é exibido e nada é recriado.",
            )
        scheduled = habit.is_scheduled(self.day)
        if record:
            if not scheduled:
                return HabitCell(
                    habit_id,
                    habit.name,
                    recorded,
                    recorded,
                    False,
                    "Fora da programação atual; registro histórico preservado.",
                )
            return HabitCell(habit_id, habit.name, recorded, recorded, self.day <= self.today)
        if not scheduled:
            return HabitCell(habit_id, habit.name, "not_scheduled", None, False)
        if self.day > self.today:
            return HabitCell(habit_id, habit.name, "future", None, False)
        state = "pending" if self.day == self.today else "unrecorded"
        return HabitCell(habit_id, habit.name, state, None, True)

    def field_cell(self, field_id: UUID) -> FieldCell:
        records = self.observations.get(str(field_id), [])
        record = records[0] if len(records) == 1 else None
        value = record.get("value") if record else None
        field = self.fields.get(field_id)
        if self.error or field is None:
            label = record["field_label_snapshot"] if record else str(field_id)
            note = self.error or "Campo ausente neste cofre; o rótulo salvo é exibido."
            return FieldCell(field_id, label, "text", value, False, note)
        base = dict(
            unit=field.unit,
            options=field.options,
            minimum=field.minimum,
            maximum=field.maximum,
        )
        cell = FieldCell(field_id, field.name, field.value_type, value, False, **base)
        if len(records) > 1:
            return replace(cell, note="Observações duplicadas; compare o arquivo.")
        if field.temporal_policy != "daily":
            note = "Campo semanal: captura ainda não disponível."
        elif self.day > self.today:
            note = "Data futura: sem registro."
        elif self.day < field.active_from.date():
            note = (
                f"Campo ativo desde {field.active_from.date().isoformat()}; "
                "dias anteriores não contam como falha."
            )
        else:
            return FieldCell(field_id, field.name, field.value_type, value, True, **base)
        return FieldCell(field_id, field.name, field.value_type, value, False, note, **base)

    def block(self, component: Component) -> list[HabitCell | FieldCell]:
        binding = component.binding
        if isinstance(component.config, InputConfig):
            return [self.field_cell(binding.source_id)] if binding else []
        if not isinstance(component.config, ChecklistConfig):
            return []
        if binding is not None:
            return [
                self.habit_cell(binding.source_id)
                if binding.kind == "habit"
                else self.field_cell(binding.source_id)
            ]
        selection = component.config.selection
        if selection is None:
            return []
        # A manual list is ordered configuration, including unavailable references.
        # Never sort it by name or drop an ineligible/missing canonical source.
        if selection.mode == "manual":
            ordered: list[HabitCell | FieldCell] = []
            for identifier in selection.source_ids:
                if identifier in self.fields:
                    cell = self.field_cell(identifier)
                    compatible = cell.value_type == "boolean" and "boolean" in selection.value_types
                else:
                    cell = self.habit_cell(identifier)
                    compatible = "habit" in selection.value_types
                ordered.append(
                    cell
                    if compatible
                    else replace(
                        cell, editable=False, note="Tipo de fonte incompatível com esta checklist."
                    )
                )
            return ordered
        cells: list[HabitCell | FieldCell] = []
        if "habit" in selection.value_types:
            for habit in sorted(self.habits.values(), key=lambda h: (h.name.casefold(), str(h.id))):
                if selection.mode == "by_tags" and not set(selection.tags) & set(habit.tags):
                    continue
                # Dynamic lists follow the explicit occurrence date. Retain historical
                # records outside the current schedule, clearly labelled and read-only.
                if habit.is_scheduled(self.day) or str(habit.id) in self.checkins:
                    cells.append(self.habit_cell(habit.id))
        for field in sorted(self.fields.values(), key=lambda f: (f.name.casefold(), str(f.id))):
            if field.value_type == "boolean" and selection.matches(field):
                cells.append(self.field_cell(field.id))
        return cells
