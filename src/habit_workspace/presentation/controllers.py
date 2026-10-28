"""Presentation adapter over Phase 1 services. Never owns canonical document data."""

import json
import re
from dataclasses import replace
from datetime import date, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from PySide6.QtCore import Property, QObject, QSettings, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from habit_workspace.application.capture import (
    CaptureService,
    CaptureSnapshot,
    fields_in,
    habits_in,
    parse_value,
)
from habit_workspace.application.habits import HabitService, HistoryImpactError
from habit_workspace.application.imports import ImportService
from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.documents import Document, DocumentError
from habit_workspace.domain.temporal import Recurrence, TemporalScope
from habit_workspace.presentation.navigation import Navigation, long_date
from habit_workspace.presentation.tracking import STATE_LABELS, date_state, default_day
from habit_workspace.vault.atomic_io import ConflictError, read_bytes
from habit_workspace.vault.format import decode
from habit_workspace.vault.habits import habit_from_document
from habit_workspace.vault.scanner import reference_problem
from habit_workspace.vault.watcher import VaultWatcher

KIND_LABELS = {
    "note": "Nota",
    "page": "Página",
    "year_page": "Página anual",
    "month_page": "Página mensal",
    "week_page": "Página semanal",
    "day_page": "Página diária",
    "habit": "Definição de hábito",
    "metric_definition": "Definição de campo",
}


def local_path(value: str) -> Path:
    url = QUrl(value)
    if url.isLocalFile():
        return Path(url.toLocalFile())
    if url.scheme():
        raise DocumentError("Escolha um arquivo ou uma pasta local.")
    return Path(value).expanduser().absolute()


def excerpt(body: str) -> str:
    """Inert text summary, not an HTML/Markdown/resource renderer."""
    text = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"[Imagem: \1]", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s+", "", text)
    text = re.sub(r"(?m)^```[^\n]*$", "", text)
    return text.strip()[:6000]


class WorkspaceController(QObject):
    changed = Signal()

    def __init__(self, parent=None, *, settings=None, today=None):
        super().__init__(parent)
        self.settings = settings if settings is not None else QSettings()
        self.today = today or date.today()
        self.navigation = Navigation(self.today)
        self.session: VaultSession | None = None
        self.watcher: VaultWatcher | None = None
        self._selected = ""
        self._query = ""
        self._notice = ""
        self._notice_error = False
        self._preview = {}
        self._pending = None
        self._state = {}
        self._capture_day: date | None = None
        self._feedback = {}
        self._habit_form = {}
        self._editing_habit = None
        from habit_workspace.presentation.layout_studio import LayoutStudio

        self.studio = LayoutStudio(self)
        self._publish()

    @Property("QVariantMap", notify=changed)
    def state(self):
        return self._state

    @Property(QObject, constant=True)
    def layoutStudio(self):
        return self.studio

    def _composition(self):
        if not self.session or not self.navigation.period:
            return {}
        from habit_workspace.application.layouts import LayoutService
        from habit_workspace.presentation.layout_studio import composition

        try:
            resolved = LayoutService.resolve_report(
                self.session.report, self.navigation.period_ref, datetime.now().astimezone()
            )
            capture = CaptureSnapshot(self.session.report, self.capture_day, self.today)
            return dict(
                blocks=composition(
                    resolved.layout, self.session.report, self.session.root, capture=capture
                ),
                columns=resolved.layout.grid.columns,
                issues=list(resolved.issues),
                activation=resolved.assignment.effective_at.isoformat()
                if resolved.assignment
                else "Padrão interno",
                captureError=capture.error,
            )
        except (ValueError, OSError) as error:
            return dict(blocks=[], columns=1, issues=[str(error)], activation="Indisponível")

    @property
    def capture_day(self) -> date | None:
        period = self.navigation.period_ref
        if period is None:
            return None
        if self._capture_day and period.start <= self._capture_day <= period.end:
            return self._capture_day
        return default_day(period, self.today)

    def _tracking(self):
        period = self.navigation.period_ref
        if not self.session or period is None:
            return {}
        return date_state(period, self.capture_day, self.today) | {"feedback": self._feedback}

    def _habits(self):
        """Canonical habits relevant to this period, shared by every period view.

        Uses the existing scan only: no filesystem work or occurrence expansion.
        """
        period = self.navigation.period_ref
        if not self.session or period is None:
            return {}
        try:
            habits = habits_in(self.session.report)
            snapshot = CaptureSnapshot(self.session.report, self.capture_day, self.today)
        except (ValueError, OSError) as error:
            return {"rows": [], "error": str(error), "unresolved": []}
        interval = period.scope
        records = [
            record
            for loaded in self.session.report.documents
            for record in loaded.document.metadata["hw"].get("checkins", ())
            if interval.contains(date.fromisoformat(record["date"]))
        ]
        weekdays = ("Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom")
        rows = []
        for habit in sorted(habits.values(), key=lambda h: (h.name.casefold(), str(h.id))):
            if not habit.scope.intersects(interval):
                continue
            end = habit.scope.end_exclusive
            cell = snapshot.habit_cell(habit.id)
            rows.append(
                dict(
                    id=str(habit.id),
                    name=habit.name,
                    tags=", ".join(habit.tags),
                    scope=habit.scope.start.isoformat()
                    + " → "
                    + ((end - timedelta(days=1)).isoformat() if end else "sem término"),
                    recurrence="Diário"
                    if habit.recurrence.kind == "daily"
                    else ", ".join(weekdays[d - 1] for d in habit.recurrence.days),
                    stateLabel=STATE_LABELS.get(cell.state, cell.state),
                    outside=sum(
                        r["habit_id"] == str(habit.id)
                        and not habit.is_scheduled(date.fromisoformat(r["date"]))
                        for r in records
                    ),
                )
            )
        known = {str(i) for i in habits}
        return {
            "rows": rows,
            "error": "",
            "unresolved": [
                f"{r['date']} · {r['label_snapshot']} · {STATE_LABELS.get(r['state'], r['state'])}"
                for r in sorted(records, key=lambda r: r["date"])
                if r["habit_id"] not in known
            ],
        }

    def _capture_failed(self, target: str, error: Exception) -> bool:
        stale = isinstance(error, ConflictError)
        text = ("Não salvo: " if not stale else "Conflito, nada foi salvo: ") + str(error)
        self._feedback = {"target": target, "text": text, "error": True}
        if self.session:
            # Show the current canonical state after a rejected or stale edit.
            self.session.scan()
        self._notice_message(text, True)
        return False

    def _captured(self, target: str, text: str) -> bool:
        self._feedback = {"target": target, "text": text, "error": False}
        self._notice_message(text)
        return True

    @Slot(int)
    def moveCaptureDate(self, amount: int):
        period = self.navigation.period_ref
        if period is None:
            return
        target = self.capture_day + timedelta(days=amount)
        if period.start <= target <= period.end:
            self._capture_day, self._feedback = target, {}
            self._publish()

    @Slot(str)
    def setCaptureDate(self, value: str):
        period = self.navigation.period_ref
        try:
            target = date.fromisoformat(value)
        except ValueError:
            self._notice_message("Data inválida. Use AAAA-MM-DD.", True)
            return
        if period is None or not period.start <= target <= period.end:
            self._notice_message("Escolha uma data dentro do período aberto.", True)
            return
        self._capture_day, self._feedback = target, {}
        self._publish()

    @Slot(str, str, str, result=bool)
    def setCheckin(self, habit_id: str, state: str, expected: str) -> bool:
        if not self.session or self._guard_studio() or self.capture_day is None:
            return False
        try:
            result = CaptureService(self.session).set_checkin(
                UUID(habit_id),
                self.capture_day,
                state or None,
                today=self.today,
                recorded_at=datetime.now().astimezone(),
                expected=json.loads(expected),
            )
        except (ValueError, OSError) as error:
            return self._capture_failed(habit_id, error)
        label = STATE_LABELS["unrecorded" if not state else state]
        verb = {"unchanged": "Sem alterações", "cleared": "Registro removido"}.get(
            result.action, "Check-in salvo"
        )
        return self._captured(
            habit_id, f"{verb} · {long_date(self.capture_day)} · {label}. Arquivo diário canônico."
        )

    def _observe(self, field_id: str, block_id: str, value, expected: str) -> bool:
        if not self.session or self._guard_studio() or self.capture_day is None:
            return False
        try:
            result = CaptureService(self.session).set_observation(
                UUID(field_id),
                self.capture_day,
                value,
                today=self.today,
                recorded_at=datetime.now().astimezone(),
                source_period=self.navigation.period_ref,
                source_block_id=UUID(block_id) if block_id else None,
                expected=json.loads(expected),
            )
        except (ValueError, OSError) as error:
            return self._capture_failed(field_id, error)
        verb = {
            "unchanged": "Sem alterações",
            "cleared": "Valor removido",
            "updated": "Valor corrigido",
        }.get(result.action, "Valor salvo")
        return self._captured(field_id, f"{verb} · {long_date(self.capture_day)}.")

    @Slot(str, str, str, str, result=bool)
    def saveObservation(self, field_id: str, block_id: str, text: str, expected: str) -> bool:
        if not self.session:
            return False
        try:
            field = fields_in(self.session.report).get(UUID(field_id))
            if field is None:
                raise ValueError("Campo ausente; nada foi registrado")
            value = parse_value(field, text)
        except ValueError as error:
            return self._capture_failed(field_id, error)
        return self._observe(field_id, block_id, value, expected)

    @Slot(str, str, str, str, result=bool)
    def setBooleanObservation(self, field_id: str, block_id: str, value: str, expected: str):
        value = {"true": True, "false": False}.get(value)
        return self._observe(field_id, block_id, value, expected)

    @Slot(str, str, result=bool)
    def clearObservation(self, field_id: str, expected: str) -> bool:
        return self._observe(field_id, "", None, expected)

    def _form(self, **values):
        period = self.navigation.period_ref
        self._habit_form = (
            dict(
                open=True,
                mode="create",
                id="",
                name="",
                tags="",
                scopeMode="period",
                start=period.start.isoformat(),
                end=period.end.isoformat(),
                recurrence="daily",
                days=[],
                bind=False,
                error="",
                impact=False,
                periodLabel=self.navigation.title,
                canBind=True,
            )
            | values
        )
        self._publish()

    @Slot()
    def newHabit(self):
        if self.session and self.navigation.period_ref and not self._guard_studio():
            self._editing_habit = None
            self._form()

    @Slot(str)
    def editHabit(self, identifier: str):
        if not self.session or not self.navigation.period_ref or self._guard_studio():
            return
        try:
            loaded = HabitService(self.session).load(identifier)
        except (ValueError, OSError) as error:
            self._notice_message("Não foi possível abrir o hábito. " + str(error), True)
            return
        habit = loaded.habit
        self._editing_habit = loaded
        end = habit.scope.end_exclusive
        self._form(
            mode="edit",
            id=str(habit.id),
            name=habit.name,
            tags=", ".join(habit.tags),
            scopeMode="custom",
            start=habit.scope.start.isoformat(),
            end=(end - timedelta(days=1)).isoformat() if end else "",
            recurrence=habit.recurrence.kind.value,
            days=list(habit.recurrence.days),
            canBind=False,
        )

    @Slot()
    def cancelHabit(self):
        self._habit_form, self._editing_habit = {}, None
        self._publish()

    @Slot("QVariantMap", result=bool)
    def saveHabit(self, values) -> bool:
        if not self.session or not self._habit_form or self._guard_studio():
            return False
        period = self.navigation.period_ref
        form = dict(self._habit_form) | {
            k: values.get(k, self._habit_form[k])
            for k in ("name", "tags", "scopeMode", "start", "end", "recurrence", "days", "bind")
        }
        try:
            name = str(form["name"]).strip()
            if not name:
                raise ValueError("Informe um nome para o hábito.")
            tags = tuple(t.strip() for t in str(form["tags"]).split(",") if t.strip())
            if form["scopeMode"] == "period":
                scope = period.scope
            else:
                try:
                    start = date.fromisoformat(str(form["start"]).strip())
                    end = str(form["end"]).strip()
                    end = date.fromisoformat(end) if end else None
                except ValueError as error:
                    raise ValueError("Datas devem usar AAAA-MM-DD.") from error
                if end is not None and end < start:
                    raise ValueError("A data final deve ser igual ou posterior à inicial.")
                scope = (
                    TemporalScope.from_inclusive(start, end) if end else TemporalScope(start, None)
                )
            days = tuple(sorted({int(d) for d in form["days"]}))
            if form["recurrence"] == "weekdays":
                if not days:
                    raise ValueError("Escolha ao menos um dia da semana.")
                recurrence = Recurrence.weekdays(days)
            else:
                recurrence = Recurrence.daily()
            service = HabitService(self.session)
            if self._editing_habit is None:
                origin = None
                try:
                    from habit_workspace.application.layouts import period_page

                    page = period_page(self.session.report, period)
                    origin = page.document.id if page else None
                except ConflictError:
                    origin = None
                saved = service.create(
                    name=name,
                    period=period,
                    scope=scope,
                    recurrence=recurrence,
                    tags=tags,
                    origin_page_id=origin,
                )
            else:
                saved = service.update(
                    self._editing_habit,
                    name=name,
                    tags=tags,
                    scope=scope,
                    recurrence=recurrence,
                    acknowledge_history=bool(values.get("acknowledge", False)),
                )
        except HistoryImpactError as error:
            self._habit_form = form | {
                "error": f"{len(error.records)} check-in(s) ficarão fora da nova programação. "
                "Eles serão preservados no arquivo diário e exibidos como históricos. "
                "Confirme para salvar.",
                "impact": True,
            }
            self._publish()
            return False
        except (ValueError, OSError) as error:
            stale = isinstance(error, ConflictError)
            self._habit_form = form | {
                "error": (
                    "O arquivo do hábito mudou fora do aplicativo; cancele e reabra para revisar. "
                    if stale
                    else ""
                )
                + str(error),
                "impact": False,
            }
            self._publish()
            return False
        created = self._editing_habit is None
        self._habit_form, self._editing_habit = {}, None
        self._notice_message(
            ("Hábito criado: " if created else "Hábito atualizado: ")
            + saved.habit.name
            + ". Uma única definição canônica, visível em todos os períodos do escopo."
        )
        if created and form["bind"]:
            self.studio.open()
            if self.studio.draft:
                self.studio.add("checklist", str(saved.habit.id), saved.habit.name, "")
                self.studio.message = (
                    "Checklist vinculada ao novo hábito adicionada. Revise e salve o layout."
                )
                self.studio.changed.emit()
        return True

    def _guard_studio(self):
        if self.studio.draft:
            self.studio.message = "Salve ou descarte o rascunho antes de navegar."
            self.studio.changed.emit()
            self._notice_message(
                "Feche o Layout Studio: salve ou descarte o rascunho antes de navegar.", True
            )
            return True
        return False

    def _notice_message(self, text: str, error: bool = False) -> None:
        self._notice, self._notice_error = text, error
        self._publish()

    def _entries(self):
        if not self.session:
            return []
        report = self.session.report
        conflicts = {c.document_id for c in report.conflicts}
        rows = []
        for loaded in report.documents:
            doc = loaded.document
            hw = doc.metadata["hw"]
            rows.append(
                {
                    "id": str(doc.id),
                    "title": doc.title or "Documento sem título",
                    "kind": KIND_LABELS[doc.kind],
                    "path": str(loaded.path.relative_to(self.session.root)),
                    "period": hw.get("period", "day/" + hw["date"] if "date" in hw else ""),
                    "tags": ", ".join(hw.get("tags", [])),
                    "conflict": doc.id in conflicts,
                    "missing": sum(r.source_path == loaded.path for r in report.missing_references),
                }
            )
        return sorted(rows, key=lambda row: (row["title"].casefold(), row["path"]))

    def _issues(self):
        if not self.session:
            return []
        report = self.session.report
        issues = [
            {
                "title": "Arquivo não reconhecido",
                "detail": str(i.path.relative_to(self.session.root)) + "\n" + i.message,
            }
            for i in report.invalid
        ]
        issues += [
            {
                "title": "Conflito de identidade · " + str(c.document_id),
                "detail": "Compare os arquivos no seu editor; nenhum foi substituído.\n"
                + "\n".join(str(p.relative_to(self.session.root)) for p in c.paths),
            }
            for c in report.conflicts
        ]
        roles = {
            "habit_id": "Hábito",
            "origin_page_id": "Página de origem",
            "layout_id": "Layout",
            "field_id": "Campo",
        }
        issues += [
            {
                "title": "Referência indisponível · " + roles.get(r.role, r.role),
                "detail": str(r.source_path.relative_to(self.session.root))
                + "\n"
                + str(r.target_id),
            }
            for r in report.missing_references
        ]
        if self.session.index_error:
            issues.append(
                {
                    "title": "Índice indisponível; documentos preservados",
                    "detail": self.session.index_error,
                }
            )
        return issues

    def _selection(self, entries):
        matches = [r for r in entries if r["id"] == self._selected]
        if len(matches) != 1 or matches[0]["conflict"]:
            return {}
        row = dict(matches[0])
        doc = next(
            d.document
            for d in self.session.report.documents
            if str(d.document.id) == self._selected
        )
        row["excerpt"] = excerpt(doc.body)
        row["truncated"] = len(doc.body) > 6000
        row["records"] = []
        states = {"done": "Concluído", "missed": "Falha declarada", "skipped": "Dispensado"}
        hw = doc.metadata["hw"]
        for record in hw.get("checkins", []):
            row["records"].append(
                {"label": record["label_snapshot"], "value": states[record["state"]]}
            )
        for record in hw.get("observations", []):
            row["records"].append(
                {"label": record["field_label_snapshot"], "value": str(record["value"])}
            )
        return row

    def _publish(self):
        nav = self.navigation
        entries = self._entries()
        visible = entries
        if nav.period:
            # Scope-only filtering of the existing scan: no filesystem work or
            # occurrence expansion on the GUI thread, and no generated pages.
            interval = nav.period_ref.scope
            habit_ids = (
                {
                    str(entry.document.id)
                    for entry in self.session.report.documents
                    if entry.document.kind == "habit"
                    and habit_from_document(entry.document).scope.intersects(interval)
                }
                if self.session
                else set()
            )
            visible = [r for r in visible if r["period"] == nav.period or r["id"] in habit_ids]
        if self._query:
            query = self._query.casefold()
            visible = [
                r
                for r in visible
                if query in " ".join(str(r[k]) for k in ("title", "tags", "id", "path")).casefold()
            ]
        recent = self.settings.value("recentVaults", [], type=list)
        state = {
            "composition": self._composition(),
            "tracking": self._tracking(),
            "habits": self._habits(),
            "habitForm": self._habit_form,
            "hasVault": self.session is not None,
            "vaultName": self.session.info.name if self.session else "Seu espaço pessoal",
            "vaultPath": str(self.session.root) if self.session else "",
            "recentVaults": recent,
            "view": nav.view,
            "title": nav.title,
            "period": nav.period,
            "anchor": nav.anchor.isoformat(),
            "today": self.today.isoformat(),
            "todayLabel": long_date(self.today),
            "range": long_date(nav.start) + " — " + long_date(nav.end) if nav.period else "",
            "breadcrumbs": nav.breadcrumbs(),
            "children": nav.children(),
            "calendar": nav.calendar(),
            "documents": visible,
            "documentCount": len(entries),
            "issues": self._issues(),
            "selected": self._selection(entries),
            "query": self._query,
            "notice": self._notice,
            "noticeError": self._notice_error,
            "importPreview": self._preview,
            "theme": self.settings.value("theme", "dark"),
            "reducedMotion": self.settings.value("reducedMotion", False, type=bool),
            "sidebarCollapsed": self.settings.value("sidebarCollapsed", False, type=bool),
        }
        if state != self._state:
            self._state = state
            self.changed.emit()

    def _attach(self, session: VaultSession):
        if self.watcher:
            self.watcher.stop()
            self.watcher.deleteLater()
        self.session = session
        self._selected, self._query = "", ""
        self._pending, self._preview = None, {}
        self._capture_day, self._feedback, self._habit_form = None, {}, {}
        self.navigation.view = "overview"
        self.watcher = VaultWatcher(session, self)
        self.watcher.refreshed.connect(lambda _report: self._publish())
        self.watcher.failed.connect(
            lambda message: self._notice_message(
                "Não foi possível atualizar o cofre. " + message, True
            )
        )
        recent = self.settings.value("recentVaults", [], type=list)
        path = str(session.root)
        self.settings.setValue("recentVaults", [path] + [p for p in recent if p != path][:4])
        self.watcher.start()
        self._notice_message("Cofre aberto. Seus arquivos permanecem neste dispositivo.")

    @Slot(str, str, result=bool)
    def createVault(self, directory: str, name: str) -> bool:
        if self._guard_studio():
            return False
        try:
            self._attach(VaultSession.create(local_path(directory), name.strip()))
            return True
        except (DocumentError, OSError) as error:
            self._notice_message(
                "Não foi possível criar o cofre. Escolha uma pasta vazia.\n" + str(error), True
            )
            return False

    @Slot(str, result=bool)
    def openVault(self, directory: str) -> bool:
        if self._guard_studio():
            return False
        try:
            self._attach(VaultSession.open(local_path(directory)))
            return True
        except (DocumentError, OSError) as error:
            self._notice_message(
                "Não foi possível abrir o cofre. O cofre atual foi mantido.\n" + str(error), True
            )
            return False

    @Slot(str)
    @Slot(str, str)
    def navigate(self, view: str, value: str = ""):
        if self._guard_studio():
            return False
        try:
            self.navigation.select(view, value)
            self._query = ""
            self._selected = ""
            self._capture_day, self._feedback, self._habit_form = None, {}, {}
            self._publish()
        except (ValueError, OverflowError) as error:
            self._notice_message(str(error), True)

    @Slot(int)
    def movePeriod(self, amount: int):
        if self._guard_studio():
            return False
        try:
            self.navigation.move(amount)
            self._selected = ""
            self._capture_day, self._feedback, self._habit_form = None, {}, {}
            self._publish()
        except ValueError, OverflowError:
            self._notice_message("Limite de navegação: anos de 2 a 9998.", True)

    @Slot()
    def goToday(self):
        self.today = date.today()
        self.navigate(
            self.navigation.view if self.navigation.period else "day", self.today.isoformat()
        )

    @Slot(str)
    def setQuery(self, query: str):
        self._query = query
        self._publish()

    @Slot(str)
    def selectDocument(self, identifier: str):
        matches = [r for r in self._entries() if r["id"] == identifier]
        if len(matches) != 1 or matches[0]["conflict"]:
            self._selected = ""
            self._notice_message(
                "Identidade ausente ou duplicada. Compare os arquivos nas "
                "pendências do cofre; nenhum documento foi escolhido.",
                True,
            )
            return
        self._selected = identifier
        self._publish()

    @Slot()
    def clearSelection(self):
        self._selected = ""
        self._publish()

    @Slot()
    def reindex(self):
        if self.watcher:
            failures = []
            self.watcher.failed.connect(failures.append)
            try:
                self.watcher.refresh()
            finally:
                self.watcher.failed.disconnect(failures.append)
            if not failures:
                self._notice_message("Índice reconstruído a partir dos arquivos.")

    @Slot(str, bool, result=bool)
    def previewImport(self, source: str, as_note: bool) -> bool:
        self._pending, self._preview = None, {}
        if not self.session:
            return False
        try:
            path = local_path(source)
            if path.suffix.lower() != ".md":
                raise DocumentError("Selecione um documento .md.")
            raw, revision = read_bytes(path)
            plain = as_note and not raw.decode("utf-8-sig").startswith("---")
            doc = (
                Document.from_metadata(
                    {
                        "hw": {
                            "schema_version": 4,
                            "kind": "note",
                            "id": str(uuid4()),
                            "title": path.stem,
                        }
                    },
                    raw.decode("utf-8"),
                )
                if plain
                else decode(raw)
            )
            report = self.session.scan()
            matches = [d for d in report.documents if d.document.id == doc.id]
            conflict = bool(matches) and not (
                len(matches) == 1 and matches[0].revision.digest == revision.digest
            )
            preview_report = report
            if not matches:
                from habit_workspace.vault.scanner import LoadedDocument

                preview_report = replace(
                    report, documents=report.documents + (LoadedDocument(path, doc, revision),)
                )
            missing = sum(
                reference_problem(preview_report, ref) is not None for ref in doc.references()
            )
            self._preview = {
                "title": doc.title or path.stem,
                "kind": KIND_LABELS[doc.kind],
                "path": str(path),
                "id": "Novo UUID ao importar" if plain else str(doc.id),
                "excerpt": excerpt(doc.body)[:800],
                "missingCount": missing,
                "conflict": conflict,
                "identical": bool(matches) and not conflict,
                "plain": plain,
            }
            self._pending = (path, revision, as_note)
            self._publish()
            return True
        except (DocumentError, OSError, UnicodeError) as error:
            self._notice_message("Não foi possível preparar a importação. " + str(error), True)
            return False

    @Slot()
    def cancelImport(self):
        self._pending, self._preview = None, {}
        self._publish()

    @Slot(result=bool)
    def confirmImport(self) -> bool:
        if self._guard_studio():
            return False
        if not self.session or not self._pending or self._preview.get("conflict"):
            return False
        path, revision, as_note = self._pending
        try:
            _, current = read_bytes(path)
            if current != revision:
                raise DocumentError("O arquivo mudou após a prévia. Selecione-o novamente.")
            result = ImportService(self.session).import_files([path], as_note=as_note)
            failed = bool(result.conflicting or result.invalid)
            message = (
                "Conflito: documento já existente; nenhum arquivo foi substituído."
                if result.conflicting
                else "Arquivo inválido; importação não realizada."
                if result.invalid
                else "Documento idêntico já presente. Nenhuma cópia criada."
                if result.skipped
                else "Documento importado. Consulte as pendências do cofre "
                "para referências indisponíveis."
            )
            if result.invalid:
                message += "\n" + result.invalid[0].message
            self._pending, self._preview = None, {}
            self.navigation.view = "notes"
            self._query = ""
            if result.imported:
                self._selected = str(result.imported[0].document_id)
            self._notice_message(message, failed)
            return not failed
        except (DocumentError, OSError) as error:
            self.cancelImport()
            self._notice_message("Importação interrompida. " + str(error), True)
            return False

    @Slot(str)
    def setTheme(self, value: str):
        if value in ("light", "dark"):
            self.settings.setValue("theme", value)
            self._publish()

    @Slot(bool)
    def setReducedMotion(self, value: bool):
        self.settings.setValue("reducedMotion", value)
        self._publish()

    @Slot(bool)
    def setSidebarCollapsed(self, value: bool):
        self.settings.setValue("sidebarCollapsed", value)
        self._publish()

    @Slot()
    def dismissNotice(self):
        self._notice_message("")

    @Slot()
    def revealVault(self):
        if self.session and not QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(self.session.root))
        ):
            self._notice_message("O gerenciador de arquivos não pôde ser aberto.", True)

    @Slot()
    def revealSelected(self):
        selection = self._state["selected"]
        if self.session and selection:
            # Reveal the containing directory. Never execute a document or remote reference.
            path = self.session.root / selection["path"]
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent))):
                self._notice_message("O gerenciador de arquivos não pôde ser aberto.", True)

    def close(self):
        if self.watcher:
            self.watcher.stop()
