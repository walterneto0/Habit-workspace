import json
import os
import subprocess
import sys


def command(*args):
    result = subprocess.run(
        [sys.executable, "-m", "habit_workspace", "vault", *map(str, args)],
        capture_output=True,
        text=True,
        timeout=15,
    )
    return result, json.loads(result.stdout)


def test_cli_portability_and_rebuild(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    assert command("create", first)[0].returncode == 0
    result, created = command("new-note", first, "--title", "Olá", "--body", "Portable text")
    assert result.returncode == 0
    identifier = created["id"]
    assert command("create", second)[0].returncode == 0
    result, imported = command("import", second, created["path"])
    assert result.returncode == 0 and len(imported["imported"]) == 1
    result, shown = command("show", second, identifier)
    assert result.returncode == 0 and shown["body"] == "Portable text"
    (second / ".habit-workspace/index.sqlite").unlink()
    result, rebuilt = command("reindex", second)
    assert result.returncode == 0 and len(rebuilt["documents"]) == 1
    assert command("show", second, identifier)[1]["body"] == "Portable text"
    result = subprocess.run(
        [sys.executable, "-m", "habit_workspace", "--vault", str(second), "--smoke-test"],
        capture_output=True,
        text=True,
        timeout=15,
        env={
            **os.environ,
            "QT_QPA_PLATFORM": "offscreen",
            "QT_QUICK_BACKEND": "software",
            "QML_DISABLE_DISK_CACHE": "1",
        },
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_cli_errors_are_structured(tmp_path):
    result, error = command("open", tmp_path / "missing")
    assert result.returncode == 1
    assert "Cannot open vault" in error["error"]
