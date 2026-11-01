"""Planning forms reuse the vault worker; drafts never replace scan documents."""

from datetime import date, timedelta

from PySide6.QtCore import QObject, Slot

from habit_workspace.application.planning import query_report
from habit_workspace.domain.planning import goal_home, planning_from_mapping
from habit_workspace.domain.temporal import PeriodRef, TemporalScope


class PlanningActions(QObject):
    def __init__(self, workspace):
        super().__init__(workspace)
        self.workspace = workspace
        self.form = {}
        self.loaded = None

    def rows(self):
        w = self.workspace
        return (
            query_report(w.session.report, w.navigation.period_ref, w.today, w._query)
            if w.session
            else []
        )

    @Slot(str)
    def create(self, kind):
        w = self.workspace
        if not w.session or w.actions.busy or w._guard_studio() or kind not in ("task", "goal"):
            return
        period = w.navigation.period_ref or PeriodRef.containing("day", w.today)
        self.loaded = None
        self.form = dict(
            home=str(period),
            cadence="home_only",
            open=True,
            kind=kind,
            title="",
            body="",
            tags="",
            start=period.start.isoformat(),
            end=period.end.isoformat(),
            due="",
            status="pending" if kind == "task" else "not_started",
            progress="",
            error="",
        )
        w._publish()

    @Slot(str)
    def edit(self, identifier):
        w = self.workspace
        if not w.session or w.actions.busy or w._guard_studio():
            return
        matches = [d for d in w.session.report.documents if str(d.document.id) == identifier]
        if len(matches) != 1 or any(
            str(c.document_id) == identifier for c in w.session.report.conflicts
        ):
            w._notice_message("Referência ausente ou UUID ambíguo; nenhum arquivo alterado.", True)
            return
        loaded = matches[0]
        hw = loaded.document.metadata["hw"]
        if loaded.document.kind not in ("task", "goal"):
            return
        row = next((r for r in self.rows() if r["id"] == identifier), {})
        if row.get("followup_period"):
            w.content.followup(identifier, row["followup_period"])
            return
        self.loaded = loaded
        end = hw["scope"]["end_exclusive"]
        home = goal_home(hw, planning_from_mapping(hw).scope) if hw["kind"] == "goal" else None
        self.form = dict(
            home=str(home) if home else "",
            cadence=hw.get("tracking", {}).get("granularity", "home_only"),
            open=True,
            kind=hw["kind"],
            title=hw["title"],
            body=loaded.document.body,
            tags=", ".join(hw.get("tags", ())),
            start=hw["scope"]["start"],
            end=(date.fromisoformat(end) - timedelta(days=1)).isoformat() if end else "",
            due=hw.get("due_date") or "",
            status=hw["status"],
            progress=str(hw["progress_percent"]) if hw.get("progress_percent") is not None else "",
            error="",
        )
        w._publish()

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
        self.form = self.form | dict(values)
        try:
            f = self.form
            start = date.fromisoformat(f["start"])
            end = date.fromisoformat(f["end"]) if f["end"].strip() else None
            scope = TemporalScope.from_inclusive(start, end) if end else TemporalScope(start, None)
            fields = dict(
                title=f["title"].strip(),
                body=f["body"],
                tags=tuple(f["tags"].split(",")),
                scope=scope,
            )
            if not fields["title"]:
                raise ValueError("Informe um título.")
            if f["kind"] == "task":
                fields["due_date"] = date.fromisoformat(f["due"]) if f["due"].strip() else None
            else:
                fields.update(
                    home_period_ref=str(PeriodRef(f["home"])),
                    tracking={"mode": "home_only"}
                    if f["cadence"] == "home_only"
                    else {"mode": "periodic", "granularity": f["cadence"]},
                    status=f["status"],
                    progress_percent=int(f["progress"]) if f["progress"].strip() else None,
                )
            arguments = dict(
                loaded=self.loaded,
                fields=fields,
                kind=f["kind"],
                period=w.navigation.period_ref or PeriodRef.containing("day", w.today),
            )
            if w.actions.tasks.capture("planning_save", arguments):
                self.form["error"] = ""
                w._notice_message("Salvando…")
        except (ValueError, TypeError) as error:
            self.form["error"] = str(error)
            w._publish()

    @Slot(str, bool, str)
    def complete(self, identifier, completed, token):
        w = self.workspace
        if not w.session or w.actions.busy or w.studio.draft:
            return
        matches = [d for d in w.session.report.documents if str(d.document.id) == identifier]
        if len(matches) != 1 or matches[0].revision.digest != token:
            w._notice_message(
                "Conflito: revise a tarefa atualizada antes de tentar novamente.", True
            )
            return
        if w.actions.tasks.capture(
            "planning_complete", dict(loaded=matches[0], completed=completed, now=w.clock.now())
        ):
            w._notice_message("Salvando…")

    def completed(self, kind, error):
        if error:
            if self.form:
                self.form["error"] = (
                    "Não salvo. O arquivo pode ter mudado; "
                    "copie seu texto antes de cancelar e reabrir. " + str(error)
                )
            self.workspace._notice_message("Não salvo: " + str(error), True)
        else:
            if kind == "planning_save":
                self.form, self.loaded = {}, None
            self.workspace._notice_message("Salvo. Todas as visualizações usam o mesmo registro.")
