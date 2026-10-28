"""Qt composition root; application and domain logic will remain outside Qt."""

import sys
from importlib.resources import as_file, files
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine


def run(*, smoke_test: bool = False, vault_directory: Path | None = None) -> int:
    app = QGuiApplication([sys.argv[0]])
    app.setApplicationName("Habit Workspace")
    app.setOrganizationName("Habit Workspace")
    engine = QQmlApplicationEngine()
    qml_errors: list[str] = []
    watcher = None
    if vault_directory is not None:
        from habit_workspace.application.vault import VaultSession
        from habit_workspace.domain.documents import DocumentError
        from habit_workspace.vault.watcher import VaultWatcher

        try:
            session = VaultSession.open(vault_directory)
        except (DocumentError, OSError) as error:
            print(f"Habit Workspace: {error}", file=sys.stderr)
            return 1
        watcher = VaultWatcher(session, app)

        def refresh_status(report) -> None:
            text = (
                f"{session.info.name} · {len(report.documents)} documentos\n"
                f"{len(report.invalid)} arquivos inválidos · {len(report.conflicts)} conflitos · "
                f"{len(report.missing_references)} referências indisponíveis"
            )
            engine.rootObjects()[0].setProperty("vaultStatus", text)

        watcher.refreshed.connect(refresh_status)
        watcher.failed.connect(
            lambda error: engine.rootObjects()[0].setProperty("vaultStatus", error)
        )

    def capture_errors(errors: list) -> None:
        qml_errors.extend(error.toString() for error in errors)

    engine.warnings.connect(capture_errors)
    resource = files("habit_workspace.presentation").joinpath("qml/Main.qml")
    with as_file(resource) as qml_path:
        engine.load(QUrl.fromLocalFile(str(qml_path)))
        if len(engine.rootObjects()) != 1:
            print("Habit Workspace: failed to create the QML window.", file=sys.stderr)
            return 1
        if watcher is not None:
            watcher.start()

        if smoke_test:

            def finish_smoke_test() -> None:
                window = engine.rootObjects()[0]
                if qml_errors or not window.isVisible():
                    print("Habit Workspace: QML smoke test failed.", file=sys.stderr)
                    app.exit(1)
                else:
                    print("Habit Workspace: QML smoke test passed (one visible root window).")
                    app.exit(0)

            QTimer.singleShot(300, finish_smoke_test)

        result = app.exec()
        if watcher is not None:
            watcher.stop()
    return result
