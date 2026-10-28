# Habit Workspace

Habit Workspace is an early-stage desktop application for organizing personal
planning data across year, month, ISO-week, and day views. Its design goal is a
local-first workspace where readable files, not a server account or database, are
the durable source of truth.

> **Status: pre-alpha.** Phases 0–4 are implemented. The application is useful
> for exploring the vault, navigation, and domain/file contracts, but it is not
> a finished habit tracker. Data capture, the visual layout editor, charts, and
> backup/export workflows are incomplete. Use test or disposable data and keep
> independent backups.

The initial application interface language is Brazilian Portuguese. Repository
documentation is in English.

## What exists today

- Desktop shell built with Python, PySide6, Qt Quick, and QML, with temporal
  navigation, document browsing, local search, settings, and light/dark themes.
- A local vault format based on Markdown with validated YAML frontmatter.
  Documents have stable UUIDs and remain readable in ordinary editors.
- Atomic document writes, conflict detection, import preview, file watching,
  diagnostics for missing references, and a rebuildable SQLite index.
- Pure-Python temporal and habit-definition models and queries.
- Versioned declarative JSON layout templates, period assignments and defaults,
  immutable revisions, typed metric definitions, and canonical dated
  observations.
- Dynamic metric-source discovery and manual source selections in the domain
  layer. These are not yet a chart-rendering or habit-capture UI.
- Tests and verification scripts for persistence, temporal behavior, layout
  contracts, and offscreen Qt/QML startup.

See the [roadmap](ROADMAP.md) and
[verification reports](docs/verification/phase-0.md) for phase details.

## Not implemented yet

- Phase 5 Layout Studio, component-tree rendering, drag-and-drop, preview,
  undo/redo, and keyboard layout editing.
- Habit check-in and general structured-input capture interfaces.
- Finished task, goal, event, rich-note, and image workflows.
- Chart rendering and broader analytics/rollups.
- Self-contained dependency export, integrated backup, and recovery UX.
- Native desktop accessibility/platform validation or mobile support.

The presence of a domain contract does not imply its corresponding user
interface or workflow is complete. Do not treat this pre-alpha build as a
production personal-data system.

## Architecture

- **Python 3.14** for the application and typed, Qt-independent domain layer.
- **PySide6 / Qt Quick / QML** for the desktop presentation.
- **Markdown + YAML** for canonical pages, habit definitions, metric definitions,
  and dated observations.
- **Versioned JSON** for inert layout configuration. Vault-provided code or QML
  is never executed.
- **SQLite** only as a disposable index/cache reconstructed from canonical files.
- **pytest** and **Ruff** for tests and static checks.

The vault is local and offline by default. Local files are plaintext, not
encrypted. No account is not anonymity, and local storage is not a backup.
Choose a vault folder outside the source checkout; do not place personal vault
data in this repository. Read [PRIVACY.md](PRIVACY.md) before using personal
information.

## System requirements

- Linux x86_64 is the currently verified development platform.
- Python 3.14. The package metadata currently requires `>=3.14,<3.15`.
- A desktop environment for normal use. Headless checks use Qt's offscreen
  platform and software Quick renderer.
- Installation needs package access unless the pinned dependencies are already
  available locally. Running the application does not require network access.

Other operating systems and Python versions are not currently validated.

## Install and launch

From the repository root:

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-deps --no-build-isolation -e '.[dev]'
.venv/bin/python -m habit_workspace
```

The lock file pins the tested dependency versions; it is not hash-verified or a
cross-platform lock. The editable install keeps development dependencies local
to the virtual environment. Do not install project dependencies globally.

For a disposable local vault, choose a directory outside the repository and
create it through the application or CLI:

```bash
.venv/bin/python -m habit_workspace vault create "$HOME/Documents/HabitWorkspace" --name "My vault"
.venv/bin/python -m habit_workspace --vault "$HOME/Documents/HabitWorkspace"
```

Do not use a real personal vault for tests or verification scripts.

## Tests and development

```bash
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m pytest -q
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python -m habit_workspace --smoke-test
.venv/bin/python tools/verify_phase1.py
.venv/bin/python tools/verify_phase2.py
.venv/bin/python tools/verify_phase3.py
```

The pytest suite includes offscreen Qt/QML startup and the Phase 2 input/render
check. The explicit smoke-test command checks that a QML window starts and exits.
These checks do not replace testing with a native window manager, graphics
hardware, platform file dialogs, and assistive technology.

Before submitting changes, run the full checks above. Keep changes scoped to an
approved roadmap phase; do not begin Phase 5 as part of repository maintenance.
Never commit vault data, credentials, generated files, or dependency artifacts.

## Roadmap

| Phase | Status |
| --- | --- |
| 0 — Environment and minimal prototype | Complete |
| 1 — File-first vault | Complete |
| 2 — Desktop shell and navigation | Complete |
| 3 — Temporal domain and canonical habit definitions | Complete |
| 4 — Layout, field, assignment, and observation contracts | Complete |
| 5 — Visual Layout Studio and renderer | Not started |
| 6 — Habit and structured capture | Pending |
| 7 — Planning, notes, images, and calendar | Pending |
| 8 — Charts and cross-period rollups | Pending |
| 9 — Packages, backup, stabilization, and distribution | Pending |

The [ROADMAP.md](ROADMAP.md) and specifications are authoritative for scope and
acceptance criteria.

## Contributing

Early-stage contributions are welcome, especially focused bug reports, test
coverage, documentation improvements, accessibility feedback, and review of
file-format and privacy behavior. Please read [CONTRIBUTING.md](CONTRIBUTING.md)
and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) first. Do not include personal
vault data in an issue, pull request, test fixture, screenshot, or log.

## Source availability and licensing

This repository is **source-available**, not OSI-approved open-source software.
No project license has been selected or added yet. Public visibility alone does
not grant permission to use, modify, or redistribute Habit Workspace; until a
license is approved and included, assume all rights are reserved.

The maintainer is evaluating the PolyForm Noncommercial License 1.0.0 as a
possible future license. It has **not** been adopted, and no noncommercial
permission is granted by this README. See the
[licensing review](docs/licensing-review.md) for the evaluation and outstanding
decisions. Third-party dependencies retain their own licenses; see
[dependency licensing notes](docs/dependencies.md).

Do not publish packages or represent this project as unrestricted open source.
