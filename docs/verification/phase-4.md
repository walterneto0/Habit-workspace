# Phase 4 — Layout and metric contracts

Implemented on 2026-10-28 by continuing the recovered, uncommitted Phase 4
worktree changes. The implementation is domain/application/storage work only.
Phase 2 QML files and design tokens remain unchanged; no Layout Studio or
drag-and-drop UI was added.

## Delivered

- Pure-Python immutable metric, observation, component, layout revision and
  assignment-history models.
- A finite declarative component registry for checklist, list, table, chart,
  rich-text note binding, local image, typed inputs and sections. One/two-column
  placement is validated; unknown component types are never executed or rewritten.
- Schema-v4 JSON layout templates and default registries, strict JSON parsing,
  duplicate identity detection, unknown metadata preservation and immutable
  revision publication.
- Explicit period assignment > period-scale default > deterministic built-in
  fallback. Assignment histories use timezone-aware effective instants and retain
  earlier revisions.
- Canonical schema-v4 metric definitions in Markdown and dated observations in
  daily-page frontmatter. Removing or changing a component does not remove a
  definition or observation.
- File-derived dynamic source queries with activation dates, fixed manual
  selections, missing-source diagnostics and explicit weekly cross-month
  attribution. Queries return actual records only; they do not synthesize misses.
- Scanner, importer, watcher and disposable SQLite v2 index support for layouts,
  defaults, metric definitions and references. Unsupported or malformed input
  remains unchanged with diagnostics.
- Idempotent publication ordering for operations spanning metric, layout and
  period-page files. A failed operation may leave an unassigned definition or
  revision; it does not delete canonical data or publish a dangling assignment.

Canonical formats and current runtime limits are described in
[FILE_FORMAT.md](../../FILE_FORMAT.md). The component/domain boundary and
remaining presentation work are described in [LAYOUT_ENGINE.md](../../LAYOUT_ENGINE.md).

## Verification

All commands below are run from the repository root using the existing `.venv`.

| Check | Result |
| --- | --- |
| `.venv/bin/python -m pytest -q` | 187 passed (final run) |
| `.venv/bin/python -m ruff check .` | Passed |
| `.venv/bin/python -m ruff format --check .` | Passed |
| `.venv/bin/python tools/verify_phase1.py` | Passed |
| `.venv/bin/python tools/verify_phase2.py` | Passed with offscreen/software rendering |
| `.venv/bin/python tools/verify_phase3.py` | Passed |
| `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python -m habit_workspace --smoke-test` | Passed; one visible root window |
| `git diff --check` | Passed |

Phase 4 contract tests include the weekly `2026-W44` activation scenario:
revision 1 is active before `2026-10-29T10:00:00-03:00`; revision 2 adds the
numeric `Reading duration` field at that instant; an observation dated October 29
is discovered by the October tag query; October 26–28 produce no synthetic
failures; a pre-existing observation and fixed manual selection remain unchanged;
the monthly page retains its assigned layout; removing the input block preserves
the field and its observation; and deleting
`index.sqlite` followed by reopening the vault rebuilds the same layout resolution
and metric query from canonical files.

The core test is
[`test_weekly_field_monthly_discovery_and_removal_preserve_data`](../../tests/test_layouts.py);
the surrounding layout, safety and persistence contracts are in
[`test_layouts.py`](../../tests/test_layouts.py),
[`test_layout_safety.py`](../../tests/test_layout_safety.py), and
[`test_persistence_safety.py`](../../tests/test_persistence_safety.py).

## Acceptance status

| Phase 4 criterion | Status |
| --- | --- |
| Stable layout/component/source UUIDs and validated schema-v4 serialization | Satisfied |
| All documented initial component kinds represented without executing vault code | Satisfied |
| One effective explicit/default/built-in layout per period and instant | Satisfied |
| Immutable revisions and historical activation | Satisfied |
| Typed observations stored canonically outside layouts and SQLite | Satisfied |
| Dynamic eligible-source discovery; fixed manual source IDs | Satisfied |
| No inferred missed values before activation | Satisfied |
| Missing references and duplicate identities surfaced without overwriting files | Satisfied |
| Index deletion/rebuild preserves assignments, layouts and query results | Satisfied |
| Approved Phase 2 visual interface preserved | Satisfied; no QML files changed |

## Limitations and risks

- Layout rendering, editor UI, drag/drop, preview, undo/redo and keyboard
  rearrangement are Phase 5 work. This phase does not visually validate a new
  layout component tree.
- Metric queries discover and filter observations; chart rendering and general
  rollup/aggregation behavior remain later roadmap work.
- `.hwpack` dependency export, backups and recovery UX remain Phase 9 work.
- A multi-file publication cannot be atomic as a set. Ordering, explicit errors
  and idempotent retries preserve recoverability, but an interrupted operation
  can leave unused canonical definitions or revisions for the user to inspect.
- Existing synchronous scan/index operations retain their Phase 1/2 limits for
  large vaults. No large-vault responsiveness or native-platform rendering claim
  is made here.
- Phase 2's software/offscreen check passed; native desktop rendering was not
  validated in this environment.

Phase 4 acceptance is complete. Phase 5 has not been started.
