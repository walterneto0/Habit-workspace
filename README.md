# Habit Workspace

Habit Workspace is an early-stage desktop application for organizing personal
planning data across year, month, ISO-week, and day views. Its design goal is a
local-first workspace where readable files, not a server account or database, are
the durable source of truth.

> **Status: pre-alpha.** Phases 0–4, the main Layout Studio workflow,
> Phase 6/6.5, Phase 7A tasks/goals and Phase 7B content/reflection are
> implemented and tested. Events/calendar, charts and backup/export remain pending. Use disposable data and keep independent backups.

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
- Dynamic metric-source discovery, manual source selections, direct habit
  check-ins and typed observation capture. Calculated charts remain pending.
- Direct task and goal planning (Phase 7A): canonical records, search,
  deadlines, carryover, goal progress, and task list/checklist bindings.
- Explicit goal ownership/cadence, linked period follow-ups with independent
  manual overall progress; full-length notes and validated page-local regions.
- Exact-period Markdown reviews with optional manual rating, safe local raster
  import into Assets/, alternative text, and offline images in notes/layouts.
- Tests and verification scripts for persistence, temporal behavior, layout
  contracts, and offscreen Qt/QML startup.

See the [roadmap](ROADMAP.md), [Phase 7A CI report](docs/verification/phase-7a.md)
and [Phase 7B final verification](docs/verification/phase-7b-final.md) for phase details.

Concrete period pages now offer **Abrir Layout Studio**: add/select/reorder/resize
blocks, preview, undo/redo and save a new immutable revision for that period.
New metrics require an explicit choice and are saved separately. Chart
calculations remain unavailable. See [verification and limitations](docs/verification/phase-5.md)
and [keyboard operations](docs/layout-studio-shortcuts.md).

The same pages have a **tracking mode** (Phase 6): create or edit habits, pick a
date in the open period, and mark check-ins or enter typed values (for example,
minutes studied) in the resolved layout without opening the Studio. Values are
written to the canonical day file. See [Phase 6 verification](docs/verification/phase-6.md).

## Not implemented yet

- Complete Phase 5 acceptance: comprehensive component properties, specialized
  input shapes, validated pointer drag/drop and native visual review.
- Events and calendar (Phase 7C).
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
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python tools/verify_phase6.py
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python tools/verify_phase7a.py
```

The pytest suite includes offscreen Qt/QML startup and the Phase 2 input/render
check. The explicit smoke-test command checks that a QML window starts and exits.
These checks do not replace testing with a native window manager, graphics
hardware, platform file dialogs, and assistive technology.

Before submitting changes, run the full checks above. Keep changes scoped to an
approved roadmap phase; do not introduce unrelated features as maintenance.
Never commit vault data, credentials, generated files, or dependency artifacts.

## Roadmap

| Phase | Status |
| --- | --- |
| 0 — Environment and minimal prototype | Complete |
| 1 — File-first vault | Complete |
| 2 — Desktop shell and navigation | Complete |
| 3 — Temporal domain and canonical habit definitions | Complete |
| 4 — Layout, field, assignment, and observation contracts | Complete |
| 5 — Visual Layout Studio and renderer | Partial; integrated workflow available |
| 6 — Habit and structured capture | Implemented; awaiting owner review |
| 7A — Tasks and goals | Implemented; CI verified |
| 7B — Notes, reviews, images and tracking policy | Implemented; ready for review |
| 7C — Events, agenda and selected transfer | Pending |
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
The project's original source code is licensed under the
[PolyForm Noncommercial License 1.0.0](LICENSE).

The license permits use, study, modification, and redistribution for permitted
noncommercial purposes, subject to its complete terms. Commercial use requires
separate authorization from the relevant copyright holder(s). This is not an
OSI-approved license or unrestricted open source. Third-party dependencies
retain their own licenses and notices; see
[dependency licensing notes](docs/dependencies.md).

See the [licensing notes](docs/licensing-review.md) for contributor copyright,
dependency, and future commercial licensing considerations.

## Phase 7B content workflows

Use **Nova nota** or **Nova avaliação do período** directly from the workspace.
Reviews require an exact period (for example week/2026-W53); their optional 1–5
rating is manual, with no derived scoring. Multiple reviews per period are allowed.
The note/review editor saves asynchronously and preserves drafts after conflicts.
Use **Inserir imagem local** with alternative text, then **Prévia segura** to see
local images. PNG/JPEG/WebP/GIF imports are limited to 2 MiB and 4 million pixels.
Layout Studio image properties also offer a local image picker; save a new layout
revision after import. Failed/cancelled saves may leave an unreferenced asset.

The Markdown preview uses inert text and validated local image thumbnails, with
no HTML execution or remote fetching. Existing page-region markers are required;
missing/ambiguous markers are reported without automatic repair. External-edit
conflicts retain drafts and require explicit reopen; there is no merge editor.
See [full acceptance instructions and evidence](docs/verification/phase-7b-final.md).
