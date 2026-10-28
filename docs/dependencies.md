# Phase 0 dependency inventory

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
