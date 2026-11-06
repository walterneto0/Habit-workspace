# Codex prompt — Habit Workspace Phase 7C, Execution 1 (Events and Agenda)

**MODE: EXECUTION. Implement, test and report; do not stop at a plan.**

Work in `walterneto0/Habit-workspace`, branch `feat/phase-7c-events-agenda-transfer` starting from current `main` (the verified baseline was `b33d57d52fafe75e064a23e8d27605ae4cfc4a11`). If the branch exists, continue it. Inspect Git state; preserve all local user changes. Do not rewrite, stash or reset them.

Before coding, read `AGENTS.md` and **`docs/planning/phase-7c-direction.md`** in full; if the direction document has not yet been added to the repository, copy the supplied `phase-7c-direction.md` to that path. Read relevant sections of `PRODUCT.md`, `FILE_FORMAT.md`, `ARCHITECTURE.md`, `LAYOUT_ENGINE.md`, `DESIGN_SYSTEM.md`, `PRIVACY.md` and `ROADMAP.md`. The verified Phase 7B.1 baseline passed 359 tests. It does not yet implement `kind: event`.

## Scope: complete event and agenda workflows only

1. Reconcile `PRODUCT.md`'s generic start/end event rule with the approved **discriminated timing union**: timed events require `starts_at`, `ends_at` and IANA timezone; all-day events use civil `start_date`, `end_date_exclusive` and IANA timezone. Persist one authoritative interval, not redundant date/time authorities. Add documented schema-v4 `kind: event` with stable UUID, title/tags/body and optional origin provenance. Preserve unknown metadata and old documents. Validate actual timezone offsets, DST ambiguous/nonexistent local times, aware instant ordering and exclusive interval boundaries. Do not add recurrence.
2. Implement typed pure-Python event domain and an asynchronous, optimistic-revision `EventService` reusing VaultSession, scanner and existing VaultTasks. Support direct create, edit, search, open/details and restart/index rebuild. Errors must preserve drafts and never overwrite external edits.
3. Add user-friendly **Novo evento** Qt Quick/QML forms using Portuguese dates/times, explicit event timezone and all-day selection. Initial calendar context must suggest a *date*, not implicitly create a month- or year-long event. Keep established design/tokens/accessibility and support small windows and keyboard use.
4. Implement an **agenda as a read-only projection**, combining one-off event intersections, tasks on their exact `due_date` and real scheduled habit occurrences. Use `ScanReport` and existing recurrence/check-in contracts. Do not fabricate `missed`, duplicate event/task files, daily checkboxes, scores or occurrences outside scope. Task deadlines remain independent of task scope. Crossing-midnight and multi-day events may display once per relevant agenda day while referring to one canonical UUID. Document/display event-local timezone grouping clearly; do not silently mix viewer/system timezone conventions.
5. Expose grouped agenda rows in normal year/month/week/day navigation with stable ordering, type labels and navigation to original events/tasks/habits. Use bounded/paginated queries for large years. UI must work without a new Layout Studio block. Preserve goal home/cadence, existing layout assignments and habit capture.
6. Add tests **before acceptance** for schema errors, DST rules, midnight exclusivity, all-day day boundaries, ISO cross-year weeks, task due outside scope, no inferred missed habits, UUID conflict, external edits, date navigation, restart, delete/rebuild index and QML pointer/keyboard journeys. Run native X11 when available.

**Explicitly exclude this execution:** selective transfer; `.hwpack`; backup; recurring events; notifications; calendar sync; Phase 8 analytics; Phase 9 packaging. The next execution will implement selected transfer.

Run and report exact results:

```bash
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
git diff --check
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python -m pytest -q
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python -m habit_workspace --smoke-test
```

Create `docs/verification/phase-7c-execution-1.md` containing file changes, final canonical schema, timezone/UI decisions, exact test counts/commands, GUI findings, compatibility and outstanding risks. If you cannot implement a requirement safely, mark it incomplete instead of inventing evidence.

**Do not commit, push, open a PR or merge. Stop after reporting Execution 1.**
