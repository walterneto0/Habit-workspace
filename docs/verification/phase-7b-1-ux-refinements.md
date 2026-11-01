# Phase 7B.1 — UX and integration refinements

Verified 2026-10-31 on `fix/phase-7b-ux-refinements`, based on merged
`main` / `104754cf9bbea39244f58c4197d05b0899b9ad87`. The initial working tree
was clean. No commits, pushes or pull requests were created. All vaults, images
and preferences used for verification were disposable synthetic fixtures.

## Changes and confirmed causes

- Nested `LayoutComposition` Loaders forwarded planning/capture signals but
  omitted `editContent`. Forwarding that signal at every recursive Loader now
  opens the existing single editor for nested notes. The original region UUID
  and linked document UUID pass through unchanged. Explicit `content_id`, fallback
  block ID and standalone bindings all use the existing save pipeline.
- Goal/content forms previously asked for raw canonical period identifiers.
  `PeriodSelector.qml` reuses `Input` and `StudioChoice`, with a small Python
  `PeriodChoices` adapter over `PeriodRef`. It offers Ano/Mês/Semana/Dia, a year,
  named months and concrete weeks/days with Portuguese date labels.
- Goal tracking was reconstructed from the index in a changing options list.
  The draft now retains the selected policy independently of that list. Editing
  the home period cannot silently select another policy. Incompatible policies
  show a warning, offer only valid replacements, and fail validation before
  dispatch without losing title/body/scope/home/cadence drafts. New goals retain
  `home_only`. Scope dates are never changed by the selector.
- Reviews keep one exact selected period. For example, changing week 53's year
  to a year without week 53 leaves the selection invalid; it cannot become week
  52 implicitly. Existing note/review associations initialize from their own
  metadata, including no association. New forms use the current page when one
  exists. Reviews opened outside a period page require an explicit selection;
  standalone notes can choose **Sem período associado**.
- Cold image reads/decodes and full-resolution PNG re-encoding occurred inside
  GUI composition. The bounded cache avoided repeat application decodes but did
  not prevent large data-URL transfer/rendering costs on later navigation.
  Measurements below justified moving cache misses to `VaultTasks`, bounding
  display previews to 1024 px and enabling asynchronous QML Images.
- Image-only external changes do not change the document scan fingerprint.
  Unchanged refresh completion now revalidates visible asset revisions as well.
  The import callback also dispatches Markdown image preview work to the worker
  instead of potentially decoding other cold note images on the GUI thread.

Content forms scroll with persistent save/cancel actions at small desktop sizes;
the existing themed checkbox is reused for safe preview. Tracking has a visible
**Acompanhar** label. Follow-up headings also use readable period labels.

## Persistence, safety and async decisions

There are no canonical schema changes, migrations or new persistence paths.
`PeriodRef` strings, goal `home_period_ref`/`tracking`, note/review `hw.period`,
stable UUIDs, optimistic revisions and Markdown regions retain their existing
contracts. No text, assessment or image bytes become canonical in SQLite/layout
JSON. Historical verification reports were left intact.

`LayoutMedia` validates contained paths and revision metadata before returning
even cached pixels. Misses use the existing serialized vault worker. Page and
Studio contexts each coalesce one pending request; accepted writes and refreshes
have priority over pending media. Media reads do not mark the form as saving.
Generation tokens reject superseded requests; current revision keys reject
results after asset edits. A media completion never installs its document scan
over newer GUI state. Shutdown retains the established accepted-write contract.
Workers create only local decoder objects and transfer inert strings, not GUI
objects/QPixmaps.

The original 2 MiB and 4,000,000-pixel validation limits remain, checked before
scaling. Display previews are at most 1024 px on the longest edge; original files
are unchanged. The encoded-pixel LRU remains 64 MiB; a media batch and each display
context also have a 64 MiB payload budget. Overflow is visible, not an unbounded
retry loop. Markdown previews retain the existing maximum of 64 image links.

## Automated results

Final full suite: **359 passed in 102.31 s**, versus the supplied 342-test baseline
(17 new cases). No failures or skips were reported.

| Command | Result |
| --- | --- |
| `.venv/bin/python -m ruff check .` | All checks passed |
| `.venv/bin/python -m ruff format --check .` | 137 files already formatted |
| `git diff --check` | Passed, no output |
| `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python -m pytest -q` | 359 passed in 102.31 s |
| `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python -m habit_workspace --smoke-test` | QML smoke test passed; one visible root window |

New coverage:

- `tests/test_phase7b1_qml.py`: two rendered subprocess cases, at one and three
  nested section levels. Each activates three note buttons with pointer events,
  checks that only one editor is visible and verifies exact editor targets.
  Both explicit and implicit page regions and a linked standalone note are saved
  through the existing editor after publishing/reloading a layout. A fresh
  application process reopens them after deleting/rebuilding `index.sqlite`.
- The same journeys use keyboard calendar/cadence controls, preserve an invalid
  goal policy draft, retain the home-only default, serialize a selected home and
  monthly cadence, save an unassociated note, reject nonexistent week 53 without
  losing a review draft, and retain associations after restart. They render and
  save the review form at 640×480, then reopen it at 1440×1000.
- `tests/test_period_selection.py`: 11 cases covering all four canonical period
  scales, ISO-year boundaries, leap days, invalid input, invalid goal home/cadence
  combinations before worker dispatch, and existing note/review associations.
- `tests/test_layout_media.py`: four cases covering a deliberately blocked cold
  decoder while GUI timers/navigation keep running, stale-page rejection,
  off-main-thread decoding, warm reuse, image-only refresh invalidation, symlink
  rejection on cached paths, revision changes during decoding, unchanged original
  image bytes, 1024 px previews, batch budgets, queue coalescing and a write
  accepted behind an active media read.
- Existing import/duplicate/missing-reference, period/layout uniqueness,
  cross-period queries, round-trip, conflict, restart and Phase 7B tests all ran
  in the full suite. The older GUI script now explicitly waits for asynchronous
  media completion before asserting that a newly opened layout has image data.

A negative control temporarily removed the new forwarding line, ran the nested
journey and confirmed that it failed because no editor opened (`KeyError: open`).
The line was restored before the passing full run.

## GUI results

| Journey | Offscreen/software | Native X11 (`xcb`)/software |
| --- | --- | --- |
| `tools/verify_phase7b1_ux.py --depth 1` | PASS in full pytest | Not separately run |
| `tools/verify_phase7b1_ux.py --depth 3` | PASS, including fresh-process restart | PASS, including fresh-process restart |
| `tools/verify_phase7b_final.py` | PASS in full pytest | PASS |

These runs reported no QML warnings. The existing 7B journey covers note
creation/editing, keyboard save, goal monthly tracking, follow-up editing,
home-only isolation, page regions, linked notes, reviews, local image chooser
selection/import/display, layout images, process restart and index rebuild.

Screenshots of the review form were inspected at desktop and minimum window
sizes. Disposable screenshots are under
`/tmp/habit-workspace-phase7b1/{offscreen,xcb}/review-{desktop,640}.png`.
This is Linux render/input evidence, not Windows/macOS/Wayland validation or a
human accessibility audit. Initial sandbox access to display `:0` was denied;
the native checks passed when run with the required display-access permission.

## Image measurements

Environment: Linux 7.1.13 x86_64 / glibc 2.42, Python 3.14.7, PySide6 6.12.0,
16 logical CPUs, Qt offscreen/software, 1440×1000 window. The benchmark creates a
disposable vault and one page with six distinct 2000×2000 images, then clears the
application image cache. Deterministic random seed: 7.

| Assets | Actual file sizes (bytes) | Pixels each |
| --- | --- | --- |
| PNG ×2 | 1,768,240; 1,781,214 | 4,000,000 |
| JPEG ×2 | 1,866,170; 1,866,065 | 4,000,000 |
| WebP ×2 | 2,013,192; 2,013,034 | 4,000,000 |

All inputs are below 2 MiB and exactly at the pixel limit. GIF was not included
in the performance fixture. These are local samples, not a cross-platform
performance guarantee or statistical latency distribution.

The final harness was replayed against source exported from baseline commit
`104754c` into `/tmp/hw-7b1-baseline`, without changing the working branch. The
corrected run waits for the six asynchronous Images to report Ready and a frame;
baseline Images are synchronous. Each run includes one cold opening, three
return navigations, one unrelated publish, one unchanged worker refresh and one
external replacement followed by the same publication operation. Heartbeat
values are maximum excess gaps over a 5 ms GUI timer during each operation.
Rendered timings include frame waits, not an arbitrary settle sleep.

| Operation | Slot ms before → after | Rendered ms before → after | Heartbeat excess ms before → after | Application decodes before / after |
| --- | --- | --- | --- | --- |
| First page opening | 1585.44 → 21.62 | 1605.42 → 738.25 | 1587.52 → 47.09 | 6 GUI / 6 worker |
| Return navigation 1 | 208.01 → 50.64 | 222.63 → 69.71 | 207.16 → 49.42 | 0 / 0 |
| Return navigation 2 | 209.45 → 50.89 | 223.18 → 67.39 | 208.59 → 49.91 | 0 / 0 |
| Return navigation 3 | 210.03 → 53.99 | 226.66 → 74.19 | 211.45 → 54.01 | 0 / 0 |
| Unrelated publish | 1.68 → 1.29 | 29.16 → 34.14 | 2.56 → 11.56 | 0 / 0 |
| Unchanged refresh | 0.16 → 0.08 | 33.94 → 42.20 | 4.75 → 13.76 | 0 / 0 |
| One externally replaced image | 140.87 → 27.64 | 159.66 → 97.48 | 136.40 → 26.31 | 1 GUI / 1 worker |

Cold application decode/encode time totaled 1376.66 ms before and 538.84 ms after;
the latter produces bounded previews. No corrected application decodes occurred
on the main thread. Warm visits reused all six cache entries; external replacement
invalidated exactly one. The replacement is a valid uniform 2000×2000 PNG; this
row measures invalidation, not worst-case random-image re-encoding. Unrelated
refresh timing varies by a few frames and was not optimized further.

Reproduce the corrected benchmark:

```bash
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python tools/benchmark_phase7b1_images.py
```

The captured final JSON outputs are `/tmp/phase7b1-images-before-final.json` and
`/tmp/phase7b1-images-final.json`. Replaying the baseline uses `git archive` of
that commit's `src` and `tools` directories, copies only this benchmark harness
into the exported tools directory and sets `PYTHONPATH` to the exported `src`.

## Remaining limitations

- Large-page presentation still costs around 50–54 ms on warm navigation here;
  asynchronous loading removes the measured multi-second decode stall, not all
  Qt transfer/rendering work. First complete image presentation is still async.
- One active media batch finishes before a queued write can start. Pending media
  coalesces and writes take priority afterward; an active decode is not forcibly
  interrupted. Stale results can warm the cache but cannot replace current UI.
- Preview resolution is capped at 1024 px; this is not a full-resolution image
  viewer. Visible payload/cache budgets are not a cap on total Qt process memory.
- Unrelated publication still performs safe path/stat checks. Very slow local
  filesystems were not benchmarked. No personal vault or network filesystem was
  used. Native image workflows were tested, but timing figures above are offscreen.
- Existing region-marker creation behavior and GIF first-frame behavior are
  unchanged. No calendar/events, analytics, backup/export, cloud or goal-progress
  semantics were added.

## Manual verification

1. Use a new disposable vault. In Layout Studio, add sections inside sections
   and link an existing standalone note. For an existing page with Markdown
   regions, include both an explicit region binding and a block-ID region.
   Publish, navigate away/back and activate each nested edit button. Verify its
   full text and target label, save, restart and repeat after reindexing.
2. On an annual page, create a goal. Verify the readable home period and
   **Somente neste período** default. Select monthly tracking, change home to a
   day and save: the policy and draft must remain and validation must explain
   the incompatibility. Restore the annual home or explicitly choose a valid
   policy, then save. Verify scope dates were not changed by home selection.
3. Create a review on the week containing 31 December 2026. Verify the displayed
   28/12/2026–03/01/2027 range. Change its year to 2027: saving must require a
   valid week selection. A note may explicitly have no associated period.
   Reopen both from a different page and check that their associations persist.
4. Run the benchmark above; navigate while images load, then return, refresh,
   externally replace one fixture image and refresh again. Broken or unsafe
   images must remain visible errors. Only use generated/disposable images.
5. Run `tools/verify_phase7b1_ux.py --depth 3` with the offscreen environment
   above, then with `QT_QPA_PLATFORM=xcb QT_QUICK_BACKEND=software` on an available
   native X11 session. Resize to 640×480; scroll content and keep save/cancel
   available. Check Tab navigation, safe-preview focus and reduced motion.

## Changed files

Presentation Python: `capture_actions.py`, `content.py`, `controllers.py`,
`layout_assets.py`, new `layout_media.py`, `layout_studio.py`, new
`period_selection.py`, `planning.py`, `vault_tasks.py` under
`src/habit_workspace/presentation/`.

QML: `ContentDialog.qml`, `LayoutComposition.qml`, `LocalImages.qml`, new
`PeriodSelector.qml`, `PlanningDialog.qml` under that presentation directory.

Tests: new `tests/test_layout_media.py`, `tests/test_period_selection.py`,
`tests/test_phase7b1_qml.py`.

Tools: new `tools/benchmark_phase7b1_images.py`, new
`tools/verify_phase7b1_ux.py`, async-wait adjustment in
`tools/verify_phase7b_final.py`.

Documentation: `ARCHITECTURE.md`, `DESIGN_SYSTEM.md`, and this report.

## Suggested delivery text

Commit: `fix: refine nested note editing, period selection and image loading (7B.1)`

PR title: `Phase 7B.1: fix nested note editing and refine period/image UX`

PR description:

> Notes inside nested sections now open the existing canonical editor. Goal,
> note and review forms use Portuguese calendar choices, preserve exact period
> associations and reject incompatible goal tracking without losing drafts.
>
> Measured cold image decoding now runs on the existing worker with bounded
> previews, revision validation and stale-result protection. Canonical schemas,
> original assets and persistence paths are unchanged.
>
> Validation: 359 pytest cases passed; Ruff, format, diff and QML smoke checks
> passed. Offscreen and native X11 journeys passed, including restart/index
> rebuild. The six-image benchmark reduced cold navigation return from 1585 ms
> to 22 ms and warm returns from 208–210 ms to 51–54 ms. See this verification
> report for complete timings, tested platforms and remaining limitations.
