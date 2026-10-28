# Phase 0 verification

## Implemented

- Python src-layout package, local virtual environment, exact dependency snapshot,
  pytest/Ruff configuration and wheel package data.
- Minimal Portuguese Qt Quick window using initial dark design tokens and a system
  font. No vault, domain features, or preferences are created.
- Side-effect-free package/entry imports and a bounded QML startup smoke option.

## Executed results

| Check | Result |
| --- | --- |
| Python/dependency compatibility | Python 3.14.7 and PySide6 6.12.0 installed successfully |
| `python -m ruff check .` | Passed |
| `python -m ruff format --check .` | Passed |
| `python -m pytest -q` | 3 passed |
| Network-isolated offscreen startup | Passed, exit 0 |
| Wheel build | Passed; QML resource verified in archive |
| Wheel installation into temporary directory | Passed; launch used installed wheel package, not source package |
| Offscreen image capture | Passed; inspected at 1100 × 740, legible Portuguese text and no clipping |
| Native display startup | Failed: could not connect to display `:0`; Qt xcb plugin initialization failed |

The wheel test reused dependencies from the project virtual environment, while
installing the application wheel into a fresh temporary directory and asserting
its import location. It does not establish a completely fresh machine install.

Offline check command (Linux namespace support required):

```bash
unshare --user --map-root-user --net env QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software QML_DISABLE_DISK_CACHE=1 .venv/bin/python -m habit_workspace --smoke-test
```

The screenshot was captured to `/tmp/habit-workspace-phase0.png` using the software
renderer and inspected. It is a temporary verification artifact, not a committed
golden screenshot. An initial capture helper lacked the QtQuick type import and
failed; the corrected helper succeeded. This did not require application changes.

## Limitations and next gate

Native desktop behavior, GPU rendering, keyboard integration, window-manager
resize, and cross-platform compatibility remain unverified. The xcb diagnostic
also mentions `xcb-cursor0`; no system packages were installed or display settings
changed. Native validation must be repeated in a working desktop session.

This foundation is not the Phase 2 visual shell. Light theme, responsive panels,
accessibility interactions, reduced motion and later Layout Studio workflows
will receive their own visual and interaction acceptance checks.

The initial sandbox dependency download failed on DNS; the authorized network
retry succeeded. No user vault files were created or transmitted, and no Git
commit was made. Phase 1 has not started.
