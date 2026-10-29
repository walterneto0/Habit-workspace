# Refine Layout Studio creation, organization, and save workflows

Base: `main`
Head: `feat/phase-5-1-layout-studio-ux`

The Studio previously split field creation across a flat palette and a technical
configuration dialog. Users can now find blocks in a categorized, searchable
library, choose a compatible existing source or create a field in one form, and
reveal specialized settings only when needed. Checklists reuse existing manual,
tag and contextual selection contracts.

Cards have a compact drag handle and explicit edit action, with keyboard/button
alternatives for organization. Responsive panels, themed dialogs, inline validation
and readable period/change summaries clarify the path from an empty/current/template
layout to saving and tracking. Starting points modify only the current draft and
reuse the existing resolver and revision publication path. Historical records,
source UUIDs, other periods and template defaults are preserved.

Validation: 250 pytest tests passed; Ruff lint/format and diff checks passed.
Phase 5/6 Qt regressions and a new end-to-end journey passed. The new journey ran
both offscreen and in native Linux/X11 at 640–1920 px, in light/dark themes; rendered
screenshots were inspected. It covers multi-habit selection, pointer/button reorder,
field validation/reuse, preview, save, direct tracking and a separate-process reopen
with deleted SQLite cache and unchanged canonical Markdown/JSON bytes. No QML
warnings in passing runs.

No schema migrations or dependencies. Phase 7 authoring, table-row capture and
Phase 8 chart calculations remain unavailable and disclosed. Weekly fields remain
read-only in capture. Human accessibility review and other platforms are unverified.

Full evidence: [Phase 5.1 verification](docs/verification/phase-5-ux-refinement.md).
