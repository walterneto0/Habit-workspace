# Habit Workspace — Phase 7B: Content, Reflection and Scope-Cadence Consistency

> **Proposed repository path:** `docs/planning/phase-7b-direction.md`  
> **Status:** reviewed implementation direction; **not an implementation claim**.  
> **Baseline:** `main` at `cd2dbc486678f7dc3b5db22e4165ba92781549e1` (2026-10-31).  
> **Read alongside:** `AGENTS.md`, `PRODUCT.md`, `FILE_FORMAT.md`, `ARCHITECTURE.md`, `LAYOUT_ENGINE.md`, `DESIGN_SYSTEM.md`, `PRIVACY.md` and `ROADMAP.md`.

## 1. Purpose and constraints

Phase 7A implemented canonical tasks and goals, their direct forms and planning views, and task bindings to existing lists/checklists. Its PR #12 passed 313 pytest tests, Ruff checks and QML startup on GitHub Actions; the merged `main` workflow also passed. Phase 7B must extend this foundation without introducing parallel data stores, a second editor framework, or misleading UI promises.

The product's founding purpose is to help users organize responsibilities from the micro to the macro. This informs UX decisions but does **not** impose religious beliefs or language on users.

Phase 7B delivers: (1) an explicit policy for goal ownership, visibility and tracking cadence, correcting Phase 7A's implicit cross-period display; (2) full editable Markdown notes and page-local text regions; (3) reviews tied to one temporal period; (4) safe local raster asset ingestion and display. It does **not** deliver events, agenda, charts/rollups, automatic goal scoring, cloud features or Phase 9 packaging.

## 2. Product invariant — ownership is not tracking

**Three different concepts must never be conflated:**

- **Home period (`home_period_ref`)**: the primary temporal location of the item, such as `year/2026` or `week/2026-W44`. It is a logical UI association, **not** the file path or the identity of the document.
- **Temporal scope (`scope`)**: the start-inclusive, end-exclusive interval during which the item is relevant/eligible. A year-wide scope does **not** automatically create child-period entries.
- **Tracking cadence (`tracking`)**: an explicitly selected policy describing whether a goal is followed only in its home period or receives follow-up prompts/records at a smaller period scale.

A fourth idea, **query/display policy**, is distinct from both scope and cadence. Explicit search, deliberate binding or a user-selected global planning view may show a reference to an item outside its home period. Normal child pages must never inherit the full parent goal merely because dates intersect.

### Required behavior

| Example | Home period | Tracking selection | Ordinary child pages |
| --- | --- | --- | --- |
| Annual goal: "Read 24 books" | `year/2026` | Home period only | No automatic goal card on months, weeks or days |
| Annual goal reviewed monthly | `year/2026` | Monthly | A **linked monthly follow-up**, not a second goal, in relevant months; no automatic daily/weekly copy |
| Annual goal reviewed weekly | `year/2026` | Weekly | Linked follow-up for eligible ISO weeks; do not automatically list the full annual goal in each day |
| Annual goal reviewed daily | `year/2026` | Daily | Linked daily follow-up during its eligible dates |
| Monthly goal reviewed weekly | `month/2026-10` | Weekly | Follow-ups for eligible weeks only, including boundary weeks, with the scope intersection made explicit |
| Weekly goal | `week/2026-W44` | Home period only | Exists in the weekly view without automatic daily projection |

**Default for newly created goals: `home_only`.** The creation form must ask whether smaller-period follow-up is desired, offering only valid narrower choices; no need to force repetitive confirmation if the default is visible and understood. Users can change the policy later.

An annual goal's manually maintained overall `progress_percent` remains the current goal state; follow-up records must not create a second, contradictory authoritative current percentage. Before adding period-specific progress values, explicitly define whether they are historical snapshots, separate dated facts or the single source from which current progress is derived. This decision must be written in `FILE_FORMAT.md` and tested, not improvised in QML.

**Type-specific rules:**

- **Goals:** require a home period + explicit tracking policy; no implicit child visibility.
- **Tasks:** remain one-off canonical tasks with independent optional due dates and completion state. Do not create one checkbox per day simply because their scope intersects that day. A due-date reminder/agenda entry is a distinct projection, not a recurring task. The global planning search and clearly labeled carryover remain available.
- **Habits:** their existing `recurrence` and daily check-in semantics remain authoritative. Do not silently replace them with goal tracking. The long-term UI may use a common *choice of follow-up scale*, but never silently rewrite established habit occurrences.
- **Notes and reviews:** associated with a specific period by context; no automatic child-period replication. A review of a week is **not** seven daily reviews.

### Compatibility and schema direction

New goal file fields must be **additive** to schema v4 and must preserve unknown metadata. Before implementing, validate the proposal against all existing readers and write the final contract in `FILE_FORMAT.md`. Proposed conceptual shape (subject to contract review):

```yaml
hw:
  schema_version: 4
  kind: goal
  id: "00000000-0000-4000-8000-000000000001"
  title: "Read 24 books"
  scope:
    start: "2026-01-01"
    end_exclusive: "2027-01-01"
  home_period_ref: "year/2026"
  tracking:
    mode: home_only  # or periodic
    # granularity: month  # required only for periodic; month/week/day
  status: in_progress
  progress_percent: 25
```

This example is a **proposed format**, not a statement that runtime support already exists. `origin_page_id` continues to mean creation provenance; it must **not** be repurposed as `home_period_ref`.

Pre-7B goal documents have no `home_period_ref` or `tracking`. They must remain readable and discoverable. Define and test a deterministic, non-destructive legacy fallback. Prefer exact calendar-period inference from the scope when possible, clear labeling for ambiguous/custom scopes, and explicit user correction. Never silently rewrite old files or silently hide legacy items without discoverability in global planning/search.

The existing `application/planning.py::query_report()` uses scope intersection to display goals on smaller-period pages. **Fix this for goals.** Scope intersection remains valid for eligibility calculations and some explicit queries, but not as the default rule for goal ownership/visibility.

When following a goal across ISO weeks spanning two months/years, never record outside its eligible scope. One ISO week retains one stable identity (`week/YYYY-Www`); define the valid intersection rather than fabricating duplicate week entries.

## 3. Editable standalone notes

- Create, search, open, edit and reopen canonical `kind: note` Markdown documents directly, with an optional explicit period association.
- Provide a full-length editor and a safe, legible preview, not an editor initialized from the current **6,000-character excerpt** in `presentation/layout_studio.py`.
- Use existing `DocumentRepository`, `VaultSession.save`, optimistic revisions and `VaultTasks`. Preserve YAML metadata not managed by the editor, Markdown, BOM/newline policy and arbitrary external edits on conflict.
- Safe preview must not execute HTML, scripts or embedded remote resources; local image references must pass the vault/asset policy below.
- Drafts must remain recoverable in the open form after validation or stale-revision failures. Never overwrite an external editor's changes.

## 4. Page-local Markdown content regions

The current `FILE_FORMAT.md` shows regions such as:

```markdown
<!-- hw:content id="4484184e-42fd-4624-a23a-e19606c08955" -->
## Reflections
Free-form Markdown.
<!-- /hw:content -->
```

- Implement an exact, tested parser/editor for the existing marker syntax. Do not regex-replace arbitrary Markdown without checking structural validity.
- Resolve a note block's region identity deterministically: use the explicit `NoteConfig.content_id` when present; otherwise use that block's stable ID. Document this resolution in `FILE_FORMAT.md` before relying on it.
- Reject or safely disclose missing, duplicate, malformed, overlapping or nested regions; show original text read-only if the situation is ambiguous.
- Editing one region must preserve every byte/character outside that region to the extent permitted by the file serializer, and must preserve other regions unchanged.
- Editing a linked standalone note modifies that note's canonical document; editing a page-local region modifies the owning page. These are **two distinct editing targets** and must be clearly labeled.
- Layout revisions, block removal or movement never delete canonical content. Never write note text to layout JSON or SQLite as the only copy.
- Plain Markdown content must stay intelligible after the layout JSON is unavailable.

## 5. Reviews per exact period

Introduce `kind: review` only after documenting its schema and validation in `FILE_FORMAT.md`.

Minimum contract: UUID, title or appropriate display label, exactly one validated `PeriodRef` of scale year/month/ISO-week/day, optional tags, and canonical Markdown commentary. A review may include *explicitly defined* optional assessment values, but avoid phantom daily records or duplicated measurements. Decide the revision/concurrency and creation rules, including whether multiple reviews per period are allowed, before implementation.

A weekly review is one document associated with `week/YYYY-Www`, even if that week crosses a month. It does not become seven daily documents. A monthly review is not a collection of fabricated weekly/daily scores.

Support creation/editing/reopening and navigation from the exact period, search, readable empty states and conflict-safe async saving. Any review attached to a parent period should not automatically appear as a child-period review.

If a value has meaningful existing typed observation semantics, link it to the canonical field/observation rather than copying it. **Do not force week/month/year values into daily observations.** If no appropriate period-level typed-value contract exists, store commentary only or document a minimal properly typed review value with no competing source of truth. Automatic period analytics belongs to Phase 8.

## 6. Local image ingestion and display

Reuse the existing `ImageConfig` path validation and `presentation/layout_assets.py` bounded raster decoder; no remote fetches.

- File picker for supported PNG/JPEG/WebP/GIF. Validate actual image format, extension policy, file size, pixel dimensions and decode success before use.
- Import into `Assets/` via a validated, contained, non-symlink path. Use collision-safe filenames and avoid overwriting a different asset. Consider content-addressed naming only if it does not complicate compatibility.
- Preserve offline, vault-relative paths and alt text. Use a safe Markdown reference for note images; no absolute machine paths in canonical content.
- Avoid URL/local-file access through arbitrary Markdown or QML. Preview must resolve only permitted vault assets.
- Existing image decoder uses `read_bytes`' default 2 MiB limit and 4,000,000-pixel cap. Keep both unless explicitly justified and tested.
- Do not decode images repeatedly on every unrelated UI update. Use bounded caching or an async decode path **only** if profiling or interaction tests show it is needed; never block the GUI on large file copies.
- Missing or invalid assets must be reported without deleting the note or layout. Import does not imply full dependency-aware `.hwpack` export (Phase 9).
- When adding a media file and then updating a Markdown/layout reference, define safe partial-failure handling (e.g., an unreferenced asset may remain, but an invalid reference must not be silently accepted).

## 7. User experience and navigation

- Use the established Portuguese-Brazilian design system; preserve the current desktop shell and Layout Studio.
- Users must be able to edit notes, create reviews, select images and choose goal tracking **without requiring Layout Studio** for core operations.
- Notes and reviews should appear under their **chosen associated period**, never automatically cascade into every descendant period.
- Distinguish `Objetivo do ano` from `Acompanhamento mensal do objetivo` in user-facing copy. These are linked views of **one** canonical goal, not separate goal documents.
- Offer accessible keyboard navigation, focus retention, clear states and contextual return paths. Validation/conflict states must leave drafts intact.
- When users change an existing tracking policy, do not delete historical follow-up records or silently reinterpret them. Explain and test the compatibility behavior.

## 8. Implementation sequence within one PR

1. Correct current roadmap/readme statuses and document the goal home-period/tracking policy. Update `PRODUCT.md`, `FILE_FORMAT.md`, `ARCHITECTURE.md` and `LAYOUT_ENGINE.md` with final validated contracts.
2. Add regression tests proving an annual goal is not inherited by child pages without an explicit tracking selection; preserve task carryover and habitual recurrence.
3. Implement minimal goal visibility/cadence correction, with explicit follow-up UI and canonical storage **only if the data contract is finalized**. Do not show interactive tracking controls that do not persist.
4. Add direct full-length standalone note editing and page-local content-region editing.
5. Add reviews for exactly one selected period.
6. Add safe asset import and notes/layout integration.
7. Execute full regression, Qt offscreen and native X11 flows, report limitations, and stop.

This is **one Phase 7B delivery**, not six separately required PRs. However, contract validation and feature tests precede implementation to avoid a large late-stage schema rewrite.

A lower-period follow-up must be a working, persisted operation before its selection is presented as functional. If implementation cannot safely complete this within Phase 7B, report Phase 7B as **partially complete**, preserve the default home-only correction, and leave the unsupported choice unavailable. Do not claim Phase 7B acceptance until the explicitly offered tracking choices work end to end. Analytics and inferred progress remain Phase 8.

## 9. Acceptance tests / non-negotiable checks

1. A year-only goal is visible in its home year and global search, but **not** automatically in any month/week/day.
2. A monthly-tracked annual goal presents a linked monthly follow-up only where eligible; it does not create a second canonical goal or a daily check-in.
3. Creating a goal offers an understandable home-only vs valid smaller-period tracking choice; legacy documents remain readable and discoverable.
4. A task with year scope and a due date remains a one-off task; due-date navigation and carryover remain correct.
5. Habit recurrence and past/future check-in policy remain unchanged.
6. A note with more than 6,000 characters edits and reopens without truncation. BOM, CRLF, unknown metadata and concurrent external edits remain safe.
7. Editing one `hw:content` region leaves all other regions and surrounding Markdown unchanged; malformed/duplicate markers cannot overwrite content.
8. One ISO-week review remains one review, including a week that crosses months/years; no fabricated per-day measurements.
9. A raster image imports into `Assets/`, displays offline and reopens after index deletion/rebuild; invalid media, symlinks and paths cannot escape the vault.
10. Layout block removal does not remove notes, assets, reviews or goal state; unresolved references are visible.
11. Canonical data survives restart, external modification, reindex and cross-directory file moves where UUID references apply.
12. Ruff, full pytest, QML smoke and a real pointer/keyboard Phase 7B verification pass; clearly separate Linux X11 evidence from untested platforms and human accessibility review.

## 10. Boundaries, handoff and delivery report

**Do not implement:** events, recurring calendar entries, integrated agenda, chart rollups, automatic inferred goal progress, generic cross-provider sync, remote image downloads, `.hwpack` dependency export, backup UI, arbitrary plugins or an alternative data layer.

The implementer must report: changed paths; final on-disk contracts; compatibility rules for pre-7B records; tests with exact counts and commands; Qt platform results; remaining risks; and instructions for direct manual testing. Do not commit, push or open a PR without owner authorization.
