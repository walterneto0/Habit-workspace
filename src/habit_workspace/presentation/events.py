"""Draft-preserving event forms and paged agenda navigation."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

from PySide6.QtCore import QObject, QTimeZone, Slot

from habit_workspace.application.agenda import agenda_groups, agenda_rows
from habit_workspace.domain.events import local_candidates, resolve_local
from habit_workspace.domain.temporal import PeriodRef
from habit_workspace.vault.habits import habit_from_document


class EventActions(QObject):
    def __init__(self, workspace):
        super().__init__(workspace)
        self.workspace = workspace
        self.form = {}
        self.loaded = None
        self.offset = 0
        self.period = None
        self.zones = tuple(sorted(available_timezones() | {"UTC"}))

    def rows(self):
        w = self.workspace
        p = w.navigation.period_ref
        if p != self.period:
            self.offset, self.period = 0, p
        return (
            agenda_rows(w.session.report, p, w.today, offset_days=self.offset)
            if w.session and p
            else []
        )

    def window(self):
        p = self.workspace.navigation.period_ref
        if p is None:
            return {}
        start = p.start + timedelta(days=self.offset)
        end = min(p.end, start + timedelta(days=30))
        return dict(
            label=f"{start:%d/%m/%Y} a {end:%d/%m/%Y}", previous=self.offset > 0, next=end < p.end
        )

    def groups(self, rows):
        return agenda_groups(rows)

    @Slot(str, result="QVariantList")
    def dayRows(self, value):
        w = self.workspace
        if not w.session:
            return []
        try:
            period = PeriodRef.containing("day", date.fromisoformat(value))
        except ValueError:
            return []
        return agenda_rows(w.session.report, period, w.today, window_days=1)

    @Slot(str, result=str)
    def dayPreview(self, value):
        """Read a single civil day without navigating or writing canonical data."""
        w = self.workspace
        if not w.session:
            return "Abra um cofre para ver os registros."
        try:
            period = PeriodRef.containing("day", date.fromisoformat(value))
        except ValueError:
            return "Data inválida."
        rows = agenda_rows(w.session.report, period, w.today, window_days=1)
        labels = [
            " · ".join(filter(None, (r["title"], r.get("time_label"), r.get("status_label"))))
            for r in rows
        ]
        for loaded in w.session.report.documents:
            doc = loaded.document
            hw = doc.metadata["hw"]
            if doc.kind in ("note", "review", "goal") and (
                hw.get("period") == str(period) or hw.get("home_period_ref") == str(period)
            ):
                labels.append(doc.title)
        return (
            "\n".join(labels[:12])
            + (f"\nMais {len(labels) - 12} registros…" if len(labels) > 12 else "")
            if labels
            else "Nada marcado para esta data."
        )

    @Slot(str, result="QVariantList")
    def zoneOptions(self, query):
        return [z for z in self.zones if query.casefold().replace(" ", "_") in z.casefold()]

    @staticmethod
    def local_zone():
        name = bytes(QTimeZone.systemTimeZoneId()).decode("utf-8", errors="replace")
        try:
            ZoneInfo(name)
            return name, "Fuso sugerido pelo sistema; confirme ou escolha outra cidade."
        except ZoneInfoNotFoundError, ValueError:
            return (
                "UTC",
                "Fuso local não identificado. UTC sugerido; escolha sua cidade.",
            )

    @staticmethod
    def wall(day, clock):
        value = time.fromisoformat(clock)
        if value.tzinfo is not None:
            raise ValueError("Informe a hora local sem offset.")
        return datetime.combine(datetime.strptime(day, "%d/%m/%Y").date(), value)

    @Slot(str, str, str, result="QVariantList")
    def wallOptions(self, day, clock, zone):
        try:
            candidates = local_candidates(self.wall(day, clock), zone)
            if len(candidates) != 2:
                return []
            return [
                dict(
                    value=c.isoformat(),
                    label=("Primeira ocorrência" if i == 0 else "Segunda ocorrência")
                    + " · UTC"
                    + c.strftime("%z"),
                )
                for i, c in enumerate(candidates)
            ]
        except ValueError:
            return []

    def search_rows(self):
        w = self.workspace
        if not w.session or not w._query:
            return []
        return [
            dict(id=str(d.document.id), title=d.document.title)
            for d in w.session.report.documents
            if d.document.kind == "event"
            and w._query.casefold()
            in " ".join(
                (d.document.title, d.document.body, *d.document.metadata["hw"].get("tags", []))
            ).casefold()
        ]

    @Slot(int)
    def page(self, delta):
        p = self.workspace.navigation.period_ref
        if p:
            self.offset = max(0, min((p.end - p.start).days // 31 * 31, self.offset + delta * 31))
            self.workspace._publish()

    @Slot()
    def create(self):
        w = self.workspace
        if not w.session or w.actions.busy or w._guard_studio():
            return
        day = (w.navigation.period_ref or PeriodRef.containing("day", w.today)).start
        self.loaded = None
        zone, notice = self.local_zone()
        self.form = dict(
            open=True,
            title="",
            body="",
            tags="",
            start=day.strftime("%d/%m/%Y"),
            end=day.strftime("%d/%m/%Y"),
            startTime="09:00",
            endTime="10:00",
            timezone=zone,
            zoneNotice=notice,
            startChoice="",
            endChoice="",
            allDay=False,
            error="",
        )
        w._publish()

    @Slot(str, str)
    def open(self, kind, identifier):
        w = self.workspace
        if not w.session or w.actions.busy or w._guard_studio():
            return
        matches = [d for d in w.session.report.documents if str(d.document.id) == identifier]
        if (
            len(matches) != 1
            or matches[0].document.kind != kind
            or any(str(c.document_id) == identifier for c in w.session.report.conflicts)
        ):
            w._notice_message("Referência ausente ou UUID ambíguo; nenhum arquivo alterado.", True)
            return
        if kind == "task":
            w.planning.edit(identifier)
            return
        if kind == "habit":
            w._notice_message("Escolha a ocorrência do hábito na agenda.", True)
            return
        if kind != "event":
            w._notice_message("Tipo de referência indisponível.", True)
            return
        self.loaded = matches[0]
        hw = self.loaded.document.metadata["hw"]
        t = hw["timing"]
        all_day = t["kind"] == "all_day"
        start = datetime.fromisoformat(t["start_date"] if all_day else t["starts_at"])
        end = datetime.fromisoformat(t["end_date_exclusive"] if all_day else t["ends_at"])
        if all_day:
            end -= timedelta(days=1)
        self.form = dict(
            open=True,
            title=hw["title"],
            body=self.loaded.document.body,
            tags=", ".join(hw.get("tags", [])),
            start=start.strftime("%d/%m/%Y"),
            end=end.strftime("%d/%m/%Y"),
            startTime=start.time().isoformat(timespec="auto"),
            endTime=end.time().isoformat(timespec="auto"),
            timezone=t["timezone"],
            zoneNotice="Fuso salvo no evento; alterar o fuso mantém as horas locais digitadas.",
            startChoice=start.isoformat() if not all_day else "",
            endChoice=end.isoformat() if not all_day else "",
            allDay=all_day,
            error="",
        )
        w._publish()

    @Slot(str, str, str)
    def openOccurrence(self, kind, identifier, day):
        w = self.workspace
        if kind != "habit":
            self.open(kind, identifier)
            return
        if not w.session or w.actions.busy or w._guard_studio():
            return
        try:
            date_value = datetime.strptime(day, "%Y-%m-%d").date()
            matches = [d for d in w.session.report.documents if str(d.document.id) == identifier]
            if len(matches) != 1 or matches[0].document.kind != "habit":
                raise ValueError("Hábito ausente ou UUID ambíguo; confira as pendências do cofre.")
            habit = habit_from_document(matches[0].document)
            if not habit.is_scheduled(date_value):
                raise ValueError("O hábito não está mais programado nesta data. Atualize a agenda.")
            w.navigate("day", day)
            w.selectDocument(identifier)
        except ValueError as error:
            w._notice_message(str(error), True)

    @Slot()
    def cancel(self):
        if not self.workspace.actions.busy:
            self.form, self.loaded = {}, None
            self.workspace._publish()

    @Slot("QVariantMap")
    def save(self, values):
        w = self.workspace
        if not self.form or w.actions.busy:
            return
        self.form.update(dict(values))
        try:
            f = self.form
            start, end = (datetime.strptime(f[k], "%d/%m/%Y").date() for k in ("start", "end"))
            timing = dict(kind="all_day" if f["allDay"] else "timed", timezone=f["timezone"])
            if f["allDay"]:
                timing.update(
                    start_date=start.isoformat(),
                    end_date_exclusive=(end + timedelta(days=1)).isoformat(),
                )
            else:
                timing.update(
                    starts_at=resolve_local(
                        self.wall(f["start"], f["startTime"]),
                        f["timezone"],
                        f.get("startChoice", ""),
                    ).isoformat(),
                    ends_at=resolve_local(
                        self.wall(f["end"], f["endTime"]), f["timezone"], f.get("endChoice", "")
                    ).isoformat(),
                )
            args = dict(
                loaded=self.loaded,
                title=f["title"],
                timing=timing,
                body=f["body"],
                tags=tuple(f["tags"].split(",")),
            )
            w.actions.tasks.capture("event_save", args)
        except (ValueError, TypeError, OverflowError) as error:
            self.form["error"] = str(error)
        w._publish()

    def completed(self, error):
        if error:
            self.form["error"] = "Não salvo; rascunho preservado. " + str(error)
        else:
            self.form, self.loaded = {}, None
