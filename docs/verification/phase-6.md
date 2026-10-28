# Phase 6 — habit check-ins and structured capture

Branch `feat/phase-6-habit-tracking`, based on `main` at `c06a720` (Phase 5
integrated Layout Studio, partial acceptance). Phase 5 code was present; it was
extended, not rebuilt. No Phase 7–9 scope was started. No canonical schema version,
dependency or license changed.

## What is usable in the GUI

On any concrete year/month/week/day page, below the period header:

1. **Modo de acompanhamento** shows the selected capture date (defaults to today
   when inside the period). ◀/▶, **Alt+Shift+←/→**, a `AAAA-MM-DD` jump field and
   **Hoje** move it within the open period.
2. **Hábitos deste período** lists canonical habits whose scope intersects the
   period, with recurrence, scope, tags and the state on the selected date.
   **Novo hábito** / **Editar** open a form: name (required), tags, scope (the
   page's period as the default, or custom start/inclusive end, empty end = open)
   and recurrence (daily or weekdays). Validation errors stay inside the form with
   the typed input retained. The optional **Adicionar checklist vinculada** opens
   the Layout Studio with a checklist already bound to the new habit for review/save.
3. The page's resolved layout is rendered interactively:
   - habit-bound checklists offer **Concluído**, **Dispensado**, **Não cumprido**
     and **Limpar registro**;
   - boolean-field checklists/inputs offer **Sim** / **Não** / **Limpar**;
   - typed inputs (integer, number, duration, rating, text, date, time) offer a text
     field with **Salvar** (or Enter) and **Limpar**; selection fields use a combo.
   - Each entry shows inline saved/rejected feedback; the global notice repeats it.
4. States are distinguished: *Não programado*, *Futuro · sem registro*,
   *Pendente hoje · sem registro*, *Sem registro (não é falha)*, and the explicit
   recorded states. Missing habits/fields show the saved label snapshot and are not
   editable or recreated. Records outside the current schedule are shown as
   preserved history, read-only.
5. The Layout Studio remains the editing mode; its canvas still shows inert
   placeholders. Capture is refused while a Studio draft is open.

## Storage contract (unchanged schema v4)

- A habit-bound control writes only `hw.checkins` in the day's canonical
  `day_page`: `id`, `habit_id`, `date`, `state` (`done`/`skipped`/`missed`),
  `label_snapshot`, `recorded_at`.
- A field-bound control writes only `hw.observations` in the same day page:
  `id`, `field_id`, `field_label_snapshot`, `observed_date`, `recorded_at`,
  `value`, plus `source_period_ref` and `source_block_id` provenance.
- The service checks the target kind: a habit UUID cannot receive observations and
  a metric UUID cannot receive check-ins, so a fact never has two sources.
- Writes are upserts per (habit, date) or (field, date): identical repeats do not
  touch the file; corrections keep the record UUID and unknown keys, update the
  value/state and `recorded_at`; **Limpar** removes the explicit record (absence is
  *unrecorded*, never *missed*). A missing day page is created at
  `Pages/Days/<uuid>.md`, as the Phase 4 metric service already did.
- Every write runs under the vault writer lock against a fresh scan, then uses the
  revision-checked atomic writer with a recovery copy. The GUI sends the value it
  displayed; if the file changed meanwhile (external edit), nothing is written,
  a conflict is shown and the page reloads the current file values.
- Refused: future dates; check-ins on dates the habit is not scheduled (records
  already there stay intact); observations before the field's activation date
  (no historical-entry UI); fields with weekly temporal policy; values failing the
  field's type/bounds/options; ambiguous duplicate day pages or habit UUIDs.
- `HabitService.update` now also accepts `name` and `tags`; schedule edits that
  orphan recorded check-ins still require explicit acknowledgement in the form.
- Layout JSON stays presentation/binding only; SQLite stays a disposable index.

## Files changed

- `src/habit_workspace/application/capture.py` (new): `CaptureService`
  (`set_checkin`, `set_observation`), `CaptureSnapshot` read-only projection,
  `parse_value`.
- `src/habit_workspace/application/habits.py`: `update(name=, tags=)`.
- `src/habit_workspace/presentation/tracking.py` (new): QML view mappings.
- `src/habit_workspace/presentation/controllers.py`: capture date, habit list,
  habit form and capture slots.
- `src/habit_workspace/presentation/layout_studio.py`: optional capture snapshot
  in the shared composition.
- QML: new `CaptureCell.qml`, `TrackingPanel.qml`, `HabitDialog.qml`; tracking
  mode in `LayoutComposition.qml`; integration and shortcuts in `Main.qml`.
- Tests: `tests/test_capture.py`, `tests/test_tracking.py`.
- `tools/verify_phase6.py`; docs (this report, README, ROADMAP, FILE_FORMAT,
  CHANGELOG, shortcuts).

## Commands executed and results

The checkout had no `.venv`; one was created locally per `CONTRIBUTING.md`
(`python3.14 -m venv .venv`, `pip install -r requirements.lock`, editable install).
Nothing was installed globally.

Baseline on `main` before changes: **212 passed**, Ruff clean, 82 files formatted.

Final:

```sh
.venv/bin/python -m ruff check .            # All checks passed!
.venv/bin/python -m ruff format --check .   # 87 files already formatted
.venv/bin/python -m pytest -q               # 234 passed
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python -m habit_workspace --smoke-test   # passed
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python tools/verify_phase{1,2,3,5}.py      # PASS each
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python tools/verify_phase5_interaction.py # PASS
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python tools/verify_phase6.py             # PASS
DISPLAY=:0 .venv/bin/python tools/verify_phase6.py   # PASS, platform "xcb" (native X11 window)
git diff --check                                     # clean
```

### Test coverage mapping

| Requirement | Tests |
| --- | --- |
| Default/overridden scope, weekdays, month and ISO-year week boundaries | `test_capture.py::test_default_and_overridden_scope_with_weekday_recurrence`, `::test_iso_week_across_month_and_year_boundaries`, `test_tracking.py::test_habit_form_validation_override_and_search` |
| Habit creation, UUID identity, tags/search, checklist binding | `test_tracking.py::test_gui_flow_*`, `::test_habit_form_*`, `test_capture.py::test_dynamic_checklist_*` |
| Create/correct/clear check-in; idempotency; no duplicates | `test_capture.py::test_create_correct_clear_and_idempotent_checkin`, `::test_correction_preserves_unknown_record_metadata_and_page_body` |
| Unrecorded/future never become missed | `test_capture.py::test_future_unrecorded_and_pending_never_become_missed`, `test_tracking.py::test_selected_date_states_and_validation` |
| Numeric observation create/edit/validate/persist by `field_id` | `test_capture.py::test_numeric_observation_*`, `::test_pre_activation_*` |
| No check-in/observation duplication | `test_capture.py::test_checkins_and_observations_never_share_a_fact` |
| Block reorder/revision/removal keeps data | `test_tracking.py::test_visual_changes_and_block_removal_keep_values` |
| Scope change after check-ins | `test_capture.py::test_scope_change_after_checkins_preserves_records`, `test_tracking.py::test_edit_scope_after_checkins_requires_acknowledgement` |
| Restart/reopen; delete/rebuild test-vault index | `test_capture.py::test_restart_and_index_rebuild_keep_records`, `test_tracking.py::test_index_rebuild_restores_tracking_state`, `::test_gui_flow_*`, `tools/verify_phase6.py` |
| Missing references, external edits, ambiguity, errors | `test_capture.py::test_external_edit_conflict_and_missing_references`, `::test_missing_habit_shows_saved_label_without_recreating`, `::test_input_block_and_duplicate_ambiguity`, `test_tracking.py::test_stale_external_edit_*`, `::test_capture_blocked_while_studio_draft_is_open` |
| Phases 1–5 regression | full suite plus verification scripts above |

Controller tests freeze the clock so field activation and `recorded_at` agree with
the injected civil "today".

### GUI acceptance script

`tools/verify_phase6.py` drives a real `QQuickWindow` with pointer clicks and key
events on a temporary vault: opens it (Ctrl+O), opens the week, submits the habit
form empty (error shown), fills name/tags/daily recurrence/bind, creates the habit,
adds a new integer field through the Studio palette/metric dialog, publishes the
layout, clicks **Concluído → Dispensado → Concluído → Concluído**, types
`quarenta`+Enter (rejected, file untouched), `40`+Enter (saved), `45`+**Salvar**
(corrected), checks focus visibility at 640 and 1024 px in light theme, moves the
capture date with Alt+Shift+→ (future state), navigates month→week, then deletes
`index.sqlite` and reopens the vault **in a separate process**, asserting the
check-in `done` and the observation `45` from the files. Captures are written to
`/tmp/habit-workspace-phase6/<platform>/`. QML warnings fail the run; none occurred.

## Manual GUI steps

1. `.venv/bin/python -m habit_workspace`, create a disposable vault, open **Semanas**.
2. **Novo hábito** → name, tags, keep *Período da página* or **Personalizar datas**,
   choose recurrence, tick **Adicionar checklist vinculada…**, **Criar hábito**.
3. In the Studio, optionally add a numeric input (*integer_input*, name it
   "Tempo de estudo"), **Revisar e salvar** → **Salvar**.
4. Back on the page, click **Concluído**; type `40` and press Enter.
5. Change to **Dispensado**/back, edit to `45`, try `abc` to see the error.
6. Open **Meses**/**Dias** to see the same habit; quit and reopen the vault.

## Limitations and unverified behavior

- Capture writes run synchronously on the GUI thread (single small files under the
  writer lock). Large-vault latency is unmeasured.
- No human visual or assistive-technology review. The native run on X11 was an
  automated script, not a person checking layout, contrast or screen-reader output.
  Wayland, Windows and macOS were not tested.
- Weekly-policy fields are displayed but cannot be captured (explicitly disclosed).
- Historical (pre-activation) entries and corrections of out-of-schedule check-ins
  are not offered in the GUI; the records remain intact and visible.
- Date, time, duration and rating use validated text entry rather than specialized
  pickers/sliders. Selection uses a combo box without a "clear" choice in the combo
  (use **Limpar**).
- The Studio can bind a checklist to one habit or boolean field; configuring a
  checklist tag/query selection in the Studio UI is still a Phase 5 gap. Such
  selections are rendered and captured when present in layout JSON.
- Capture uses the layout active *now*; selecting an earlier date in a period
  whose layout changed shows today's blocks (field activation still prevents
  pre-activation entries).
- The CI on this branch and the GitHub PR checks were not observed from here.

## Roadmap acceptance (ROADMAP.md, Phase 6)

| Criterion | Status |
| --- | --- |
| Check-ins linked to a habit UUID; observations linked to Field UUIDs; canonical daily file | Met |
| Tags, search, scope/recurrence | Met (form + existing document search over tags/IDs) |
| Habit-bound checklist produces correct check-in | Met (tests + GUI script) |
| Numeric field in layout produces typed observation | Met (tests + GUI script) |
| Visual change does not change value | Met (reorder/column change/revision test) |
| Observation remains after block removed | Met (removal test; day-page bytes unchanged) |

All Phase 6 roadmap criteria are met by executed automated checks. The phase is
ready for owner review; human visual/accessibility review is still outstanding,
and Phase 5 remains partially accepted as documented in its report.
