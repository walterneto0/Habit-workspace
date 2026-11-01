import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("depth", [1, 3])
def test_nested_note_editing_selectors_restart_and_index_rebuild(depth):
    script = Path(__file__).resolve().parents[1] / "tools/verify_phase7b1_ux.py"
    result = subprocess.run(
        [sys.executable, str(script), "--depth", str(depth)],
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "QT_QUICK_BACKEND": "software"},
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert '"result": "PASS"' in result.stdout
    assert '"freshProcess": true' in result.stdout
    assert not result.stderr, result.stderr
