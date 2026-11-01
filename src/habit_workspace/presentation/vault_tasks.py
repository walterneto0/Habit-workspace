"""Bounded, serialized file work for one desktop vault session.

Only the worker touches its VaultSession. Reports cross to the GUI read-only;
writers already deep-copy documents. One capture may wait behind one refresh,
refresh requests coalesce, and epochs reject scans older than a foreground write.
Closing stops publication/queued work; an already-started atomic save finishes.
"""

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from habit_workspace.application.capture import CaptureService
from habit_workspace.application.vault import VaultSession


class _Signals(QObject):
    done = Signal(object)


class _Job(QRunnable):
    def __init__(self, owner, epoch, kind, arguments):
        super().__init__()
        self.owner, self.epoch, self.kind, self.arguments = owner, epoch, kind, arguments
        self.signals = _Signals()

    def run(self):
        owner = self.owner
        result = error = None
        try:
            if owner._worker_session is None:
                owner._worker_session = VaultSession.open(owner.root)
                opened = True
            else:
                opened = False
            session = owner._worker_session
            if self.kind == "refresh":
                if not opened:
                    session.scan()
            elif self.kind == "layout_media":
                from habit_workspace.presentation.layout_assets import load_images

                result = (
                    self.arguments["context"],
                    self.arguments["generation"],
                    load_images(session.root, self.arguments["paths"]),
                )
            elif self.kind in ("image_import", "content_media"):
                from habit_workspace.presentation.layout_assets import import_image, markdown_images

                result = (
                    import_image(session.root, self.arguments["source"])
                    if self.kind == "image_import"
                    else markdown_images(session.root, self.arguments["body"])
                )
            elif self.kind == "content_save":
                from habit_workspace.application.content import ContentService
                from habit_workspace.application.planning import PlanningService
                from habit_workspace.domain.temporal import PeriodRef

                loaded = self.arguments["loaded"]
                values = self.arguments["values"]
                if values["followup"]:
                    result = PlanningService(session).followup(
                        loaded, PeriodRef(values["followup"]), values["body"]
                    )
                else:
                    service = ContentService(session)
                    rating = values.get("rating", "")
                    args = dict(
                        title=values["title"],
                        body=values["body"],
                        period=values["period"],
                        rating=int(rating) if str(rating).strip() else None,
                    )
                    result = (
                        service.save(loaded, region=values["region"], **args)
                        if loaded
                        else service.create(kind=values.get("kind", "note"), **args)
                    )
            elif self.kind in ("planning_save", "planning_complete"):
                from habit_workspace.application.planning import PlanningService

                service = PlanningService(session)
                args = dict(self.arguments)
                if self.kind == "planning_complete":
                    result = service.complete(**args)
                else:
                    loaded = args.pop("loaded")
                    fields = args.pop("fields")
                    result = (
                        service.update(loaded, **fields)
                        if loaded
                        else service.create(**args, **fields)
                    )
            elif self.kind in ("checkin", "observation"):
                service = CaptureService(session)
                method = service.set_checkin if self.kind == "checkin" else service.set_observation
                result = method(**self.arguments)
            else:
                raise ValueError("Unknown vault operation")
        except Exception as caught:
            error = caught
            # Reconcile after optimistic conflicts. Never turn a failed save into success.
            if owner._worker_session is not None:
                try:
                    owner._worker_session.scan()
                except Exception:
                    pass
        session = owner._worker_session
        self.signals.done.emit(
            (
                self.epoch,
                self.kind,
                result,
                session.report if session else None,
                session.index_error if session else None,
                error,
            )
        )


class VaultTasks(QObject):
    completed = Signal(str, object, object, object, object)

    def __init__(self, root, parent=None):
        super().__init__(parent)
        self.root = root
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self._worker_session = None  # accessed only by sequential jobs
        self._epoch = 0
        self._closed = False
        self._refresh_pending = False
        self._capture_pending = None
        self._media_pending = {}
        self.active = False
        self.saving = False
        self.job = None

    def invalidate(self):
        """A foreground operation superseded any in-flight read snapshot."""
        self._epoch += 1
        if self.active:
            self._refresh_pending = True

    def refresh(self):
        if not self._closed:
            self._refresh_pending = True
            self._pump()

    def capture(self, kind, arguments):
        if self._closed or self.saving:
            return False
        self.saving = True
        self._capture_pending = kind, dict(arguments)
        self._pump()
        return True

    def media(self, arguments):
        if not self._closed:
            self._media_pending[arguments["context"]] = dict(arguments)
            self._pump()

    def _pump(self):
        if self._closed or self.active:
            return
        if self._capture_pending:
            kind, arguments = self._capture_pending
            self._capture_pending = None
        elif self._refresh_pending:
            kind, arguments = "refresh", {}
            self._refresh_pending = False
        elif self._media_pending:
            context = next(iter(self._media_pending))
            kind, arguments = "layout_media", self._media_pending.pop(context)
        else:
            return
        self.active = True
        self.job = _Job(self, self._epoch, kind, arguments)
        self.job.signals.done.connect(self._done)
        self.pool.start(self.job)

    @Slot(object)
    def _done(self, payload):
        epoch, kind, result, report, index_error, error = payload
        self.active = False
        if kind not in ("refresh", "layout_media"):
            self.saving = False
        if not self._closed and epoch == self._epoch:
            self.completed.emit(kind, result, report, index_error, error)
        self._pump()

    def close(self, *, wait=True):
        self._closed = True
        self._epoch += 1
        pending = self._capture_pending
        self._capture_pending = None
        self._refresh_pending = False
        self._media_pending.clear()
        if pending:
            # A capture already accepted by the UI must finish even when closing.
            kind, arguments = pending
            final_job = _Job(self, self._epoch, kind, arguments)
            self.pool.start(final_job)
        if wait:
            # Never terminate a thread midway through atomic persistence.
            self.pool.waitForDone()


class OpenVaultJob(QRunnable):
    """Opening owns a fresh session until it is handed to the GUI once."""

    def __init__(self, root, name=None):
        super().__init__()
        self.root, self.name = root, name
        self.signals = _Signals()

    def run(self):
        try:
            session = (
                VaultSession.open(self.root)
                if self.name is None
                else VaultSession.create(self.root, self.name)
            )
            self.signals.done.emit((session, None))
        except Exception as error:
            self.signals.done.emit((None, error))
