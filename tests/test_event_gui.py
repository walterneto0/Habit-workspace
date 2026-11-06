"""Run the complete rendered journey in an isolated Qt GUI process."""

import os
import subprocess
import sys
from pathlib import Path


def test_event_agenda_pointer_keyboard_and_fresh_process():
    script = Path(__file__).resolve().parents[1] / "tools/verify_phase7c_events.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "QT_QUICK_BACKEND": "software"},
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert '"qmlWarnings": []' in result.stdout
    assert '"restart": true' in result.stdout
