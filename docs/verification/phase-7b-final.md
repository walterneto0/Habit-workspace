# Phase 7B final verification

Phase 7B content, reflection and scope/cadence workflows are implemented and
ready for owner review. Work continued on feat/phase-7b-content-reflection.
The prior checkpoint, Execution 1 implementation and local documentation edits
were preserved. No commit, push, PR, merge or network dependency was introduced.

## Contracts and compatibility

- Goals retain schema 4, one canonical UUID and independent current manual status
  and progress. home_period_ref, scope and tracking are distinct. home_only is the
  default; periodic month/week/day must be smaller than the home scale.
  hw.followups stores uniquely keyed exact-period comments with UUID and goal_id.
  Changes to policy preserve historical comments; boundary weeks show the eligible
  scope intersection. Legacy exact-scope inference and global discovery remain.
- Standalone notes retain full Markdown bodies and optional exact hw.period.
  Page regions resolve content_id then block UUID. Missing, duplicate, malformed
  or nested markers are never repaired/overwritten automatically. Only the
  selected region interior changes; layout deletion does not delete content.
- New schema-4 review requires UUID, nonempty title and exactly one validated
  hw.period (year/month/ISO week/day). Commentary is the Markdown body. Optional
  hw.assessment.rating is nullable integer 1–5: manual subjective assessment of
  this exact period, never a daily metric, inferred score or goal percentage.
  Multiple reviews per period are permitted, each with its own identity.
  Reviews default to Reviews/<uuid>.md and use the existing revision-aware writer.
- PNG/JPEG/WebP/GIF imports require extension/actual-format agreement, bounded
  decode success, at most 2 MiB and 4 million pixels. Nonregular files, symlink
  sources/ancestors and unsafe destination paths are rejected. UUID filenames
  under Assets/ are published create-only. Notes/reviews insert escaped alt text
  in ordinary Markdown; layouts retain ImageConfig path/alt/fit.
- Preview never fetches remote resources or executes HTML. Only validated pixels
  become PNG data URLs. Note/review image references must point into Assets/;
  older layout image paths remain supported if safe and vault-relative.
  Missing/corrupt images produce feedback without deleting documents.
- The existing serialized VaultTasks queue performs review writes and media
  imports/previews. Drafts survive validation, I/O and external-edit errors.
  Serializer metadata, BOM, newline policy and stable UUIDs remain intact.
  Cache is disposable: up to 64 MiB encoded pixels keyed by file revision, with
  containment checked before hits. Assets and Markdown remain canonical.
  A failed/cancelled reference save may leave an unreferenced asset; no automatic
  cleanup or cross-file transaction is claimed. No schema migration is required.

See FILE_FORMAT.md for the authoritative persisted profile.

## Executed verification

All tests use disposable vaults and generated local images.

| Command | Result |
| --- | --- |
| .venv/bin/python -m ruff check . | PASS |
| .venv/bin/python -m ruff format --check . | PASS, final check: 129 files already formatted |
| git diff --check | PASS |
| QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python -m pytest tests/test_phase7b_final.py tests/test_layout_assets.py tests/test_content_execution1.py -q | 29 passed in 0.92s |
| QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python -m pytest -q | **Final run: 342 passed in 97.17s (0:01:37)**; earlier full run: 342 passed in 96.66s |
| QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python -m habit_workspace --smoke-test | PASS, one visible root window |
| QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python tools/verify_phase7b_final.py | PASS, zero QML warnings |
| QT_QPA_PLATFORM=xcb QT_QUICK_BACKEND=software .venv/bin/python tools/verify_phase7b_final.py | PASS, zero QML warnings; authorized native Linux X11 run |

New tests cover review period scales and cross-year ISO identity, manual rating
validation, multiple independent reviews, imports/duplicate conflicts, unchanged
invalid source bytes, BOM/CRLF and unknown keys, stale revisions, draft retention,
contextual filtering/body search, image format mismatch/corruption, byte/pixel
limits, symlinks, traversal/remote references, offline reindex/reopen, and cache
reuse/invalidation. The first focused compatibility run exposed a ValueError
versus DocumentError mismatch in image validation; corrected before acceptance.

The final GUI script covers annual home-only isolation on month/week/day views,
enabling monthly follow-up, note create/edit and keyboard save, page-region
editing with unchanged surrounding content, linked-note opening, ISO-week review,
local image insertion and layout publication, new controller/engine recovery,
index deletion/rebuild, and a fresh Python GUI subprocess reopening the same
vault. The subprocess confirms saved goal/follow-up/review identities, local
image decoding to Image.Ready in QML, and the persisted image layout.

The picker is opened through the pointer; the test deterministically supplies a
selected local URL and emits its acceptance callback. It does not automate the
platform file manager's full browsing interaction. Saving/editing uses real
pointer/keyboard input. Native X11 evidence does not imply Windows/macOS approval.

## Changed paths

Execution 2 extends:
- src/habit_workspace/domain/documents.py
- src/habit_workspace/application/content.py
- src/habit_workspace/presentation/content.py, controllers.py, capture_actions.py,
  vault_tasks.py, layout_assets.py, layout_studio.py
- src/habit_workspace/presentation/qml/ContentDialog.qml, LocalImages.qml (new),
  Main.qml, DocumentDetails.qml, DocumentList.qml, LayoutComposition.qml,
  StudioProperties.qml
- tests/test_phase7b_final.py (new)
- tools/verify_phase7b_final.py (new)
- README.md, ROADMAP.md, PRODUCT.md, FILE_FORMAT.md, ARCHITECTURE.md,
  LAYOUT_ENGINE.md, DESIGN_SYSTEM.md and this report.

Earlier Phase 7B goal changes in application/planning.py, domain/planning.py,
presentation/planning.py, PlanningDialog.qml, PlanningRow.qml, tests/test_planning.py,
tests/test_content_execution1.py and tools/verify_phase7b_execution1.py remain.
AGENTS.md, the direction document, Phase 7A evidence and earlier reports retain
the user's preexisting changes.

## Limitations

- Markdown preview is inert readable text with validated image thumbnails, not
  a complete formatted Markdown renderer. Up to 64 inline image references are
  displayed per preview; GIF uses the first decoded frame.
- Existing page regions require markers; no automatic marker creation/repair.
- Conflicts preserve drafts; resolution uses explicit copy/cancel/reopen, with no
  merge UI. Assets can remain unreferenced after cancellation or failed saves.
- No manual accessibility audit or Windows/macOS validation was performed.
- Events/agenda (7C), charts/analytics (8) and dependency-aware packaging/backup
  (9) remain outside this delivery. No inferred scores or progress.

## Manual acceptance

Launch with .venv/bin/python -m habit_workspace and create a disposable vault.

1. In the year view create an annual goal with Somente neste período. Check
   month/week/day views: it must not appear automatically. Return to year,
   edit Acompanhar to Mensal, then open an eligible month and save a follow-up.
   Confirm the global goal's manually entered progress remains independent.
2. Use Nova nota, write Markdown longer than 6,000 characters, save/reopen/edit.
   Optionally associate a period and use Abrir período associado. Search for a
   word from its body in the notes browser.
3. On a page with valid hw:content markers and a matching note block, use Editar
   texto da página. Check the canonical file's other regions/surrounding text.
   A linked note uses Editar nota independente. Invalid markers must block saving.
4. Use Nova avaliação do período. Select week/2026-W53, write commentary and a
   manual rating 1–5. Save/edit/search. It must appear in that exact week, not
   automatically in adjacent months or days. Other scales accept exact refs too.
5. In the note/review editor fill alternative text and Inserir imagem local.
   Select a PNG/JPEG/WebP/GIF, enable Prévia segura, then save. In Studio add an
   image, use Selecionar e importar imagem local, set alt text and publish layout.
6. Close/relaunch. Reopen each item and check images offline. Close the app,
   delete only the disposable vault's .habit-workspace/index.sqlite, reopen and
   verify all content. A missing/corrupt asset should show feedback without
   changing Markdown. An external text edit must cause a stale editor save to
   fail while keeping the draft.

## Suggested commit and PR

Commit: feat: complete phase 7b content, reflection and goal tracking

PR title: Complete Phase 7B content, reviews and explicit goal tracking

PR description:
Separate goal home ownership, validity and explicit tracking cadence, with linked
canonical period comments and independent manual overall progress. Add full-length
standalone Markdown notes, structurally validated page-region edits, exact-period
reviews with optional manual assessment, and validated local image ingestion and
offline rendering. Reuse atomic revision-aware vault workers and preserve legacy
records, drafts, unknown metadata and rebuildable indexing. Validation results and
platform limitations are recorded above. No Phase 7C/8/9 functionality is included.
