"""Optional Qt adapter. Core file/application modules never import this module."""

from PySide6.QtCore import QFileSystemWatcher, QObject, QTimer, Signal, Slot

from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.documents import DocumentError
from habit_workspace.vault.scanner import fingerprint


class VaultWatcher(QObject):
    refreshed = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        session: VaultSession,
        parent: QObject | None = None,
        *,
        debounce_ms: int = 200,
        rescan_ms: int = 2000,
        request_refresh=None,
    ):
        super().__init__(parent)
        self.session = session
        self.request_refresh = request_refresh
        self.filesystem = QFileSystemWatcher(self)
        self.debounce = QTimer(self)
        self.debounce.setSingleShot(True)
        self.debounce.setInterval(debounce_ms)
        self.periodic = QTimer(self)
        self.periodic.setInterval(rescan_ms)
        self.filesystem.fileChanged.connect(self._schedule)
        self.filesystem.directoryChanged.connect(self._schedule)
        self.debounce.timeout.connect(self._tick)
        self.periodic.timeout.connect(self._tick)
        self._emitted: tuple | None = None

    @property
    def paths(self) -> list[str]:
        return self.filesystem.files() + self.filesystem.directories()

    def clear_paths(self) -> None:
        if self.paths:
            self.filesystem.removePaths(self.paths)

    def start(self) -> None:
        if self.request_refresh:
            self.accept_report(self.session.report)
        else:
            self.refresh()
        self.periodic.start()

    def stop(self) -> None:
        self.periodic.stop()
        self.debounce.stop()
        self.clear_paths()

    @Slot(str)
    def _schedule(self, _path: str) -> None:
        self.debounce.start()

    @Slot()
    def refresh(self, force: bool = False) -> None:
        """Rescan files; announce only a changed snapshot unless ``force`` (reindex)."""
        self.debounce.stop()
        try:
            if force:
                self.session.request_index_rebuild()
            report = self.session.scan()
            self.accept_report(report, force=force)
            if self.session.index_error:
                self.failed.emit(self.session.index_error)
        except (OSError, DocumentError) as error:
            self.failed.emit(str(error))

    @Slot()
    def _tick(self):
        self.debounce.stop()
        if self.request_refresh:
            self.request_refresh()
        else:
            self.refresh()

    def accept_report(self, report, *, force=False):
        # Atomic editor saves and renames drop OS watches: reattach every scan.
        wanted = {str(p) for p in report.directories}
        wanted.update(str(d.path) for d in (*report.documents, *report.layouts, *report.defaults))
        wanted.update(
            str(issue.path)
            for issue in report.invalid
            if issue.path.is_file() and not issue.path.is_symlink()
        )
        current = set(self.paths)
        if current - wanted:
            self.filesystem.removePaths(sorted(current - wanted))
        if wanted - current:
            # Unwatchable paths still receive explicit/periodic scan coverage.
            self.filesystem.addPaths(sorted(wanted - current))
        snapshot = fingerprint(report)
        if force or snapshot != self._emitted:
            self._emitted = snapshot
            self.refreshed.emit(report)
            return True
        return False
