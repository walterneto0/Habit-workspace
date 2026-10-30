# Phase 6.5A — Stability and data integrity

**Verification date:** 2026-10-30  
**Revision under test:** `36384dd` (`origin/main` at checkout), with the
`tools/verify_phase5_interaction.py` synchronization fix described below.  
**Result:** Local automated checks passed. GitHub Actions has not run against
these uncommitted changes, so remote CI status is unconfirmed.

## Verification summary

| Check | Result |
| --- | --- |
| Full test suite | **286 passed** (`.venv/bin/python -m pytest -q`, 90.56 s) |
| Ruff lint | **Passed** (`.venv/bin/ruff check .`) |
| Ruff formatting | **Passed**, 103 files formatted (`.venv/bin/ruff format --check .`) |
| Phase 5 pointer/property/reopen verifier, XCB/software | **Passed**; real pointer events, independent process reopen, fresh QML engine reopen; no QML warnings |
| Phase 5 pointer/property/reopen verifier, offscreen/software | **Passed**; no QML warnings |
| Phase 6.5A rollover/history GUI verifier, offscreen/software | **Passed**, all 7 checks; real pointer check-in; no QML warnings |
| Remote GitHub Actions | **Not confirmed**; changes were not pushed and no post-fix remote run was available |

The GUI verifiers used synthetic temporary vaults. No user vault was opened or
changed. The offscreen result is not a native-window or accessibility review.

## `nav-week` pointer regression

The regression was a popup lifecycle race in the interaction verifier. Opening
the vault closes a modal `VaultDialog` with a 150 ms exit transition. Its submit
button becomes hidden before Qt has finished dismissing the modal popup and its
input-blocking overlay. The verifier's generic 80 ms settle period, including
the next control's focus settle, did not establish that the popup was closed.
Under CI scheduling, the actual `QTest.mouseClick` at `nav-week` could therefore
be consumed by the modal overlay.

The failure diagnostics showed the controller still at `overview` after the
click, while `nav-week` was visible and enabled with a 192 × 36 logical-pixel
button and an in-window center point at `(112, 428)`. This ruled out invalid
button geometry and a controller navigation result. The popup's QObject
`visible` property, rather than the submit button's visibility, is now awaited
after vault submission in both the initial and fresh-engine reopen paths. The
test still sends a real pointer click and still asserts `week/2026-W44`; neither
the interaction nor its assertion was removed or weakened. On a future failure,
the assertion reports the controller state, button bounds/visibility/enabled
state, window activation, and pointer containment.

The specific test passed in isolation and as part of the full suite after this
change. No post-fix GitHub Actions result is claimed.

## Responsiveness benchmark

Measurements came from `tools/benchmark_vault.py --repeat 3` on disposable
synthetic vaults. The script times synchronous Python/file/SQLite work invoked
by `WorkspaceController` without rendering QML; timings are not frame rates.
Reported operation values are median / maximum milliseconds across three
samples. The host was Python 3.14.7, PySide6 6.12.0, Linux x86_64 (glibc 2.42).

| Operation | Small: 91 files, 235,483 bytes | Medium: 596 files, 2,830,258 bytes |
| --- | ---: | ---: |
| Open vault | 118.7 / 119.3 | 10,295.5 / 10,359.3 |
| Navigate day | 5.3 / 5.3 | 27.5 / 27.7 |
| Navigate week | 5.8 / 5.9 | 30.5 / 30.7 |
| Navigate month | 5.7 / 5.7 | 32.2 / 32.4 |
| Search | 5.7 / 5.7 | 32.0 / 32.1 |
| Save check-in | 130.6 / 131.1 | 10,272.0 / 10,311.9 |
| Save typed value | 135.5 / 136.3 | 10,223.7 / 10,260.4 |
| Manual reindex | 72.4 / 72.4 | 5,205.5 / 5,225.2 |
| Watcher refresh, unchanged | 54.4 / 54.9 | 5,021.3 / 5,039.0 |
| Watcher refresh, modified | 67.9 / 68.7 | 5,190.4 / 5,330.0 |

One-run breakdown (milliseconds):

| Breakdown | Small | Medium |
| --- | ---: | ---: |
| Session scan | 54.2 | 4,990.4 |
| File scan | 54.1 | 4,872.6 |
| SQLite index rebuild | 7.0 | 90.0 |
| Publish controller state | 5.4 | 27.6 |

The medium measurements are slow enough to remain a material responsiveness
risk for synchronous GUI work. The larger benchmark profile (50 habits, 10
fields, 1,095 days of history, and 1,000 notes) did not complete during this
verification run; no large-vault timings are available. The measurements are
synthetic and from one Linux host, so they do not predict performance on other
storage devices or platforms.

## Lock recovery and interrupted writes

The full suite's lock-recovery tests passed. Specifically, they exercised:

- A normal lock records a live owner and releases on exit; an exception also
  releases it.
- A child process terminated with `os._exit` leaves a diagnosable stale lock.
  Subsequent writes are blocked without changing canonical Markdown.
- Recovery is refused for a live owner, unidentified lock, wrong token,
  different host, or unexpected lock-directory contents.
- A dead same-machine owner can be recovered with its matching token; a write
  retry then succeeds. The CLI `lock-status` and `unlock --token` path was
  exercised as well.
- A process stopped before atomic replacement leaves the original document
  bytes intact and a recovery backup. An interrupted multi-file layout
  publication leaves dependencies discoverable but does not publish an active
  page assignment to an incomplete revision; retry is idempotent.

These are automated Linux tests using child processes and temporary vaults;
they do not establish behavior on every filesystem or platform.

## Limitations and remaining risks

- The large benchmark profile remains unmeasured. Medium-vault scans, saves,
  reindexing, and watcher refreshes block for seconds in this synchronous
  controller path and need further performance work before larger vaults can
  be considered responsive.
- The Phase 6.5A GUI verification used Qt offscreen/software rendering. The
  pointer/reopen regression additionally passed under XCB/software, but there
  was no human accessibility review and no Windows/macOS validation.
- GitHub Actions has not confirmed the fix. Remote CI can only be reported after
  a run against a revision containing this change.
- Lock identity/recovery evidence is strongest on Linux, where boot ID and
  process start time are available; portable filesystems and other operating
  systems need separate validation.

No Phase 6.5B or Phase 7 work is included in this delivery. The canonical
Markdown/YAML document contract and SQLite-as-rebuildable-cache policy were not
changed.
