"""QML capture requests and background refresh publication for a workspace."""

import json
from uuid import UUID

from PySide6.QtCore import QObject, QThreadPool, Signal, Slot

from habit_workspace.application.capture import fields_in, parse_value
from habit_workspace.presentation.navigation import long_date
from habit_workspace.presentation.vault_tasks import OpenVaultJob, VaultTasks
from habit_workspace.vault.atomic_io import ConflictError


class CaptureActions(QObject):
    opened = Signal(bool)

    def __init__(self, workspace):
        super().__init__(workspace)
        self.workspace = workspace
        self.tasks = None
        self.retired = []
        self.opening = False
        self.closed = False
        self.open_pool = QThreadPool(self)
        self.target = ""
        self.day = None

    @property
    def busy(self):
        return bool(self.tasks and self.tasks.saving)

    def attach(self, session):
        for old in self.retired[:]:
            if not old.pool.activeThreadCount():
                self.retired.remove(old)
                old.deleteLater()
        if self.tasks:
            self.tasks.close(wait=False)
            self.retired.append(self.tasks)
        self.tasks = VaultTasks(session.root, self)
        self.tasks.completed.connect(self._completed)

    def invalidate(self):
        if self.tasks:
            self.tasks.invalidate()

    def close(self):
        self.closed = True
        self.open_pool.waitForDone()
        for tasks in [*self.retired, self.tasks]:
            if tasks:
                tasks.close()

    @Slot(str)
    def openVault(self, directory):
        self._open(directory, None)

    @Slot(str, str)
    def createVault(self, directory, name):
        self._open(directory, name.strip())

    def _open(self, directory, name):
        from habit_workspace.presentation.controllers import local_path

        w = self.workspace
        if self.opening or self.busy or w._guard_studio():
            return
        try:
            root = local_path(directory)
        except ValueError as error:
            w._notice_message(str(error), True)
            return
        self.opening = True
        self.open_job = OpenVaultJob(root, name)
        self.open_job.signals.done.connect(self._opened)
        self.open_pool.start(self.open_job)
        w._notice_message("Abrindo espaço de trabalho…")

    @Slot(object)
    def _opened(self, payload):
        self.opening = False
        if self.closed:
            return
        session, error = payload
        if error:
            self.workspace._notice_message(
                "Não foi possível abrir ou criar o espaço. O cofre atual foi mantido. "
                "Confira a pasta e as permissões. " + str(error),
                True,
            )
        else:
            self.workspace._attach(session)
        self.opened.emit(error is None)

    def _request(self, kind, target, values):
        w = self.workspace
        if not w.session or self.busy or w.studio.draft or w.capture_day is None:
            return False
        day = w._capture_target()
        self.target, self.day = target, day
        arguments = dict(values, day=day, today=w.today, recorded_at=w.clock.now())
        if not self.tasks.capture(kind, arguments):
            return False
        w._feedback = dict(
            target=target, date=day.isoformat(), text="Salvando…", error=False, saving=True
        )
        w._publish()
        return True

    def _failed(self, target, error):
        w = self.workspace
        w._feedback = dict(
            target=target,
            date=w.capture_day.isoformat(),
            text="Não salvo. Revise o valor e tente novamente.",
            diagnostics=str(error),
            error=True,
            saving=False,
        )
        w._notice_message(w._feedback["text"], True)
        return False

    @Slot(str, str, str, result=bool)
    def setCheckin(self, identifier, state, token):
        try:
            return self._request(
                "checkin",
                identifier,
                dict(habit_id=UUID(identifier), state=state or None, expected=json.loads(token)),
            )
        except ValueError as error:
            return self._failed(identifier, error)

    def _observe(self, identifier, block, value, token):
        return self._request(
            "observation",
            identifier,
            dict(
                field_id=UUID(identifier),
                value=value,
                expected=json.loads(token),
                source_period=self.workspace.navigation.period_ref,
                source_block_id=UUID(block) if block else None,
            ),
        )

    @Slot(str, str, str, str, result=bool)
    def saveObservation(self, identifier, block, text, token):
        try:
            field = fields_in(self.workspace.session.report).get(UUID(identifier))
            if field is None:
                raise ValueError("Campo ausente; nada foi registrado.")
            return self._observe(identifier, block, parse_value(field, text), token)
        except ValueError as error:
            return self._failed(identifier, error)

    @Slot(str, str, str, str, result=bool)
    def setBooleanObservation(self, identifier, block, value, token):
        try:
            return self._observe(identifier, block, {"true": True, "false": False}[value], token)
        except (ValueError, KeyError) as error:
            return self._failed(identifier, error)

    @Slot(str, str, result=bool)
    def clearObservation(self, identifier, token):
        try:
            return self._observe(identifier, "", None, token)
        except ValueError as error:
            return self._failed(identifier, error)

    @Slot(str, object, object, object, object)
    def _completed(self, kind, result, report, index_error, error):
        w = self.workspace
        if report is not None:
            w.session.report = report
            w.session.index_error = index_error
        if kind.startswith("planning_"):
            w.planning.completed(kind, error)
            if report is not None:
                w.watcher.accept_report(report)
            return
        if kind != "refresh":
            if error:
                text = (
                    "Conflito: o registro mudou. Revise o estado atualizado e tente novamente."
                    if isinstance(error, ConflictError)
                    else "Não foi possível salvar. Seus registros anteriores foram mantidos; "
                    "tente novamente."
                )
            else:
                text = (
                    (
                        "Registro removido"
                        if result.action == "cleared"
                        else "Sem alterações"
                        if result.action == "unchanged"
                        else "Salvo"
                    )
                    + " · "
                    + long_date(self.day)
                    + "."
                )
            w._feedback = dict(
                target=self.target,
                date=self.day.isoformat(),
                text=text,
                error=bool(error),
                saving=False,
                diagnostics=str(error) if error else "",
            )
            w._notice, w._notice_error = text, bool(error)
        elif error:
            w._notice, w._notice_error = (
                "Não foi possível atualizar. Seus arquivos foram mantidos; tente reindexar.",
                True,
            )
        emitted = report is not None and w.watcher.accept_report(report)
        if not emitted and (kind != "refresh" or error or index_error):
            w._publish()
