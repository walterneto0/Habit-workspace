# Phase 7C — Execution 1 completion

Date: 2026-11-03. Branch: `feat/phase-7c-events-agenda-transfer`.
Baseline HEAD: `b33d57d52fafe75e064a23e8d27605ae4cfc4a11`.
Continued the existing partial implementation; no reset, stash, commit, push, PR
or merge. Existing untracked direction documents and `habit_workspace_phase7c/`
were preserved. No dependency was added.

## Status and scope

Event and agenda workflows are implemented, including the completion requested
for timezone selection, grouped presentation and contextual navigation. Final
verification results and the acceptance decision appear below. This is the
Execution 1 checkpoint only: Phase 7C still requires selected transfer in
Execution 2, which has not been started. No `.hwpack`, backup/export, event
recurrence, notification, sync, cloud, analytics, charts or packaging was added.

## Final canonical event contract

Schema version **4**, `hw.kind: event`, stable UUID `id`, nonempty `title`, optional
string-list `tags`, optional UUID `origin_page_id` for provenance, Markdown body.
Default path: `Items/Events/<UUID>.md`. Moving a file never changes identity.
Exactly one authoritative timing interval is stored:

```yaml
hw:
  schema_version: 4
  kind: event
  id: "d9335796-61de-47b7-b164-8d9eb1962c84"
  title: Study group
  tags: [study]
  timing:
    kind: timed
    timezone: America/Recife
    starts_at: "2026-11-04T19:00:00-03:00"
    ends_at: "2026-11-04T20:30:00-03:00"
```

An all-day event uses this timing mapping instead:

```yaml
  timing:
    kind: all_day
    timezone: America/Recife
    start_date: "2026-12-31"
    end_date_exclusive: "2027-01-03"
```

Both intervals are half-open. Timed endpoints are ISO strings with explicit
offsets matching the IANA zone at each instant; UTC end must strictly follow UTC
start. All-day dates are civil ISO strings with exclusive end strictly after
start; they have no parallel midnight timestamp authority. Mixed known timing
fields, naive timestamps, invalid zones/dates, unsupported timing kinds and
recurrence are rejected. Invalid source bytes remain intact. Compatible unknown
metadata, Markdown and old supported documents survive round trips; opening does
not migrate unrelated documents. Application writes normalize tags.

The discriminated union from the first checkpoint is unchanged. Fold selections,
zone search and system defaults are transient UI data, not extra canonical fields.
Typed immutable projections are parsed from the validated complete Document.
Persistence always validates the Document before atomic writing.

## Timezone and DST policy

- New forms suggest the system's IANA ID using existing `QTimeZone`, checked by
  Python `ZoneInfo`. If unavailable, explicitly labeled UTC is suggested for
  correction. Existing events always open with their saved zone.
- Search available IANA zones by city/region (spaces match underscores), select a
  result, and see the exact selected ID. The form explains that changing a zone
  retains the entered wall hours; the user reviews before saving.
- Portuguese dates use `DD/MM/AAAA`; local times use `HH:MM` (existing seconds and
  fractional seconds are retained when reopening). Ordinary times resolve
  automatically. There is no raw-offset entry workflow.
- Resolve both fold candidates through UTC and back to the same wall time.
  Nonexistent times have zero candidates and are rejected without adjustment.
  Repeated times have two distinct candidates and require an explicit first/second
  occurrence choice, labeled with the UTC offset. Stale choices cannot resolve
  a different repeated wall time. Saved offsets restore the existing choice.
- All-day forms request the inclusive last day but persist only the next civil
  date as exclusive end. They never manufacture timestamps or shift dates with
  the system timezone.
- Month/year context suggests one concrete initial day and a one-hour timed
  interval, never an event occupying that whole page. All dates remain editable.
- Validation, parsing and optimistic-concurrency errors keep the entire draft.
  External edits and duplicate/moved identity conflicts never overwrite files.

Uses Python `zoneinfo` and the already installed Qt system API; no timezone
service or additional timezone dependency. Available rules depend on the local
runtime's IANA database; unavailable IDs are visibly rejected.

## Agenda and navigation rules

Agenda is an in-memory read-only `ScanReport` projection. Each query covers at
most **31 civil days**, clipped to the selected year/month/ISO-week/day. Pagination
shows its date range and enables only available previous/next windows. Changing
the period resets the window. Grouping reuses those rows without another scan.

Portuguese weekday/full-date headings group rows. Within each day: all-day events,
timed events by local start with instant/UUID tie breaks, exact task deadlines,
then scheduled habits by UUID. Continuations sort from 00:00. Multi-day events
retain a single canonical UUID and show their original span, daily start/end and
continuation text. Midnight-exclusive ends never occupy the next day. ISO
`week/2026-W53` includes dates in 2027 with their correct civil headings.

Every event is grouped in **its saved event timezone**, which is shown alongside
the interval; no viewer/system timezone conversion is silently mixed in. All-day
events are explicitly labeled and precede timed events. Task deadlines appear
only on `due_date`, independently of scope and completion. No task/daily checkbox
copies are created. Habits use their existing scope/recurrence and explicit
check-in contracts; missing logs are unrecorded/pending/future, never inferred
missed. Only an explicit `missed` log displays Falha declarada.

Rows retain source kind, UUID and projected date. Duplicate identities/records
are visibly flagged. A missing habit's saved check-in snapshot appears only on
its recorded date as an incomplete dependency, never as a reconstructed schedule.

- **Event:** opens its canonical revision-bearing event form.
- **Task deadline:** opens the existing planning editor for the original task.
- **Habit occurrence:** navigates to that exact day and selects the original habit
  UUID; its detail/capture state uses that day. Opening does not create a habit,
  day page or check-in. Missing, ambiguous or no-longer-scheduled references show
  an explicit notice; no replacement is fabricated.

Event writes use existing serialized `VaultTasks` and a worker-owned VaultSession.
No second store, thread pool or canonical agenda records. Goal home/cadence,
layout assignments and existing habit capture remain under their prior contracts.

## Files changed across Execution 1

| Area | Files |
| --- | --- |
| Domain/schema | `domain/events.py`, `domain/documents.py` |
| Application | `application/events.py`, `application/agenda.py` |
| Presentation | `presentation/events.py`, `controllers.py`, `capture_actions.py`, `vault_tasks.py` |
| QML | `EventDialog.qml`, `PlanningPanel.qml`, `Main.qml` |
| Tests/tools | `tests/test_events_agenda.py`, `tests/test_event_workflows.py`, `tests/test_event_gui.py`, `tools/verify_phase7c_events.py` |
| Contracts/design | `PRODUCT.md`, `FILE_FORMAT.md`, `ARCHITECTURE.md`, `LAYOUT_ENGINE.md`, `DESIGN_SYSTEM.md`, `ROADMAP.md` |
| Evidence | this report |

The direction document and the user's supplied prompt directory were already
untracked on entry and remain preserved. No historical Phase 7A/7B/7B.1 report
was rewritten.

## Verification coverage

The previous checkpoint had **374 passing tests**, but incomplete timezone UX,
day headings and occurrence navigation. This continuation adds 10 focused
workflow/domain tests and one complete GUI subprocess test, retaining the 15
initial event/agenda cases and all 359 baseline tests.

Focused coverage includes IANA default/correction/persistence; invalid zones;
ordinary times, DST gaps, both fold instants and Lord Howe's half-hour fold;
Samoa's skipped civil day; timed/all-day/multi-day intervals; midnight exclusivity;
chronology; Portuguese groups; task deadline outside scope with one canonical
task; exact habit UUID/day navigation; missing snapshots and duplicate check-ins;
ISO cross-year periods; pagination resets; moved UUID identity; optimistic
conflicts and drafts; restart and deleted-index reconstruction.

The rendered journey runs actual pointer/key input at **800×640** and **1200×900**:
creates/reopens a timed IANA event, preserves a draft after an external edit,
creates an all-day three-day event, rejects a DST gap, chooses a fold explicitly,
checks day headings/continuation times, opens a task deadline, navigates a habit
to its original UUID/date, verifies no generated check-ins/day documents, and
starts a fresh application process after deleting the disposable SQLite index.
It also checks month/year navigation and the bounded window after restart.

Executed offscreen and native Linux X11 (`xcb`, software Qt Quick backend), with
**zero QML warnings** in both initial and fresh-process journeys. The X11 run used
approved escalation to access the local display. Both runs reported two timed
display rows, three all-day display rows and four canonical documents total
(two events, one task, one habit), with task and habit navigation confirmed.

Screenshots were generated from synthetic data and inspected:

- `/tmp/habit-workspace-phase7c/xcb/small-event-form.png`
- `/tmp/habit-workspace-phase7c/xcb/agenda.png`
- `/tmp/habit-workspace-phase7c/xcb/restarted.png`
- matching files under `/tmp/habit-workspace-phase7c/offscreen/`.

The small form keeps actions visible while contents scroll; grouped agenda rows
and event zones are readable. This is automated/render inspection, not owner
visual approval or human accessibility certification.

## Remaining limits

- No Windows/macOS execution or human screen-reader/accessibility approval.
- Source count per day is not capped; time queries are bounded to 31 days and
  grouping is linear in returned rows. No very-large-vault latency guarantee.
- Zone search uses IANA city names; translated aliases such as Lisboa are not a
  separate timezone database (the hint shows Lisbon). Unknown zones require local
  correction rather than downloading rules.
- Domain dataclasses are projection DTOs, not an alternate persistence API;
  canonical validation is Document/event_from_mapping plus the safe service.
- No selective transfer or dependency-copy coverage is claimed. Execution 2 and
  Phase 9 retain their separate scopes. Phase 7C as a whole is not complete.

## Manual acceptance

1. Create a disposable vault and navigate to December 2026. Select Novo evento,
   search Recife and select `America/Recife`. Set 31/12/2026 23:00 through
   01/01/2027 02:00, save and reopen; check the saved zone and dates.
2. Create a Dia inteiro event from 31/12/2026 through 02/01/2027. Open the week
   containing 01/01/2027: inspect headings, all-day ordering and continuation rows.
3. Search New York (`America/New_York`). Try 08/03/2026 02:30: saving must explain
   the nonexistent time and retain the draft. Try 01/11/2026 01:30: explicitly
   choose first or second occurrence, then save a valid later end.
4. Open an existing task from its deadline row. Open a scheduled habit on a past
   date and confirm the original UUID and that exact day's Sem registro state.
   Opening either row must not create canonical documents or logs.
5. Keep an event form open, edit its Markdown externally, and attempt Save. Confirm
   the conflict retains your draft and the external bytes. Cancel/reopen to review.
6. Close the application. In this disposable vault only, delete
   `.habit-workspace/index.sqlite`. Reopen and compare events, task deadlines,
   habit states and UUIDs. Exercise year/month/week/day navigation and pagination.
7. Resize to 800×640; use Tab/Shift+Tab, dropdown keyboard controls, pointer actions
   and explicit Save/Cancel. Review themes and accessibility before owner approval.

Automated journey command:
`QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python tools/verify_phase7c_events.py`.
Native equivalent uses `QT_QPA_PLATFORM=xcb`.

## Final exact commands and results

All final commands exited **0**:

| Command | Executed result |
| --- | --- |
| `.venv/bin/python -m ruff check .` | `All checks passed!` |
| `.venv/bin/python -m ruff format --check .` | `150 files already formatted` |
| `git diff --check` | No output |
| `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python -m pytest -q` | **385 passed in 106.87s (0:01:46)** |
| `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python -m habit_workspace --smoke-test` | `Habit Workspace: QML smoke test passed (one visible root window).` No QML warnings. |
| `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python tools/verify_phase7c_events.py` | Initial + fresh-process journey passed; `qmlWarnings: []` for both. Also executed by `tests/test_event_gui.py` in the final full suite. |
| `QT_QPA_PLATFORM=xcb QT_QUICK_BACKEND=software .venv/bin/python tools/verify_phase7c_events.py` | Native X11 initial + fresh-process journey passed; `qmlWarnings: []` for both. |

385 = 359 baseline + 15 initial event/agenda cases + 10 completion workflow cases
+ 1 full GUI subprocess case. The full suite includes the existing Phase 7A,
7B and 7B.1 regression and rendered journeys; they were not skipped. No code was
edited while the final full suite ran; only documentation was updated.

## Execution 1 acceptance decision

**Every requested Execution 1 implementation and automated verification criterion
has been met. Execution 1 is complete and stopped for owner review.** This is
technical acceptance of this execution, not human UX/platform approval or
completion of Phase 7C's separate Execution 2 transfer workflow.

| Criterion | Evidence/result |
| --- | --- |
| Unchanged canonical discriminated event timing, unknown metadata and old documents | Initial round-trip/schema tests plus full regression suite passed |
| IANA selection, local default/correction and saved-zone retention | Workflow tests and pointer/keyboard selection journey passed |
| DST gaps and explicit fold resolution, draft preservation | New York and Lord Howe tests; rendered gap/fold/conflict journey passed |
| Timed/all-day/multi-day workflows | Round trips, civil/exclusive boundaries and rendered creation/reopen passed |
| Grouped Portuguese agenda, chronological ordering and type labels | Group/order tests and rendered day-heading/interval assertions passed |
| Tasks on exact deadlines without copies | Out-of-scope deadline and original-task GUI navigation passed |
| Habit UUID + exact occurrence-day navigation, no inferred missed | Backend + rendered navigation/unchanged-file assertions passed |
| Missing/ambiguous references and recorded snapshot disclosure | Missing snapshot, UUID and duplicate-check-in tests passed |
| ISO week/year boundaries and bounded pagination | Cross-year week, period-reset tests and rendered navigation passed |
| External edits, moved UUID identity, restart and rebuilt index | Revision/conflict/move tests plus fresh-process deleted-index journey passed |
| QML pointer/keyboard and small windows | Offscreen + native X11 journeys at 800×640 and 1200×900 passed |
| Preserve goals/cadence/layouts/capture and prior phases | Full **385-test** suite passed |

No commit/PR was created. Suggested future review title, if separately authorized:
`feat: add canonical events and grouped contextual agenda (Phase 7C Execution 1)`.
