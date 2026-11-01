# Repository instructions for Codex — Habit Workspace v4

## Mandatory reading
Before any feature: read `PRODUCT.md`, `FILE_FORMAT.md`, `LAYOUT_ENGINE.md`, `ARCHITECTURE.md`, `PRIVACY.md`, `DESIGN_SYSTEM.md`, `ROADMAP.md`. For Phase 7B, also read `docs/planning/phase-7b-direction.md`. v4 supersedes previous instructions saying SQLite is the primary database.

## Highest-priority product invariants
- Python + PySide6 / Qt Quick (QML), desktop first, clean Linear-inspired aesthetic; Qt is presentation only, domain is pure typed Python.
- **File-first**: the user's folder of Markdown documents and structured frontmatter is the durable, canonical datastore. SQLite is strictly a disposable cache/index and must be reconstructible.
- No login, Google account, cloud services, telemetry, network, or remote dependency for core operation. Default offline.
- Files must remain readable in ordinary text editors; preserve human-written Markdown and unknown metadata where safe.
- Each item/page has a stable UUID internal ID; paths and folder hierarchy are not identities. Physical file arrangement does not define the Year -> Month -> Week -> Day visual hierarchy.
- Creating an item on a period page sets its *default*, user-editable temporal scope. Scope, recurrence and origin page are different fields.
- Habit definition has one canonical document; check-in status on a given day has one canonical record inside the day's document. Never store those as a second conflicting truth.
- No log is NOT a missed habit. Missing referenced habit after importing a single page must be visible, not recreated or silently treated as a failure.
- Graph blocks persist configuration (time period, manually selected source IDs or dynamic tags), never computed results as their only data.
- QML must render a **visual component tree**, not a plain Markdown page. Build Layout Studio with drag/drop of lists, tables, checklist, graph, note, image and typed input.
- Each concrete period resolves **one** active layout at each time; historical changes are versioned with `effective_at`, not multiple simultaneous layouts.
- LayoutTemplate versioned JSON is separate from Markdown content and observed values. Stable field/source UUIDs survive rearrangement and layout changes.
- Adding a field to a weekly layout makes new observations eligible for dynamic monthly queries from activation onward; never backfill missed statuses before activation. Manual chart selections must not be silently changed.
- Layout input must distinguish binding existing item vs creating a new typed metric. Removing a block never deletes canonical recorded values.
- Do not execute QML or code from JSON layout files.
- A page must be importable by itself; its contents stay intelligible with snapshots, and missing dependencies are explicitly disclosed. Export with dependencies when full interactive reconstruction is requested.
- Deleting a visual block must not delete referenced domain data.

## Safety, durability and integrity
- Treat imported Markdown/YAML/JSON/ZIP as untrusted data. Strict schemas, safe parsers, path containment, size limits. Never run code from documents or remote references.
- Atomic writes, conflict detection and explicit resolution; never silently overwrite external edits or duplicate UUIDs.
- Never discard original file on parser error, schema mismatch or unknown block type. Implement versioned schema migrations with round-trip tests.
- Test deleting `index.sqlite` and rebuilding from files; this is a critical acceptance test.
- Backup/export controls, clear privacy explanation: no accounts != encryption != perfect anonymity.

## Workflow
1. Before implementing, propose changes, risks, acceptance tests and file formats.
2. Implement ONLY one roadmap phase per request; stop and summarize exactly what was verified.
3. Write tests for imports, duplicate conflicts, missing references, layout temporal uniqueness, cross-period aggregates and round-trip before feature code relying on these contracts.
4. Run lint, unit/integration tests, and render-check QML when feasible; never falsely claim visual/platform validation.
5. Never push, run global destructive operations, execute downloaded code, install globally, transmit user files, or create Git commits without explicit approval.
6. Preserve future mobile portability in domain/file contracts, while treating mobile UX as future work.

## UX and presentation
Follow `DESIGN_SYSTEM.md`, including keyboard operation, responsive desktop resizing, subtle transitions and reduced motion. Expose vault create/open/import/export/reindex actions. Show missing-link/conflict states without hiding content.
