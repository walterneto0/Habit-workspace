# Phase 7B partial checkpoint — 2026-10-31

Phase 7B is **not complete**. This checkpoint only corrects home-only goal
visibility. No periodic follow-up UI or persistence, note editor, region editor,
reviews, image ingestion, or dedicated Phase 7B GUI journey was delivered.

Changes: application/planning.py, domain/planning.py, tests/test_planning.py,
and an additive implementation note in FILE_FORMAT.md. Existing local
documentation edits were preserved; the existing feature branch was used.

New goals persist a validated home_period_ref and tracking.mode=home_only.
Legacy exact calendar scopes infer their home without writes. Custom/open
legacy scopes remain searchable globally with a visible undefined-period label.
No task/habit semantics or manual goal progress calculations were changed.

Verification:
- Regression tests first failed: 2 failed, 13 passed.
- After implementation: tests/test_planning.py: 15 passed in 0.49s.
- Ruff check: passed.
- Ruff format --check: 120 files already formatted.
- git diff --check: passed.
- Offscreen/software QML smoke: passed, one visible root window.
- Full offscreen/software pytest: 314 passed in 96.74s.
- Native X11 and dedicated pointer/keyboard Phase 7B journey: not performed.

Launch: .venv/bin/python -m habit_workspace
Manual check: create an annual goal; confirm it appears in the annual context
and global planning, but not automatically in month/week/day contexts.

Suggested checkpoint commit: fix(planning): restrict goals to their home period
Suggested PR description: Correct implicit child-period inheritance for goals.
Persist home-only defaults for new goals and infer exact calendar homes for
legacy records without rewriting them. Custom legacy scopes remain globally
discoverable. This is a partial Phase 7B checkpoint, not phase acceptance.
