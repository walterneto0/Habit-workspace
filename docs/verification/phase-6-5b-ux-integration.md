# Phase 6.5B — UX, integration, and performance verification

**Verification date:** 2026-10-30  
**Branch:** `feat/phase-6-5b-responsiveness`  
**Base revision:** `95d06d5` (`origin/main` at checkout); implementation remains
uncommitted.  
**Result:** Locally verified and prepared for maintainer review. No commit, push,
or remote CI result is claimed.

All vaults used for GUI verification and performance measurements were synthetic
temporary fixtures. No personal vault was opened or modified.

## Implemented UX and integration

- Normal tracking lists in-scope habits and provides direct completion, clearing,
  detail, and edit actions without requiring Layout Studio.
- Habit details preserve the selected period and tracking date when returning to
  tracking.
- Tracking cells in custom layouts and the normal tracking list call the same
  capture actions and use the same canonical daily records.
- Vault create/open actions run asynchronously. The dialog exposes an opening
  state, disables repeated submission while busy, closes after success, and shows
  an error while remaining available for correction/retry.
- Capture and refresh work is serialized on a worker-owned vault session.
  Refresh requests coalesce; stale scan results are invalidated after foreground
  writes. Accepted writes are drained during orderly application shutdown.
- Reference lookup is built once per scan, preserving missing, wrong-kind, and
  duplicate-identity diagnostics without rescanning all documents per reference.
- Save feedback distinguishes saving, success, and failure. Canonical Markdown
  remains authoritative; optimistic revision checks and atomic writes preserve
  external edits on conflict.

## End-to-end GUI verification

The existing GUI verifiers use Qt mouse/key events and bounded waits for observable
states. The Phase 6.5B journey was run with both
`QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software` and
`QT_QPA_PLATFORM=xcb QT_QUICK_BACKEND=software`.

| Workflow | Result |
| --- | --- |
| Launch and create a vault through the dialog; observe loading and successful closure | **Passed**, offscreen |
| Open an existing vault through the dialog; observe loading and successful closure | **Passed**, offscreen and XCB |
| Fail to open a missing vault; show an error, keep the dialog usable, and retry successfully | **Passed**, offscreen and XCB |
| Create a habit in the normal tracking flow without opening Layout Studio | **Passed**, offscreen and XCB |
| Check in from normal tracking and observe “Salvando…” then success feedback | **Passed**, offscreen and XCB |
| Inject a save failure through the clicked tracking control; show failure and retain the prior record | **Passed**, offscreen and XCB |
| Navigate through day, week, month, and year views using mouse/keyboard interactions | **Passed**, offscreen |
| Open habit details, edit, and return to the original period/date | **Passed**, offscreen and XCB |
| Use the same canonical check-in from a custom layout, then confirm stable record identity | **Passed**, offscreen and XCB |
| Keyboard focus/navigation, compact/desktop resizing, light/dark themes, reduced motion | **Passed**, offscreen and XCB |
| Close/reopen in a separate process after deleting the disposable SQLite index | **Passed**, offscreen and XCB |
| Unexpected QML warnings in the Phase 6.5B journey | **None observed** |

The GUI checks include a test-controlled worker gate to observe the loading and
saving states deterministically; it does not add delays to application code or
replace real pointer and keyboard interactions. Error paths are exercised through
the UI and use bounded waits.

Earlier-phase GUI verifiers were also run offscreen/software:

- `verify_phase2.py`, including QML startup, vault creation, navigation, keyboard
  interaction, import preview, and rendering: **passed**, no QML warnings.
- `verify_phase3.py`: **passed**, including temporal scopes, record states,
  references, moves, and index reconstruction.
- `verify_phase5.py`, `verify_phase5_interaction.py`, and `verify_phase51_ux.py`:
  **passed**, no QML warnings.
- `verify_phase6.py` and `verify_phase6_refinements.py`: **passed**, no QML
  warnings.
- `verify_phase65a.py`: **passed**, no QML warnings.

Offscreen verification is not a human accessibility review. XCB was available
and verified for the Phase 6.5B GUI journey; other operating systems and display
backends were not tested.

## Persistence integrity coverage

Focused async tests cover:

- Captures queued behind an active refresh and serialized completion.
- An accepted queued capture completing when the task manager closes.
- Duplicate check-in submission being rejected while busy and repeated completed
  state remaining an idempotent no-op.
- External edits being detected as conflicts without replacing the external value.
- Invalidated scan snapshots being suppressed while a subsequent scan sees the
  newer external content.
- Failed writes surfacing as errors, not success, without creating a record.
- Reopening from canonical files and preserving a successful check-in.

These are orderly-shutdown and temporary-filesystem tests. They do not prove
survival of sudden power loss or process termination at every instruction boundary.

## Medium-vault performance

The existing benchmark creates a disposable synthetic medium vault with 25 habits,
5 fields, 365 days of history, 200 notes, 596 files, and approximately 2.83 MB.
The non-GUI benchmark runs three samples per operation and reports medians. Its
operations are synchronous controller/service measurements and should not be
confused with asynchronous UI completion time.

Environment: Python 3.14.7, PySide6 6.12.0, Linux 7.1.13
(Fedora 43, x86_64, glibc 2.42). The previous figures below are the supplied
Phase 6.5A baseline; current measurements are from
`tools/benchmark_vault.py --sizes medium --repeat 3`.

| Operation | Previous baseline | Current median | Reduction |
| --- | ---: | ---: | ---: |
| Vault open (synchronous benchmark path) | 11,316 ms | 274.1 ms | 97.6% |
| Watcher refresh, unchanged | 5,490 ms | 144.2 ms | 97.4% |
| Watcher refresh, modified | 5,490 ms | 302.9 ms | 94.5% |
| Check-in save (synchronous benchmark path) | 11,125 ms | 410.5 ms | 96.3% |
| Typed-value save (synchronous benchmark path) | 11,062 ms | 453.0 ms | 95.9% |

The async GUI benchmark (`tools/benchmark_vault.py --sizes medium --repeat 3
--gui`) separately measures dispatch/slot time, first feedback frame, completion
plus a rendered frame, and the maximum event-loop gap. Values are median
milliseconds unless the column says max:

| GUI operation | Slot | First feedback | Completion + frame | Stall median / max |
| --- | ---: | ---: | ---: | ---: |
| Warm open (synchronous `controller.openVault`) | 280.5 | 296.1 | 298.6 | 277.5 / 361.8 |
| Week navigation by pointer | 37.9 | 44.5 | 51.2 | 31.7 / 116.3 |
| Watcher, unchanged | 0.1 | 5.9 | 144.8 | 11.1 / 11.5 |
| Watcher, modified | 0.1 | 6.0 | 457.6 | 37.8 / 39.3 |
| Check-in by pointer | 63.8 | 63.8 | 680.7 | 78.6 / 102.5 |
| Typed save by keyboard | 59.3 | 59.2 | 230.0 | 47.0 / 48.0 |
| Day navigation by pointer | 38.8 | 41.8 | 48.4 | 32.5 / 40.7 |
| Month navigation by pointer | 46.1 | 48.2 | 54.8 | 36.9 / 38.7 |

The periodic event-loop stall maximum during the measured interval was 36.9 ms.
There were no QML warnings. The async vault-opening dialog is now verified for
loading, success, and failure/retry, but its actual open duration and UI stall
were not separately benchmarked: the existing GUI benchmark still invokes the
synchronous controller open path. No timing is inferred for async opening.

## Automated checks

Final local validation for this branch:

| Check | Result |
| --- | --- |
| Full pytest suite, `.venv/bin/python -m pytest -q` | **295 passed** |
| Ruff lint, `.venv/bin/python -m ruff check .` | **Passed** |
| Ruff format, `.venv/bin/python -m ruff format --check .` | **Passed** |
| `git diff --check` | **Passed** |
| GitHub Actions for this uncommitted work | **Not run / not remotely verified** |

## Remaining limitations and risks

- Some measured GUI stalls exceed the 100 ms responsiveness target: check-in
  maximum 102.5 ms and week-navigation maximum 116.3 ms. Navigation also had a
  single 116.3 ms outlier. Median interactions and early feedback are substantially
  improved, but those outliers remain.
- The displayed warm-open measurement is synchronous. Async dialog opening has
  functional coverage only, not a duration/stall benchmark.
- The large-vault profile remains unmeasured; the results are synthetic and from
  one Linux host. Windows, macOS, and alternate filesystem behavior are unverified.
- No human accessibility review was performed.
- Atomic file replacement and revision checks cannot provide a portable
  filesystem compare-and-swap against every external writer race.
- GitHub Actions has not run against this uncommitted feature work.

**Delivery status:** locally verified and ready for maintainer review/PR
authorization. This is not a claim that the branch has been committed, pushed,
merged, or remotely verified. Phase 7 has not been started.
