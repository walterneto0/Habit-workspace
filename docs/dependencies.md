# Dependency inventory (Phases 0–2)

Initial verified environment: Linux x86_64, Python 3.14.7, pip 25.1.1.
`requirements.lock` records the complete resolved application/development package
set, excluding the editable application and pip. It is an exact-version snapshot,
not a hash-verified or cross-platform lock. Platform support must be verified
before broadening the Python range or distributing binaries.

| Packages | Purpose | Installed metadata license expression |
| --- | --- | --- |
| PySide6, PySide6_Essentials, PySide6_Addons, shiboken6 6.12.0 | Qt bindings and runtime | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only |
| PySide6_Pdf, PySide6_WebEngine 6.12.0.140 | Transitive dependencies of the PySide6 distribution | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only |
| pytest 9.2.0, Ruff 0.17.3 | Tests and static checks | MIT |
| setuptools 84.2.1 | Build backend | MIT |
| iniconfig 2.3.1, pluggy 1.7.0 | Test dependencies | MIT |
| packaging 26.3 | Test dependency | Apache-2.0 OR BSD-2-Clause |
| Pygments 2.21.0 | Test dependency | BSD-2-Clause |
| ruamel.yaml 0.18.17, ruamel.yaml.clib 0.2.15 | Phase 1 YAML round trips; transitive C extension | MIT |

Inventory obtained from installed distribution metadata. The application imports
QtCore, QtGui and QtQml, and uses Qt Quick/Controls/Layouts. It does not instantiate
WebEngine, PDF, remote resources, networking, telemetry, or account services.
The full PySide6 distribution brings additional modules; its installation does
not mean those modules are part of the application design.

No fonts or proprietary icon assets are bundled. The system supplies sans-serif.
No application license has been chosen on behalf of the owner.

Before Phase 9 distribution, audit the exact shipped Qt modules and third-party
components, retain their license texts/notices, and document the applicable
source/relinking provisions for the chosen licensing route. Package-level
metadata alone is not a completed redistribution audit. No release artifact
has been approved for public distribution in Phase 0.

All dependencies were installed into `.venv`; nothing was installed globally.
Initial installation required network access. Subsequent application startup was
verified in an isolated network namespace without network interfaces to the host.

Phase 1 adds only ruamel.yaml (plus its declared C-extension dependency).
The reader explicitly uses the pure-Python round-trip parser, preceded by an
event pass rejecting aliases, anchors, custom tags and excessive complexity.
This preserves comments and quoting while treating every document as inert data.
Strict domain validation runs after parsing and before writing. No unsafe YAML
constructor, executable template engine, network resource loader, or downloaded
code is invoked by the application. Version constraints and the exact snapshot
are recorded in `pyproject.toml` and `requirements.lock`.

Phase 2 adds no dependencies, downloaded fonts, or icon packages. Small geometric
icons are original QML Canvas drawings. The UI uses Qt Quick Controls Basic,
QtQuick.Dialogs, QSettings and QDesktopServices from the existing Qt distribution;
QDesktopServices opens local directories only after a user action. Document
previews use plain text and never fetch images or execute markup. The verification
script additionally uses the already installed QtTest module for input simulation.
