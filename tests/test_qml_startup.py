"""Run Qt in a separate process so startup and shutdown are both exercised."""

import os
import subprocess
import sys


def test_qml_window_starts_and_exits(tmp_path):
    environment = {
        **os.environ,
        "QT_QPA_PLATFORM": "offscreen",
        "QT_QUICK_BACKEND": "software",
        "XDG_CONFIG_HOME": str(tmp_path / "config"),
        "XDG_CACHE_HOME": str(tmp_path / "cache"),
        "XDG_DATA_HOME": str(tmp_path / "data"),
    }
    result = subprocess.run(
        [sys.executable, "-m", "habit_workspace", "--smoke-test"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "QML smoke test passed" in result.stdout
    assert not (tmp_path / "config").exists()
    assert not (tmp_path / "data").exists()
