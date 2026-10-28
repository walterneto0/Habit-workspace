# Phase 5 — integrated Layout Studio (partial acceptance)

This is an uncommitted implementation for human review. Phase 5 is **not marked
complete**: native visual review, full property editing, specialized typed control
shapes, and pointer drag/drop acceptance remain incomplete. No Phase 6 capture,
Phase 7 authoring, Phase 8 calculations or Phase 9 packages were implemented.
No license, dependencies or canonical schema changed.

## Baseline and repository state

The initial worktree was clean on `main`; `git rev-list --left-right --count
HEAD...origin/main` returned `0 0`. This checks the local tracking reference only;
no fetch, remote CI check, branch creation, commit, push or merge was performed.
The contributor must create `feature/phase-5-layout-studio` and review these changes.

Baseline: `.venv/bin/python -m pytest -q`: **187 passed in 16.05s**;
Ruff check passed; format check reported **71 files already formatted**.
Offscreen smoke passed. Phase 1 and 3 scripts passed. The first direct Phase 2
script invocation aborted with exit 134: xcb could not connect to display `:0`.
Repeating with offscreen/software rendering passed, with no QML warnings.
This environment did not support native graphical review.

## Implemented layers and decisions

- Application `layout_draft.py`: immutable layout snapshots, add/remove/move,
  width changes, duplicate (including new nested block IDs), undo/redo. Bound
  source IDs survive duplication. No writes occur in draft operations.
- Application `layouts.py`: optional editing snapshot preconditions checked
  under the existing writer lock, including initially absent pages and changed
  defaults/layout files. Original layout metadata can be carried into a fork.
- Presentation `layout_studio.py`: Qt state, palette, selection, safe existing
  bindings, explicit new metric drafts, property edits, summary and publication.
  Publication uses a worker-owned VaultSession, never the GUI's mutable session.
- `layout_assets.py`: contained local raster reads limited to the existing
  document byte limit and 4 million pixels; QML receives decoded PNG data, never
  an untrusted file/remote URL. Symlinks and traversal are rejected.
- `LayoutComposition.qml`: common normal-page/editor/preview composition with
  finite built-in visual behaviors, nested sections and truthful deferred states.
- `LayoutStudio.qml`: one/two-column canvas, palette, selection, reorder/resize
  buttons, drag handlers/drop targets, contextual properties, preview, confirmation
  dialogs and undo/redo shortcuts. Properties move below the canvas under 1200 px.
- `controllers.py` and `Main.qml`: normal navigation integration, activation
  label, diagnostics and navigation/close guards. Documents and snapshots remain
  accessible alongside the composition.

Explicit assignments retain their layout identity and publish the next available
version, even when another period has advanced that identity. Inherited defaults
and built-in fallbacks fork to a new UUID/version 1 on save. Merely opening,
previewing or discarding never creates a page. Default registries are never edited.

Activation is a timezone-aware current instant captured when reviewing Save,
not the selected week's start. It is shown in the summary and retained for retry;
editing invalidates the prepared instant. A collision produces an error, never
history replacement. The existing service publishes definitions, immutable JSON,
then period assignment. Multiple files are not an atomic transaction. Partial
publication is retained for recovery. Index failure after successful persistence
is shown separately in the success notice.

New metric definitions are explicitly requested, with stable UUIDs, name, type,
tags and daily temporal policy. They are stored separately from layout JSON,
activated at the exact save instant, and filtered out of publication if no longer
referenced. Existing selection definitions can be bound; creating a new selection
metric requires an options editor and is explicitly rejected for now.

## Verification evidence

Commands use the repository `.venv`, synthetic temporary vaults and no network:

```sh
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m pytest -q
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python -m habit_workspace --smoke-test
.venv/bin/python tools/verify_phase1.py
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python tools/verify_phase2.py
.venv/bin/python tools/verify_phase3.py
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python tools/verify_phase5.py
git diff --check
```

New tests cover isolated/reversible operations, UUIDs, new fields versus binding,
preview preservation, discard/navigation guard, real asynchronous save/reopen,
revision history, shared layout identity, inherited-default forks, external writes,
same-instant collision, preserved metric bytes and index deletion. Existing Phase 4
activation/manual-selection/monthly-assignment and standalone import tests remain
in the suite. No new computed facts are produced.

The Qt verification creates `week/2026-W44`, adds checklist, note, numeric input
and chart, changes properties/order, sends actual Ctrl+Z/Ctrl+Shift+Z key events,
previews and publishes through the Qt adapter. It captures both themes at
1024×768, 1440×900 and 1920×1080. Other actions in that script call the adapter;
this is **not** evidence of an entirely pointer- or keyboard-driven workflow.
Screenshots: `/tmp/habit-workspace-phase5/{dark,light}-{1024,1440,1920}.png`.
They are actual Qt window captures, software/offscreen, not mockups.

Final command counts/results are recorded in the handoff below.

## Incomplete acceptance and risks

- No native Linux visual/platform/accessibility review. No larger text/display
  scaling review, dense layout review or assistive-technology validation.
- Drag handlers/drop targets exist, but real pointer drag/drop, empty-canvas
  insertion, invalid-drop feedback and focus retention need acceptance tests.
- Nested sections can be rendered, duplicated and receive note children; a full
  nested property/reorder editor is absent. Table columns can be linked/added,
  but comprehensive column editing/removal is absent.
- Typed fields use a read-only text shape except boolean; specialized date/time,
  rating/duration/selection shapes and the full new-metric properties remain open.
- Chart manual addition/clear, dynamic tags and period are editable; detailed
  accepted-type filters and full aggregation editing remain incomplete.
- Existing note bindings display inert text; note-section marker extraction and
  richer safe Markdown formatting remain incomplete. Unbound content remains
  accessible through existing document navigation.
- List/checklist do not yet enumerate full source queries/items; no fake completion
  or missed status is invented. Existing inputs do not save observations.
- Worker publication avoids sharing sessions; existing watcher/reindex work and
  bounded raster projection remain synchronous. Large-vault performance is unproven.
- Error/retry behavior reuses Phase 4 publication contracts; exhaustive Qt-level
  partial-failure, missing-binding and conflict dialog visual coverage is incomplete.
- GUI controls and summary need further polish/localization; new-block defaults
  may retain schema-kind labels and inherited built-in titles.

These are Phase 5 follow-ups, not reasons to start Phases 6–9. CI on a new branch
has not been checked and must be reviewed by the human contributor.

## Reproduce and proposed PR

Launch `.venv/bin/python -m habit_workspace`, create a disposable vault, navigate
to the week containing October 29, 2026, and choose **Abrir Layout Studio**.
Choose **1 / 2 colunas**, add components, and explicitly name a new numeric metric
(or select an existing compatible source). Select a block to edit properties,
move/duplicate/remove it, use preview, and choose **Revisar e salvar**. Reopen the
vault and edit again. Use **Fechar** and the discard dialog to abandon a draft.

Proposed PR title: **Add integrated Layout Studio drafts, composition and immutable publication**

Proposed description: Concrete period pages can now open a graphical layout
editor, preview the shared QML composition and publish immutable revisions with
period-only assignments. Typed metrics are explicitly created or bound separately
from visual blocks; existing values and defaults survive visual edits. Includes
snapshot conflict checks, worker publication, integration tests and offscreen
captures. This is partial Phase 5 acceptance; the limitations above must be
resolved before marking the phase complete.

Review checklist:

- Verify period-only forks, shared identity revisions and activation semantics.
- Review stale-file handling, partial publication and unknown metadata retention.
- Run tests and branch CI; perform native pointer/keyboard and accessibility review.
- Finish Phase 5 property/renderer/interaction gaps before acceptance.
- Confirm no schema, licensing, telemetry or Phase 6–9 scope changes.

## Final check results

- Full pytest: **196 passed in 19.21s**, no skips.
- Ruff check: **All checks passed**.
- Ruff format check: **80 files already formatted** (final recheck).
- Offscreen/software smoke: **one visible root window**, passed.
- Verification scripts 1, 2, 3 and 5: **PASS**; Qt scripts reported no QML warnings.
- `git diff --check`: passed.
- The intermediate calendar interaction regression (1 failed, 187 passed) was
  corrected by retaining calendar navigation before composition; final suite passes.
- Native display: failed at baseline as described above; no native-review claim.
- GitHub Actions: not checked; branch and publication remain human actions.
