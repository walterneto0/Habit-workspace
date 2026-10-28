# Phase 1 — File-first vault and document persistence

Implemented and verified on Linux, Python 3.14.7, PySide6 6.12.0. Phase 2 has not
started. No Git commits were created and no personal vault data was used.

## Implementation and ownership

Markdown documents and `.habit-workspace/vault.json` are canonical. SQLite holds
only derived paths, UUIDs, titles, kinds, revisions, references and parse issues.
It contains no uniquely owned document content. Opening a vault reconstructs the
index; cache failure is disclosed independently of successful canonical writes.

The architecture follows the existing separation:

```text
src/habit_workspace/
  domain/
    __init__.py
    documents.py        # typed identity, kinds, storage validation, references
  application/
    __init__.py
    vault.py            # VaultSession: create/open/load/save/scan orchestration
    imports.py          # ImportService and structured per-file import results
    cli.py              # temporary diagnostic interface, JSON output
  vault/
    __init__.py
    manager.py          # VaultManager: identity, structure, bounded JSON manifest
    format.py           # bounded inert YAML and exact Markdown round trips
    atomic_io.py        # revisions, create-only publication, atomic save, backups
    repositories.py     # DocumentRepository: canonical file I/O
    scanner.py          # recursive discovery, duplicate IDs, missing references
    watcher.py          # optional Qt adapter with debounce and periodic rescan
  indexing/
    __init__.py
    cache.py            # IndexCache: transactional, replaceable SQLite generation
  __main__.py           # updated: diagnostic commands and optional --vault
  bootstrap.py          # updated: connect session/watcher to the existing shell
  presentation/qml/
    Main.qml            # updated: plain-text vault status; existing design retained
tests/
  test_vault.py
  test_document_format.py
  test_persistence_safety.py
  test_watcher.py
  test_cli.py
  test_package.py        # updated: application imports remain independent of Qt
tools/
  verify_phase1.py       # repeatable two-vault portability/rebuild demonstration
```

`FILE_FORMAT.md`, `README.md`, `docs/dependencies.md`, `pyproject.toml`, and
`requirements.lock` were updated. This verification report is new. Existing
Phase 0 verification remains a historical record.

Created vault structure (physical organization is optional after creation):

```text
chosen-folder/
  .habit-workspace/
    vault.json
    index.sqlite           # disposable; regenerated on open/scan/reindex
    backups/               # exact pre-save revisions, named by SHA-256
    write.lock/            # exists only while an application writer holds it
  Pages/{Days,Weeks,Months,Years}/
  Items/{Habits,Metrics,Tasks,Goals,Events}/
  Notes/
  Imports/
  Layouts/
  Assets/
  Templates/
```

Only supported Markdown kinds are indexed. Creating empty folders for future
types does not implement those types. There are no hardcoded personal paths;
the CLI requires the user-selected directory. Creating a vault requires a new or
empty directory, preventing accidental adoption of unrelated personal files.
Opening validates the manifest without rewriting unknown configuration fields.

## Verified commands and actual results

| Check | Actual result |
| --- | --- |
| Original Phase 0 suite, before implementation | 3 passed |
| New contract tests before implementation | Failed collection as expected: new modules did not yet exist |
| `.venv/bin/python -m pytest -q` | **53 passed**, 2.07 seconds |
| `.venv/bin/python -m ruff check .` | Passed |
| `.venv/bin/python -m ruff format --check .` | Passed |
| `.venv/bin/pyside6-qmllint src/habit_workspace/presentation/qml/Main.qml` | Passed, no diagnostics |
| `.venv/bin/python -m pip check` | No broken requirements |
| `unshare --user --map-root-user --net .venv/bin/python -m pytest -q` | **53 passed**, 2.19 seconds |
| Network-isolated offscreen QML `--smoke-test` | Passed, one visible root window, clean exit |
| `.venv/bin/python tools/verify_phase1.py` | Passed; also passed in the network namespace |
| `.venv/bin/python -m pip wheel --no-deps --no-build-isolation --wheel-dir dist .` | Passed |
| Wheel contents, temporary installation, CLI create/new-note, QML startup | Passed; asserted package import comes from temporary installed wheel |
| Software-rendered captures, 1100×740 and 640×480 | Captured and visually inspected; status fits, no clipping observed |
| Native xcb `--smoke-test` | Failed: cannot connect to display `:0`; xcb initialization diagnostic also mentions `xcb-cursor0` |

The wheel installation reused dependencies from `.venv`; it is not a completely
fresh-machine installation. The test captures are temporary artifacts at
`/tmp/habit-workspace-phase1-1100.png` and `/tmp/habit-workspace-phase1-640.png`,
using explicitly generated diagnostic status text. They validate the existing
shell only, not future visual document rendering. Native desktop, GPU,
window-manager interaction, Windows and macOS remain unverified. No system
packages or display configuration were changed.

The initial sandbox YAML dependency download failed on DNS; the approved retry
installed only into `.venv`. Installed metadata reports MIT for ruamel.yaml and
its transitive C extension. No runtime installation or networking is performed.

## Acceptance evidence

All **Phase 1** acceptance scenarios listed in `ROADMAP.md` are satisfied through
the permitted diagnostic CLI and existing QML shell:

1. **Copy/import/view a document from another computer:** tests and
   `tools/verify_phase1.py` create two independent temporary vaults, import without
   changing bytes or UUID, inspect metadata/content, and reopen the destination.
   CLI `show` displays preserved content and missing-reference diagnostics.
2. **Delete and recreate the index:** tests delete `index.sqlite`, reopen, and
   compare canonical file bytes, UUID sets and reference results. The demo also
   compares SHA-256 before/after rebuild. Corrupt caches are rebuilt as well.
3. **Edit externally and refresh:** real Qt event tests cover replacements,
   renames, newly created nested folders, malformed edits and restoration.
   Periodic rescan recovers after watcher paths are deliberately removed.
4. **Corrupt files survive:** malformed YAML, invalid UTF-8, unsupported versions,
   unsafe tags, duplicate keys, merge keys, excessive size/depth and malformed
   typed fields are rejected without changing the original. Scanner issues expose
   the path and diagnostic rather than silently hiding the problem.
5. **Duplicate UUIDs never overwrite:** byte-identical imports are skipped;
   divergent files conflict. Existing duplicate UUIDs, even identical ones, remain
   ambiguous and cannot be saved through the session. Both paths are reported.

Additional mandatory coverage includes create/reopen; note/page/habit round
trips; unknown metadata, comments, BOM and CRLF preservation; UUID references
surviving renames; missing habits resolving after a later/batched import;
same-size/same-mtime external edits; stale saves; interrupted replacement;
create-time destination collision; cache failure after successful canonical
write; local writer locks; symlink/path containment; standalone note conversion;
offline operation; and whole-vault relocation without the original SQLite file.

No layout resolver, cross-period aggregates, occurrence engine, habit capture,
charts, Layout Studio, full navigation, or `.hwpack` implementation was added.
Record/history validation protects stored data but does not implement these later
features. Their acceptance tests belong to the phases that implement them.

## Usage

Run the existing shell with `.venv/bin/python -m habit_workspace`, or attach a
vault with `.venv/bin/python -m habit_workspace --vault /chosen/folder`.
Use `.venv/bin/python -m habit_workspace vault --help` for diagnostic commands.
The [README](../../README.md) includes create/open/import/show/reindex examples.

The reusable Python entry points are `VaultSession.create/open`,
`create_document`, `load`, `save`, `scan`, and
`ImportService(session).import_files`. `load` returns a `LoadedDocument` carrying
the revision that `save` must check. Callers must retain this revision, handle
`ConflictError` explicitly, and surface `session.index_error` after mutations.
The application layer imports no Qt modules; the watcher is optional.

## Known limitations and recovery

- Saves use content hashes, size, modification time and file identity, checked
  before staging and again immediately before atomic replacement. App writers
  share a vault lock. **Portable filesystems have no path compare-and-swap:** an
  uncooperative external writer can still race between the final check and
  `os.replace`. This very small window is not claimed to be eliminated. Prior
  revisions are retained, but a change made inside that final race may not be in
  the recovery copy. Hostile concurrent replacement of directory components is
  also outside the guarantees of these path-based checks.
- Atomic create-only publication requires hard-link support. Unsupported
  filesystems fail safely instead of falling back to an overwrite-prone write.
  Directory fsync is used on POSIX; cross-platform durability needs native tests.
  Disk failure after publication may leave a complete file despite an error;
  rescan before retrying. Partially initialized vault folders are preserved.
- A crashed application can leave `.habit-workspace/write.lock/`. Close all
  writers, inspect the vault, and remove only that empty lock directory when
  certain no writer is active. Locks are never stolen automatically. Recovery
  copies are retained without automatic cleanup and contain personal data.
- Full rescans and cache generations favor correctness for this initial phase;
  they run synchronously in the Qt adapter and are not benchmarked for large
  vaults. The default fallback is every two seconds. Future incremental/background
  scanning must preserve the same error and identity contracts.
- The supported schema matrix is explicit in `FILE_FORMAT.md`. Unknown versions
  are left untouched; there is no invented legacy migration. Supported habit v1
  remains v1 on round trip. Layout JSON and metric definitions are unavailable
  dependencies in this phase, even if files are present. Unknown extension
  fields/blocks are preserved, but their references cannot be interpreted.
- Conflict comparison/resolution currently happens through diagnostics and the
  user's editor. There is no automatic replacement, UUID reassignment, full
  export/backup interface, or final renderer. Re-importing unstructured Markdown
  with `--as-note` intentionally creates a new UUID each time.
- Data is local plaintext, not encrypted or anonymous. Pre-save recovery copies
  are not a complete backup strategy; full packaging/backup controls remain in
  their roadmap phase.

Work stops at Phase 1.
