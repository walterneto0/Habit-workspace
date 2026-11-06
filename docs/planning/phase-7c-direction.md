# Habit Workspace — Phase 7C Implementation Direction

**Status:** reviewed proposal for the next implementation, **not a claim that Phase 7C is implemented**.  
**Source baseline:** `walterneto0/Habit-workspace`, `main` at `b33d57d52fafe75e064a23e8d27605ae4cfc4a11` (checked 2026-11-03).  
**Main CI:** successful, 359 tests in the merge run for Phase 7B.1.  
**Primary repository inputs:** `AGENTS.md`, `PRODUCT.md`, `ROADMAP.md`, `FILE_FORMAT.md`, `ARCHITECTURE.md`, `LAYOUT_ENGINE.md`, `PRIVACY.md`, `DESIGN_SYSTEM.md`, and the Phase 7B/7B.1 verification reports.

## 1. Mission and scope

Phase 7C completes the planning-and-agenda portion of Phase 7 through three features:

1. **Canonical one-off events** with valid, unambiguous date/time semantics and direct editing.
2. **Read-only unified agenda projections** from canonical events, one-off task deadlines and scheduled habit occurrences.
3. **User-selected transfer between existing local vaults**, with an explicit dependency preflight. This is *not* archive export, comprehensive backup, or restoration.

Maintain the file-first, offline, modular, local Qt/Python architecture and the existing minimalist Portuguese-Brazilian UI. `Markdown + YAML` remains canonical, `SQLite` a rebuildable cache, and layout JSON a separate presentation concern. Changes must retain the stable UUID/reference and optimistic-concurrency guarantees.

**Do not implement** event recurrence; reminders/notifications; CalDAV/iCalendar/cloud; timezone synchronization; speculative goal-progress aggregation; Phase 8 charts; Phase 9 `.hwpack`, full-vault backup, ZIP bundle extraction, general restore, installers, or mobile apps.

## 2. Reconciliation of current documentation

As of the baseline:

- `PRODUCT.md` § Evento requires start/end, timezone and all-day behavior, and explicitly says creation on a month page does **not** imply month-long duration.
- `PRODUCT.md` § Agenda requires a combined agenda of events, task `due_date` and scheduled habit occurrences with no duplicated canonical records.
- `ROADMAP.md` marks 7C as events, agenda and selected transfer with dependencies; it reserves `.hwpack` and broader backup/distribution for Phase 9.
- `FILE_FORMAT.md` shows `Items/Events/` as a prospective folder but does not validate a concrete `event` schema. `DocumentKind` does not yet contain `event`.
- `ImportService.import_files` currently imports standalone `.md` only, preserving UUIDs and disclosing some missing references; it is not a dependency-aware inter-vault transfer engine.

Before implementing, **document the final event schema and the transfer coverage matrix** in `FILE_FORMAT.md`, update the product text about all-day semantics, and cross-reference these decisions from `ARCHITECTURE.md`, `ROADMAP.md`, and `LAYOUT_ENGINE.md`. Do not replace historical verification reports or silently modify pre-7C files.

## 3. Event identity and canonical persistence

### 3.1 One event, one document

Use schema version 4, `kind: event`, a stable UUID, nonempty `title`, optional normalized tags, Markdown body, and optional `origin_page_id` for creation provenance. Use `Items/Events/<uuid>.md` as the default path but **never** use the path as the identity. Event time belongs to the event itself, not to its origin page, `home_period_ref`, or a default month/year scope. The app must require concrete event dates before saving.

**Recommended discriminated union** for event timing (implement only after reconciling with `PRODUCT.md`):

**Timed event:**

```yaml
hw:
  schema_version: 4
  kind: event
  id: "d9335796-61de-47b7-b164-8d9eb1962c84"
  title: "Study group"
  tags: [study]
  timing:
    kind: timed
    timezone: America/Recife
    starts_at: "2026-11-04T19:00:00-03:00"
    ends_at: "2026-11-04T20:30:00-03:00"
```

**All-day event:**

```yaml
hw:
  schema_version: 4
  kind: event
  id: "9d053f44-d5e4-4b15-84f1-9e0804f0832d"
  title: "Conference"
  timing:
    kind: all_day
    timezone: America/Recife
    start_date: "2026-11-04"
    end_date_exclusive: "2026-11-06"
```

**Important reconciliation:** `PRODUCT.md` generically names `starts_at`/`ends_at`. For timed events these are mandatory timezone-qualified instants. For all-day events, **civil start/end dates are the authority**; manufacturing midnight instants would create avoidable DST/portability errors. Update the product contract explicitly to explain the distinction rather than storing both date ranges and timestamp ranges as independent authorities. Every all-day event has `timezone` for civil context but must never shift to an adjacent day merely because the viewer changes timezone.

`hw.timing` is exactly one of the two kinds: no mixing timed fields and all-day fields. Do not silently normalize invalid, unknown or incomplete timing into another kind. Preserve unknown compatible metadata but reject conflicting known timing fields. Never migrate unrelated records merely by opening them.

### 3.2 Validation

- Timed `starts_at` and `ends_at` must be ISO-8601 offset-aware strings; strict UTC instant ordering `ends_at > starts_at`. Compare instants, **not string order**.
- `timezone` must be a real IANA timezone identifier that the runtime can resolve. Verify that each saved offset corresponds to that zone at the specified instant, including DST transitions. Reject nonexistent local wall times; expose the distinction for ambiguous fall-back times instead of silently choosing an offset. Explicit offset can disambiguate persisted values.
- All-day `start_date` and `end_date_exclusive` must be valid civil dates with a nonempty, half-open interval `[start_date, end_date_exclusive)`. A single all-day date ends at the *next date*, without persisting an artificial timestamp.
- A timed event crossing midnight is still one event. A multi-day all-day event is still one event. Intersections produce multiple **view rows**, never additional event files or occurrences.
- Reject malformed timestamps, missing timezone, reversed intervals, naive timestamps, impossible dates, unwanted recurrence metadata and unsupported timing kinds, while preserving original bytes in the vault on read errors.
- The UI must use Portuguese human-friendly date/time controls and available zone choices; users must not type YAML or internal identifiers. Display the saved event timezone and the chosen display-zone policy clearly.

### 3.3 Query/display timezone policy

For initial Phase 7C, use the **event's own timezone** to interpret and group timed events in the agenda. This deterministic policy works offline and is consistent across app sessions and machines. Do not silently render in a different machine timezone. A later preference for a user-selected display zone would need an explicit, separately documented conversion policy.

Query time intervals as half-open intervals. A timed event appears in each civil day it intersects **in its saved event timezone**. A timed event ending exactly at local midnight does not occupy the following day. All-day events occupy only their saved civil dates. A week crossing years (e.g. ISO `week/2026-W53`) is one period. A monthly page displays only its intersecting days, not an event's entire unrelated span.

If the product later requires *simultaneous* per-viewer timezone grouping across events, treat that as a separate design decision; do not quietly mix event-local and system-local date calculations.

## 4. Direct event UX and operations

Implement a direct **Novo evento** action and an accessible create/edit/details form, independent of Layout Studio. The form must include title, timed/all-day choice, start/end, timezone, optional tags and Markdown description. Provide sensible initial dates from the current page while **requiring** explicit concrete dates for a newly created event; opening an annual/monthly page must not create a year-long or month-long event by default. End defaults may be offered transparently but must be user-editable. Preserve incomplete drafts after validation failure or optimistic-revision conflict.

Use a typed, Qt-free event domain model and a revision-aware `EventService` over `VaultSession`. Use existing serialized `VaultTasks` rather than independent threads or a second store. Expose missing/corrupt/conflicting event records safely and keep them readable in ordinary Markdown editors. Implement search, details, cross-page navigation, restart, manual external-edit detection, and SQLite rebuild compatibility.

No arbitrary event recurrence, notifications, invitation handling or external calendar integration in 7C.

## 5. Unified agenda as a pure projection

### 5.1 Sources

Build a domain/application projection from a canonical `ScanReport` and a bounded `PeriodRef` query; **do not** create `kind: agenda`, daily copies, cached occurrences as canonical Markdown or independent task/habit data.

| Source | Inclusion | Identity and action |
| --- | --- | --- |
| One-off event | Relevant civil-day/period intersection under the documented event-zone rule | Canonical event UUID, edit/open event; distinguish timed vs all-day |
| One-off task | Exactly its `due_date` (independent of `scope`, completed or not) | Canonical task UUID; open same task, do not create a daily checkbox |
| Habit | Existing recurrence and `TemporalScope` schedule on eligible dates | Canonical habit UUID + projected date; call existing check-in action only when allowed |

Habit state comes from the existing capture/snapshot rules: `done`, explicitly `missed`, `skipped`, `unrecorded`, `pending`, `future`, `not_scheduled`. **Never** infer missed from missing a check-in. Missing habits with snapshot logs must be labeled as incomplete dependency rather than synthesized into new schedules. Task overdue is a separate label/filter, not a recurring task entry inserted on every day after the deadline.

### 5.2 Shape, sorting and UI

Use a stable immutable/JSON-friendly projection containing `source_kind`, `source_id`, `display_day`, type-specific `status`, `title`, optional start/end display, `conflict`/`missing` state and a deterministic navigation target. A repeated multi-day event may appear as one row per intersecting day in the agenda, but every row references the **same** canonical event UUID. Deduplicate by source type + UUID + projected civil day, never title, and do not mistake repeated display rows for new records.

Group agenda rows by day in year/month/week/day views, using pagination or bounded windows for large year queries. Within a day, sort all-day events first, then timed events by local start, then task deadlines, then scheduled habits; use stable UUID tie-breaks. Show human-friendly Portuguese labels and clearly distinguish **Evento**, **Prazo da tarefa**, and **Hábito programado**.

The agenda must be directly accessible in the normal workspace, not dependent on a custom Layout Studio widget; optional layout-block integration may reuse the read-only projection if supported without expanding Phase 7C into a generic calendar-framework redesign. Clicking a row must open/navigate to its original record and use its **existing** editing/capture workflow, with conflict protection.

Test multi-day, midnight-exclusive, leap-day, ISO cross-year, invalid event zone, overlapping events, due dates outside task scopes, task completion unchanged and absent vs explicit missed habit state.

## 6. Selective transfer between local vaults — explicit Phase 7C boundary

### 6.1 Supported workflow

**Transfer scope for Phase 7C:** choose one or more existing canonical documents from a source vault, select another **existing local destination vault**, preview dependencies, explicitly select which supporting items/assets/layout revisions to copy, confirm, copy only selected content, rescan/reindex destination and report results. The source is not modified and no network is used.

**Phase 9 remains responsible** for creating/reading `.hwpack` ZIP packages, full-vault backup/restore UI, dependency-complete transport archives, history packaging, comprehensive recovery/distribution and one-click device migration. 7C must not create a hidden alternative package format.

### 6.2 Dependency discovery and disclosure

A deterministic preview should classify:

- **Selected canonical Markdown documents**, including event/task/goal/habit/note/review/period page kinds supported by the current parser.
- **Referenced Markdown documents** using existing `Document.references()` / scanner reference roles and UUID identities (for example attached notes, referenced habits, task bindings).
- **Relevant layout JSON revisions** referenced by selected pages' `layout_history`, if selected for visual reconstruction; include their typed fields and other resolvable references when explicitly requested. If a layout cannot be transferred safely, identify that exact missing dependency and do **not** claim visual reconstruction.
- **Local asset files** referenced from selected Markdown note/image content and selected layout `ImageConfig` paths, using the existing strict contained-path and media validation. Assets are not silently copied unless explicitly selected.
- **Unresolvable, unsupported or ambiguous dependencies**, distinctly labeled. Do not fabricate replacement documents or silently rewrite UUIDs.

Resolve dependencies transitively for **supported** references, with deterministic visited sets, depth/item/byte limits, and cycle handling. Default should make dependencies clear and easy to include but must preserve a meaningful explicit selection and privacy preview. Never silently include unrelated notes, historical day pages, whole vaults or personal data just because a broad scope intersects a period. If the user excludes a dependency, disclose the destination's resulting missing reference before final confirmation.

### 6.3 Collision, integrity and partial failures

- A matching UUID with **identical bytes** is already present: skip/report.
- A matching UUID with different bytes or ambiguous identity: **block that item**, do not overwrite, silently merge or assign a fresh UUID.
- For asset paths, copy only validated local regular files with create-only atomic publication. On differing existing content at the same path, report an explicit conflict rather than silently overwriting or rewriting canonical references.
- Validate selected JSON layout revisions against existing schema and revision uniqueness. Never weaken layout-history invariants to make a transfer seem successful.
- Preflight source/destination identity (disallow same vault), hardlink/symlink/path traversal, paths, file formats, sizes, duplicate identities, destination collisions, destination read-only/locked conditions and explicit user consent.
- Use the existing writer lock and create-only atomic writes. **Multi-file atomicity is not guaranteed**: preflight before writing, then report imported/skipped/conflicted/failed items and any partial transfer. Do not delete preexisting destination files or auto-clean up unreferenced dependencies. Never claim transactional rollback without implementing and testing it.
- Copying a single Markdown file must continue to work through the existing import workflow. If transfer extends that importer, keep its duplicate/conflict semantics and original-byte/metadata behavior.

### 6.4 Minimum meaningful acceptance

Transfer a selected standalone note with an image into an empty existing vault and reopen it offline; transfer an event/task and ensure canonical UUIDs, time metadata and due date survive. Transfer a selected period page with its specific layout revision and explicitly selected supporting sources; verify accurate reconstruction **only for dependencies actually transferred**. When an item is omitted, show an explicit missing-dependency warning. Test same-UUID/different-content, identical copies, symlink/traversal, malformed source, crash/partial failure and reindex/restart.

If the implementation cannot safely support some dependency kind (e.g. layout history) in 7C, keep its selection visibly unsupported, report that part as **incomplete**, and preserve Phase 9's separate guarantees. Do not advertise a fully reconstructed page unless the transferred graph actually supports it.

## 7. Implementation order and stage boundaries

Use a single eventual Phase 7C PR, but two bounded Codex executions:

**Execution 1 — Event + agenda:** final schema/doc changes, domain validation, `EventService`, direct QML creation/editing, agenda projection and workspace UI, regression tests/GUI evidence. Stop and report `docs/verification/phase-7c-execution-1.md`. This is a checkpoint, not Phase 7C acceptance.

**Execution 2 — Selective transfer + integration:** dependency preflight, explicit local destination/selection UI, safe copies, conflict reporting, integration with new events/agenda, all relevant docs, full regression and GUI verification; report `docs/verification/phase-7c-final.md` and stop for review. It is acceptable to split internally into smaller commits **after** the owner authorizes commits, but do not create extra PRs by default.

Both stages must respect existing docs, the current QML visual identity, Qt-free domain code and worker serialization. Do not commit, push, open a PR or merge without explicit authorization.

## 8. Non-negotiable verification

1. Timed, all-day and multi-day event creation/editing round trips with timezone and invalid-DST handling.
2. Timed events query and display correctly at midnight and DST boundaries; year/month/week/day projections use the documented timezone rule.
3. Event creation on an annual/monthly page does not default its duration to that whole page.
4. Agenda event, task and habit rows are derived from **one canonical source each**, navigable and not duplicated as new documents.
5. Task deadline is not a daily repeating task; task status/carryover and goal tracking remain unchanged.
6. Habit missing check-in is never marked `missed`, including after a restart or deleted index.
7. ISO weeks crossing year boundaries, events crossing dates, invalid source records and UUID conflicts produce correct results.
8. Transfer preview enumerates document/layout/asset dependencies and unresolved references, respects explicit selection, and transmits no unrelated private data.
9. Identical and conflicting UUIDs, different asset bytes, unsafe paths/symlinks and partial failure are safely handled.
10. Restart, external edits, path moves (where UUID applies) and index deletion/rebuild retain canonical results.
11. Ruff, format, `git diff --check`, full pytest, QML smoke and dedicated offscreen/X11 pointer/keyboard journeys pass; exact results are reported, no invented claims.
12. Windows/macOS and human accessibility approval must remain unclaimed unless actually tested.

## 9. Completion and owner handoff

The final report must include final schemas (examples + field validation), timezone display policy, reference/dependency transfer coverage matrix, changed files, exact test commands/counts, GUI/platform results, unresolved and unsupported cases, manual reproduction using disposable vaults and suggested commit/PR text. Mark Phase 7C complete **only** when events, agenda and the stated selective-transfer workflow work end to end. Do not equate passing tests with owner UX acceptance.
