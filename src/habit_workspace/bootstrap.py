"""Qt composition root; file/domain services remain independent of presentation."""

import sys
from importlib.resources import as_file, files
from pathlib import Path

from PySide6.QtCore import QLibraryInfo, QLocale, QTimer, QTranslator, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from habit_workspace.presentation.controllers import WorkspaceController


def run(*, smoke_test: bool = False, vault_directory: Path | None = None) -> int:
    QQuickStyle.setStyle("Basic")
    QLocale.setDefault(QLocale("pt_BR"))
    app = QGuiApplication([sys.argv[0]])
    app.setApplicationName("Habit Workspace")
    app.setOrganizationName("Habit Workspace")
    translator = QTranslator(app)
    if translator.load(
        QLocale("pt_BR"),
        "qtbase",
        "_",
        QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath),
    ):
        app.installTranslator(translator)
    engine = QQmlApplicationEngine()
    controller = WorkspaceController(app)
    if vault_directory is not None and not controller.openVault(str(vault_directory)):
        print(f"Habit Workspace: {controller.state['notice']}", file=sys.stderr)
        return 1
    engine.setInitialProperties({"backend": controller})
    qml_errors: list[str] = []

    def capture_errors(errors: list) -> None:
        qml_errors.extend(error.toString() for error in errors)

    engine.warnings.connect(capture_errors)
    resource = files("habit_workspace.presentation").joinpath("qml")
    with as_file(resource) as qml_directory:
        engine.load(QUrl.fromLocalFile(str(qml_directory / "Main.qml")))
        if len(engine.rootObjects()) != 1:
            print("Habit Workspace: failed to create the QML window.", file=sys.stderr)
            controller.close()
            return 1
        if smoke_test:

            def finish_smoke_test() -> None:
                window = engine.rootObjects()[0]
                if qml_errors or not window.isVisible():
                    print("Habit Workspace: QML smoke test failed.", file=sys.stderr)
                    app.exit(1)
                else:
                    print("Habit Workspace: QML smoke test passed (one visible root window).")
                    app.exit(0)

            QTimer.singleShot(400, finish_smoke_test)
        result = app.exec()
        controller.close()
        # Destroy QML bindings while their Python QObject still exists.
        engine.deleteLater()
    return result
