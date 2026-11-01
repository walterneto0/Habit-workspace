# Phase 7B — execution 1

Execution 1 scope A–C implemented and verified. Full Phase 7B still includes
reviews and image ingestion, excluded from this request.

Implemented goals with persisted home-only/month/week/day tracking, strictly
smaller than the logical home period. Normal child views expose linked follow-up
rows; one goal document stores uniquely keyed exact-period commentary records.
History remains visible/editable after policy changes. Overall manual progress
is independent. Boundary weeks display their eligible scope intersection.

Standalone notes support direct creation, full-text editing, inert plain-text
Markdown preview, optional exact period association, body search, details and
navigation to the associated period. Linked notes and page-local regions use
distinct actions. Regions require balanced, unique, exact, nonnested markers;
ambiguous originals are read-only. Missing regions are not auto-created.
All saves use the existing serialized worker and optimistic canonical writes;
drafts remain after validation/persistence errors and external-edit conflicts.
BOM, line-ending policy, UUIDs and unknown compatible metadata are preserved.

Canonical contract: see FILE_FORMAT.md, execution 1 section. Additive schema 4;
no implicit migrations. Legacy inference from the checkpoint remains intact.

Changed/new implementation paths:
- application/content.py; application/planning.py
- domain/planning.py
- presentation/content.py, planning.py, controllers.py, capture_actions.py,
  vault_tasks.py, layout_studio.py
- QML ContentDialog, PlanningDialog, PlanningRow, Main, DocumentDetails,
  LayoutComposition
- tests/test_content_execution1.py; tools/verify_phase7b_execution1.py
- additive FILE_FORMAT, ARCHITECTURE and LAYOUT_ENGINE documentation
Preexisting uncommitted work and the checkpoint were preserved.

Verification:
- Initial focused persistence tests: 8 passed.
- Intermediate regression: 2 failed, 321 passed; failures were existing preview
  expectations. Corrected by retaining inert simplified preview without truncation.
- Expanded focused content/Phase 6 tests: 23 passed.
- Offscreen dedicated GUI: PASS, zero QML warnings; note create/edit, keyboard
  save, monthly goal tracking, follow-up edit/reopen, index rebuild, page-region
  editing and linked-note opening.
- Native Linux X11 (xcb/software): expanded journey PASS, zero QML warnings.
  Sandbox could not connect to display; authorized native run succeeded.
- Ruff check: PASS. Ruff format --check: PASS (126 files already formatted).
- git diff --check: PASS. Offscreen/software QML smoke: PASS, one visible root window.
- Final full offscreen/software pytest: **328 passed in 98.15s (0:01:38)**.

Limitations: preview is inert text, not formatted Markdown. Existing regions
require markers in the canonical page; missing markers are disclosed without
automatic repair/creation. Conflicts preserve drafts but require explicit
cancel/reopen after copying unsaved text; no merge UI. No manual accessibility
audit or Windows/macOS validation. Reviews/images remain outside this execution.

Launch: .venv/bin/python -m habit_workspace
Manual journey: open a vault, Nova nota, edit/save/reopen; optionally associate
week/2026-W44 and use Abrir período associado. Create a goal in the year view,
choose Mensal in Acompanhar, then open an eligible month and edit its linked
follow-up. Global planning opens the original goal to change policy/progress.
On page note blocks use Editar texto da página or Editar nota independente.

Suggested commit: feat(content): add goal follow-ups and canonical Markdown editing
Suggested PR description: Add explicit goal cadence with exact-period linked
commentary, preserving independent overall progress and legacy discovery.
Introduce direct full-length note and structurally validated page-region editing
through revision-aware vault workers, with draft-preserving conflict handling.
Validation evidence above. No commits, pushes or PRs were created.

Exact verification commands:
```bash
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
git diff --check
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python -m pytest -q
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python -m habit_workspace --smoke-test
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python tools/verify_phase7b_execution1.py
QT_QPA_PLATFORM=xcb QT_QUICK_BACKEND=software .venv/bin/python tools/verify_phase7b_execution1.py
```
