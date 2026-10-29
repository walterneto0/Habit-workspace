# Agent prompt — Habit Workspace 6.5A: Stability and Data Integrity

You are the senior Python/PySide6 engineer responsible for **Phase 6.5A**. This is a narrowly scoped stabilization task, not a rewrite and not Phase 7.

## 0. Product direction and baseline

First read `docs/planning/phase-6-5-direction.md` (the accompanying 6.5 product-direction document), then `AGENTS.md`, `PRODUCT.md`, `ARCHITECTURE.md`, `FILE_FORMAT.md`, `LAYOUT_ENGINE.md`, `DESIGN_SYSTEM.md`, `PRIVACY.md`, `ROADMAP.md`, and the latest Phase 5.1/6 verification reports.

Before changing files, inspect the **actual** repository branch, Git status, related source and tests. The prior audit's findings are **hypotheses until reproduced**. Document the initial baseline, run targeted checks, and follow existing Git authorization rules. Do not reset, clean, discard unrelated changes, commit or push without authorization.

**Mission:** make canonical data and time-dependent behavior trustworthy, and prevent the UI from becoming unresponsive under ordinary use. Keep the approved look and file-first model intact.

## 1. Investigate and fix time rollover

Investigate the controller's `today`/`capture_day` behavior when the application remains open across local midnight or resumes after suspend.

- Use an injectable local clock or equivalent deterministic abstraction; do not rely on sleeping until midnight in tests.
- Recompute pending, past, future and eligible states when the local date actually changes.
- Preserve a manually selected historical page and explicitly chosen capture date. Do **not** automatically navigate away from the user's work.
- If the user is following “today,” update it intuitively without overwriting a manual selection.
- Handle wake/resume and time-zone/local-date changes pragmatically; explain assumptions.
- Avoid expensive vault rescans merely to update the civil date.

**Acceptance:** deterministic tests for midnight transition, suspend/resume equivalent, manual historical selection and next-day check-in. Include GUI state test if practical.

## 2. Resolve historical layout semantics

Inspect how the controller resolves a layout (`datetime.now()`), how `layout_history` is versioned, and how capture dates are validated.

Clarify these different concepts: selected `PeriodRef`, selected occurrence date, current instant, historical layout activation instant.

- Verify whether actual data integrity or only presentation is affected.
- Choose the smallest compatible, explicit behavior consistent with `LAYOUT_ENGINE.md` and the product-direction document.
- At minimum, ensure the UI does not misleadingly call an up-to-date layout “the layout of that past day.” A short clear indication may be preferable to implementing a second full editor.
- If an existing resolver can safely support a historical read-only presentation, expose it only if bounded and clearly labeled; never let it silently change an assignment or capture target.
- Preserve all previous revisions; no retroactive missed check-ins or observations before field activation.

**Acceptance:** tests for a layout revision activated midweek, viewing a pre-activation day, current layout resolution, and no mutation on read. Document the policy chosen and deferred historical UX if applicable.

## 3. Measure vault responsiveness before optimizing

Inspect `VaultWatcher`, `VaultSession.scan`, `IndexCache.rebuild`, controller state publication and capture writes.

Create reproducible, non-sensitive synthetic vault benchmarks covering at least **small, medium, and large** volumes (choose realistic sizes and report them), measuring:

- vault opening;
- period navigation and search;
- check-in and typed-value save;
- manual reindex;
- periodic watcher refresh, unchanged versus modified vault.

Report elapsed times and environment. Do **not** claim a performance bug from file count alone.

If measurements show significant UI stalls or needless repeated work, implement the smallest safe improvement. Potential fixes: avoid unnecessary reindex on unchanged snapshots, debounce/coalesce watcher events, or offload slow work using a safe immutable snapshot and Qt-thread handoff.

Never touch QObjects from worker threads, discard change detection, or weaken conflict protection. Preserve external editor refresh, duplicate UUID diagnostics, and rebuild-after-index-deletion behavior.

**Acceptance:** before/after measurements or justified "no change needed" decision, plus regression tests for watcher and canonical state.

## 4. Investigate interrupted writes and locks

Inspect `writer_lock`, `atomic_write`, backup behavior and `LayoutService.save_revision` publication ordering.

- Reproduce interruption scenarios using temporary vaults and safe fault injection.
- Determine what happens after a process terminates while holding a lock.
- Never remove a lock solely based on its age, presence, or an unverified PID.
- Prefer safe diagnostics and explicit recovery instructions if ownership cannot be verified with confidence.
- Check interrupted multi-file layout publication: definitions/revisions may be left unassigned, but a published assignment must not point to missing dependencies.
- Maintain idempotent retries and preserve orphaned canonical files for inspection.
- Never silently overwrite external edits, run destructive recovery on a personal vault, or claim multi-file atomicity that does not exist.

**Acceptance:** tests for normal lock release, interrupted state diagnostics, unsafe recovery refusal, recoverable retry, and original canonical bytes preserved.

## 5. Scope discipline

Focus on **stability and correctness**. You may make small user-facing wording changes required to explain failures or historical state, but do not redesign the Layout Studio, implement onboarding, create new navigation features, or start Phase 7/8/9.

Do not expand `WorkspaceController` indiscriminately; extract small testable helpers when needed. Keep domain and persistence independent of Qt and avoid new schema versions or dependencies unless essential and justified.

## 6. Verification

Use disposable vaults only. Run targeted new tests, full tests, Ruff lint/format, diff checks and applicable Phase 5.1/6 GUI verification tools. Include:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
git diff --check
```

Test the GitHub Actions environment where possible. Never delete/skip flaky tests, weaken assertions or add arbitrary long sleeps just to get green CI. Native X11 or offscreen Qt tests do not substitute for human accessibility review; report this distinction.

## 7. Deliverables and stopping point

Write `docs/verification/phase-6-5a-stability.md` with:

1. Baseline branch/commit and tests.
2. Each audit hypothesis: **confirmed / rejected / not yet verified**, with evidence.
3. Root causes and minimal corrections.
4. Historical layout policy.
5. Benchmark methodology and numbers, before/after where applicable.
6. Recovery scenarios and safeguards.
7. Files changed and actual test results.
8. Risks deferred and precise next actions for Phase 6.5B.

Update existing technical docs when behavior changes, and mark 6.5A's status in `ROADMAP.md` without claiming the entire 6.5 release is complete.

Prepare a reviewable feature branch/PR per `AGENTS.md`, but **do not merge or publish without the approvals required by the repository**.

**Stop after 6.5A. Do not start 6.5B or Phase 7.**
