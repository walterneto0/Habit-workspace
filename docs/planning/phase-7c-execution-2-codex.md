# Codex prompt — Habit Workspace Phase 7C, Execution 2 (Selective Transfer + Final Acceptance)

**MODE: EXECUTION. Implement, test and report; do not stop at a plan.**

Continue the owner-approved working branch (currently `feat/modular-calendar-transfer`) **after** reviewing the verified Execution 1 report. Read `AGENTS.md`, `docs/planning/phase-7c-direction.md`, `docs/verification/phase-7c-execution-1.md` and the relevant canonical architecture/file-format docs. Preserve all existing uncommitted changes. Do not repeat event/agenda implementations that already passed their acceptance tests.

## Scope: selected local inter-vault transfer, safe integration, phase verification

1. Implement a read-only **transfer preflight** from one source vault to another existing local destination vault. Select one or more canonical documents. Inspect and explicitly list supported referenced Markdown documents, requested layout JSON revisions and selected local Assets, plus invalid/missing/ambiguous and unsupported dependencies. Use source UUID identities and stable versioned layout references; avoid recursive cycles, too many files/bytes, path traversal and symlinks. Preview privacy consequences and allow explicit inclusion/exclusion before copying. Never automatically copy a whole vault, all historical day pages or unrelated personal notes.
2. Implement create-only transfer of selected items reusing `ImportService`, document repository, layout/asset validation, atomic writers and existing worker/lock patterns. Preserve UUIDs, metadata, original contents and selected references. Identical UUID+bytes skip; mismatched UUID or asset path collision blocks with an understandable warning. No silent overwrite, UUID remapping, automatic destructive cleanup or hidden migration. Report partial failures truthfully. Disallow source and destination being the same vault and show destination problems before confirmation.
3. Provide a user-facing Portuguese workflow: choose source items and another local vault, see a clear dependency preview, toggle allowed dependencies and confirm. Show per-item outcomes and missing-reference diagnostics. A selected note with an image must reopen offline at the target; selected event/task must keep its canonical timing/due metadata. A selected period page may claim visual reconstruction **only if its required layout revisions and supporting documents/assets actually transfer**. If a dependency class is unsupported, block or label the affected transfer incomplete rather than claiming success.
4. Keep `.hwpack`, ZIP export/import, full backup/restore, installers and complete cross-device package guarantees **for Phase 9**. Do not introduce an alternative archive format.
5. Integrate with the completed Phase 7C event/agenda feature: transferred items must be visible in the destination agenda after rebuild, without creating phantom habit states. Do not change Phase 7B goal tracking semantics, revision conflict protection or local image security.
6. Add tests for transitive dependency preview, selective inclusion/exclusion, missing reference disclosure, layout revision identity, asset paths, symlinks, duplicate identities, identical/different bytes, source invalidity, partial failure, restart/reindex, and dedicated Qt offscreen/X11 pointer/keyboard verification. Use **only disposable synthetic vaults**.
7. Update `README.md`, `ROADMAP.md`, `PRODUCT.md`, `FILE_FORMAT.md`, `ARCHITECTURE.md`, `LAYOUT_ENGINE.md` and `DESIGN_SYSTEM.md` only as required for actual behavior; preserve historical verification reports. Write `docs/verification/phase-7c-final.md` with final contracts, transfer support matrix, tested boundaries and exact results.

Verification:

```bash
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
git diff --check
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python -m pytest -q
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python -m habit_workspace --smoke-test
```

Run the specific Phase 7C GUI journeys offscreen and X11 when available. Clearly separate verified technical correctness from untested human accessibility and Windows/macOS behavior. If the transfer feature is partially complete, **do not** mark the whole Phase 7C completed.

Deliver a concise report with changed paths, schema decisions, explicit dependency coverage, exact test counts, GUI evidence, known limitations, manual acceptance instructions and suggested commit/PR text. **Do not commit, push, open a PR or merge without authorization. Stop for review.**
