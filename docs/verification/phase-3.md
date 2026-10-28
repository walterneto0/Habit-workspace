# Phase 3 — Temporal domain and canonical entities

Implemented on 2026-10-28. Work stops at Phase 3. No commits, pushes, new
dependencies, network services, Layout Studio, metric/layout engine, analytics,
or check-in capture interface were introduced. The approved Phase 2 QML files
and design tokens are unchanged.

## Delivered contracts

| Class / interface | Responsibility |
| --- | --- |
| `PeriodRef`, `PeriodScale` | Parse/serialize canonical year, month, ISO week and day identities; boundaries, ordering, intersections and containing-period lookup, independent of paths |
| `TemporalScope` | Validated inclusive start/exclusive optional end, period defaults, explicit inclusive-date adapter, inclusion and intersection |
| `Recurrence`, `RecurrenceKind` | Daily or selected ISO weekdays; finite, lazy, scope-clipped occurrence generation |
| `Habit` | Immutable UUID, name, normalized tags, scope, recurrence, optional origin UUID and timezone-aware archival metadata |
| `LoadedHabit` | Typed habit with the original document and filesystem revision for optimistic edits |
| `HabitService` | Create, UUID-load, update and query habits through Phase 1 vault services; no canonical completion writes |
| `HabitQuery`, `HabitPeriod`, `Occurrence`, `RecordedCheckin` | Typed read projections distinguishing validity, schedule, explicit results, absent records, unavailable dependencies and records outside the current schedule |
| `HistoryImpactError` | Reviewable list of existing records made ineligible by a proposed scope or recurrence edit |

`vault/habits.py` maps typed fields onto the existing document. New habits use
schema v4; existing v1 and v4 habits retain their version. Unknown metadata inside
scope/recurrence and elsewhere, Markdown, supported comments, BOM and line endings
survive edits. The optional `archived_at` field specified by the product contract
is now validated and documented. No migration, activation date or second source
of habit/check-in truth is invented.

`HabitService.update` keeps the loaded revision and delegates to the existing
atomic writer, conflict checks and recovery copies. After reviewing a
`HistoryImpactError`, a caller can explicitly retry with
`acknowledge_history=True`. This acknowledges the impact only: daily records
remain byte-for-byte intact, and become visible in `unscheduled_records` rather
than scheduled outcomes. Restoring eligibility restores their query projection.

The existing period document list shows scope-intersecting habit definitions
using the current scan. Year/month/week/day navigation shares `PeriodRef` and
performs no new scan, writes or occurrence expansion. An active habit may have
zero scheduled dates in a view (for example a weekday habit in a Saturday view).
No full checklist UI has been added.

## Actual verification results

| Command / check | Result |
| --- | --- |
| Initial new contract tests, before feature modules | Expected collection failures for the two missing modules |
| New desktop habit-visibility test, before integration | Expected failure: habit absent from period list |
| `.venv/bin/python -m pytest -q` (final code) | **129 passed in 14.83s**, no failures or skips |
| `.venv/bin/python -m ruff check .` | All checks passed |
| `.venv/bin/python -m ruff format --check .` | Passed (54 files already formatted on final check) |
| `git diff --check` | Passed |
| `.venv/bin/python tools/verify_phase1.py` | PASS: import bytes, move/reference identity, cache rebuild and external edit refresh |
| `.venv/bin/python tools/verify_phase3.py` | PASS: real-file scenario, history preservation, move/reopen/rebuild, partial import and later dependency resolution |
| QML startup subprocess in pytest | Passed: one visible root window, clean exit |
| Existing `tools/verify_phase2.py` subprocess in pytest | PASS: offscreen/software desktop interaction and rendering, zero QML warnings, 17 captures |
| `.venv/bin/pyside6-qmllint -W 0 -i src/habit_workspace/presentation/qml/qmldir src/habit_workspace/presentation/qml/*.qml` | Passed, no diagnostics |
| Qt-independent application import subprocess | Passed, including the new habit service; no PySide6 imports or filesystem side effects |

The full suite includes all existing Phase 1 and Phase 2 tests. Existing v1 habit
fixtures and v4 notes/pages remain readable. A v1 habit with comments, CRLF, BOM,
archival metadata, nested extensions and human Markdown was edited through the
new service without losing those values or changing its version.

Generated captures from the final suite are at
`/tmp/pytest-of-me/pytest-21/test_desktop_input_and_render_0/screens/` (temporary,
not committed). `week-dark.png` and `calendar-light.png` were visually inspected;
the existing period layout and styling remain intact. These are software/offscreen
checks, not renewed native-desktop visual approval. Native window-manager/GPU,
HiDPI, accessibility, Windows and macOS behavior were not newly validated.
No private user vault was used; all data was generated in temporary directories.

## Required acceptance coverage

| Requirement | Evidence |
| --- | --- |
| Valid/invalid canonical identifiers | Parameterized `test_temporal.py`: malformed padding, dates, types, unknown scales and week numbers rejected |
| Leap years/month boundaries | February 2024, invalid February 2026, December rollover, 366-day/29-day daily recurrence counts |
| ISO week 53 and year crossing | 2026-W53 = Dec 28–Jan 3; 2020-W01 starts Dec 30, 2019; invalid 2025-W53 rejected |
| 2026-W44 | Oct 26–Nov 1 inclusive, exclusive end Nov 2; same identity in October and November |
| Four default scopes | Both domain and persisted habit creation parameterized across year/month/week/day |
| Custom/open scopes | Inclusive-end conversion, no-end validity, disjoint/touching intersections, override at creation |
| Daily/weekday recurrence | Monday=1 through Sunday=7, selected-day validation, clipping and cross-month/year tests |
| Bounded querying | Unbounded query rejected immediately; large bounded range consumed lazily with `islice` |
| Scope/recurrence edits preserve identity/history | Impact acknowledgement, unchanged daily file bytes, restoration and recurrence-only impact tests |
| One entity across views | Service queries and desktop controller return one UUID; navigation performs neither I/O nor occurrence generation |
| Persistence/restart | Real Markdown reload and equivalent query after a new `VaultSession` |
| Move/rename and references | Stale loaded handle rejected; fresh UUID load follows moved file; demonstration retains daily/origin references |
| SQLite reconstruction | Delete `index.sqlite`, reopen, compare query results, file bytes and one indexed habit UUID |
| Missing records never become failures | `unrecorded`, `pending`, `future` with `record=None`; imported explicit `done` read from the daily file |
| Missing dependency/import | Daily page alone yields unresolved record and missing-reference diagnostics; later habit import resolves UUID |
| Conflict/safety regression | Duplicate habits, duplicate check-ins across daily files, stale external edits, cache failure, existing unsafe-input and atomic-write tests |
| Unknown metadata/round-trip | v1 preserved, Markdown/comments/BOM/CRLF retained, nested extensions retained, obsolete known weekday list removed on explicit switch to daily |
| Tag identity | Unicode NFC/case/whitespace collisions deduplicated within a habit; separate habit UUIDs never merged |

Both Phase 3 acceptance criteria in `ROADMAP.md` are satisfied: a habit appears
in relevant temporal views without a duplicated canonical file, and moving or
renaming its file does not break UUID references. Notes/pages continue using
their existing contracts; tasks, goals, events and reviews remain in Phase 7.

## Real canonical-file demonstration

Run:

```bash
.venv/bin/python tools/verify_phase3.py
```

The demonstration creates two temporary vaults and prints the actual habit
Markdown with its UUID and origin reference. Generated fixtures are removed on
exit. It does not modify an existing user vault.

1. Create from `day/2026-10-27`: scope `[2026-10-27, 2026-10-28)`.
2. Expand through December 31: scope `[2026-10-27, 2027-01-01)` with weekdays 1–5.
3. Query year/month/week/day: all reference one UUID and one habit file.
4. Expected dates in W44: **October 27, 28, 29, 30**. Full expanded scope:
   **48 weekdays**. No completion records are created by these operations.
5. Add a generated pre-existing daily record fixture for October 29. At the
   deterministic query date October 29, W44 states are `unrecorded`, `unrecorded`,
   `done`, `future`. Only `done` has an actual recorded check-in.
6. Shorten validity: receive an impact warning; explicitly acknowledge and verify
   the original daily file is unchanged and the record is separately disclosed.
7. Restore scope, move the habit into an unrelated folder, reopen and rebuild the
   deleted index: UUID references, canonical bytes and temporal results match.
8. Import the daily page alone into the second vault: show the snapshot and missing
   dependency. Import the habit/origin afterward: resolve without recreating logs.

## Files created and modified

Created:

- `src/habit_workspace/domain/temporal.py`
- `src/habit_workspace/domain/habits.py`
- `src/habit_workspace/vault/habits.py`
- `src/habit_workspace/application/habits.py`
- `tests/test_temporal.py`
- `tests/test_habits.py`
- `tools/verify_phase3.py`
- `docs/verification/phase-3.md`

Modified:

- `src/habit_workspace/domain/documents.py`: shared period parser and archival validation.
- `src/habit_workspace/presentation/navigation.py`: shared domain period identity/boundaries.
- `src/habit_workspace/presentation/controllers.py`: in-memory scope filtering in existing lists.
- `tests/test_desktop_controller.py`: cross-view visibility/no-I/O regression.
- `tests/test_package.py`: Qt-free new application-service import.
- `FILE_FORMAT.md`, `ARCHITECTURE.md`, `README.md`, `ROADMAP.md`: implemented profile, service use, limits and acceptance status.

## Limits and architectural risks

- No Phase 3 acceptance requirement is deferred. Full capture, layout and analytics
  behavior remains intentionally outside this phase.
- Full file operations/queries remain synchronous, use one scan per query and are
  not benchmarked for large vaults. Future QML occurrence binding must use a
  worker-owned session. The added navigation filter does no file I/O or recurrence
  expansion, but existing Phase 1/2 watcher/import/reindex work is still synchronous.
- Current scope/recurrence are not a versioned historical schedule. Explicit
  historical records are preserved; results reflect the current definition.
  `archived_at` is exposed without silently shortening scope or excluding history.
- Python civil dates and the established four-digit file format cannot represent
  an exclusive year-10000 boundary. Such calculations raise a clear range error;
  year-9999 documents still parse and remain readable. Desktop years remain 2–9998.
- Existing portable-filesystem optimistic-write race limits still apply. The
  history-impact scan and habit save are not a multi-document transaction; a
  concurrently added daily record may require a refreshed impact review. Daily
  files are never rewritten by habit edits.
- Queries expose invalid-file/missing-reference diagnostics and cache errors;
  ambiguous definitions/check-ins raise conflicts rather than selecting a winner.
  Existing unknown extensions remain inert and cannot contribute interpreted
  dependencies without a future explicit schema contract.

Phase 4 has not started.
