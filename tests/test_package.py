"""Package contracts that also apply to installed distributions."""

import subprocess
import sys
from importlib.resources import files


def test_import_has_no_qt_or_filesystem_side_effects(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import habit_workspace; import habit_workspace.__main__; "
            "import habit_workspace.application.vault; import habit_workspace.application.imports; "
            "import habit_workspace.application.habits; "
            "assert not any(name.startswith('PySide6') for name in sys.modules)",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert list(tmp_path.iterdir()) == []


def test_qml_resource_is_packaged():
    resource = files("habit_workspace.presentation").joinpath("qml/Main.qml")
    assert resource.is_file()
    assert "ApplicationWindow" in resource.read_text(encoding="utf-8")


def test_shell_components_and_singleton_manifest_are_packaged():
    directory = files("habit_workspace.presentation").joinpath("qml")
    assert "singleton Theme" in directory.joinpath("qmldir").read_text()
    for name in (
        "Theme",
        "Sidebar",
        "PeriodBrowser",
        "VaultDialog",
        "ImportDialog",
        "DocumentList",
        "DocumentDetails",
        "SettingsPage",
        "ActionButton",
    ):
        assert directory.joinpath(f"{name}.qml").is_file()
