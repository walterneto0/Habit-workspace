# Habit Workspace v4 — Prompts para o Codex CLI

**Execute uma fase por vez.** Cada prompt pressupõe leitura dos arquivos e testes de aceitação. Todos devem respeitar `AGENTS.md` e `LAYOUT_ENGINE.md`.

## P0 — Planejamento, sem implementação
```text
Act as a senior Python desktop architect, UX designer, and data-modeling specialist. Read AGENTS.md, PRODUCT.md, FILE_FORMAT.md, LAYOUT_ENGINE.md, ARCHITECTURE.md, PRIVACY.md, DESIGN_SYSTEM.md, and ROADMAP.md completely. Our core is Python + PySide6/QML, file-first vault, modern Linear-inspired block UI. The Markdown files are storage, NOT a raw Markdown editor UI. Layout Studio uses drag-and-drop; only one active layout per specific year/month/week/day period at any instant. Layout definitions are versioned inert JSON; field definitions and recorded observations are canonical documents, separate from layouts. Weekly changes must update dynamic monthly aggregates prospectively without retroactive failures. Inspect the repository, identify contradictions or dangerous assumptions, propose stable contracts and test cases, then prepare an incremental plan. Do NOT implement code yet.
```

## P1 — Fase 0: Base técnica
```text
Implement ROADMAP Phase 0 only. Set up Python, PySide6/QML, pyproject.toml, pytest, Ruff and a runnable desktop window. Offline, no global installs or cloud. Demonstrate startup, lint and tests. Stop.
```

## P2 — Fase 1: Cofre e formato de arquivo
```text
Implement ROADMAP Phase 1 only. Versioned Markdown/YAML and JSON layout parsers, UUID indexing, safe and atomic file IO, standalone import, missing references, sqlite index rebuild. Tests before code. Stop.
```

## P3 — Fase 2: Shell visual
```text
Implement ROADMAP Phase 2 only. Design System, 3-pane QML desktop shell inspired by Linear, virtual year/month/week/day navigation, responsive sizing, local vault controls, keyboard and reduced-motion. Render-check where possible. Stop.
```

## P4 — Fase 3: Períodos e domínio
```text
Implement ROADMAP Phase 3 only. Typed Python PeriodRef, ISO-week edge cases, TemporalScope and Recurrence, stable canonical domain records. Ensure visual location never defines data validity. Stop.
```

## P5 — Fase 4: Motor de layouts e schema de outputs
```text
Implement ROADMAP Phase 4 ONLY, domain and persistence first without visual builder. Define versioned inert JSON LayoutTemplate, LayoutAssignment resolution by concrete PeriodRef and effective_at, type-template fallback, FieldDefinition, Observation, and an idempotent multi-file save/recovery strategy. Ensure exactly one effective layout per period and time. Adding a field has an activation time and UUID. Test week 2026-W44 version switch on Oct 29, old values retained, no pre-activation missing entries, import/missing JSON, and index rebuild. Stop.
```

## P6 — Fase 5: Layout Studio (prioridade visual)
```text
Implement ROADMAP Phase 5 ONLY. Build a beautiful Linear-inspired Layout Studio in PySide6/QML: left component palette, center 1–2-column snap-to-grid canvas, right properties panel, live preview, drag/drop, keyboard reorder, undo/redo, save as new version. Initial component types: checklist, list, table, chart placeholder, note, image and typed field. Use declarative block-renderer mapping; never execute QML stored in vault files. Ordinary pages must render composed UI cards, NOT raw Markdown as a long document. Test saving/reopening and exclusive active assignment. Stop.
```

## P7 — Fase 6: Hábitos e entradas
```text
Implement ROADMAP Phase 6 ONLY. Bind checklist blocks to canonical Habit IDs or create typed field definitions, persist check-ins and observations in day-page documents, use stable IDs, tags and recurrences, keep historical data when blocks are removed. Test no duplication, invalid fields and missing sources. Stop.
```

## P8 — Fase 7: Agenda, rich notes, assets
```text
Implement ROADMAP Phase 7 ONLY. Tasks/goals/events/reviews, Markdown note blocks with stable markers, local image Assets with safe references, calendar derived from canonical records. Test import/transfer, unknown block preservation, and file moves. Stop.
```

## P9 — Fase 8: Gráficos e rollups
```text
Implement ROADMAP Phase 8 ONLY. Modular year/month/week charts with searchable manual source IDs or dynamic tags; typed aggregation for boolean, numeric, duration and rating. Dynamic monthly overview must detect eligible sources added by a weekly layout version effective Oct 29, include recorded values Oct 29–31, NEVER mark Oct 26–28 as missed, and NEVER silently change manually selected sources. Do not change the monthly page layout. Define explicit attribution for week-level measurements crossing months. Validate identical outputs after SQLite deletion/rebuild, with tests. Stop.
```

## P10 — Fase 9: Pacote portátil e release
```text
Implement ROADMAP Phase 9 ONLY. Portable .hwpack with manifest and selected dependencies including JSON layouts, metric definitions, Markdown records and images. Secure import, duplicate ID handling, warnings for missing dependencies, local backups and Linux packaging. Test reconstruction in a clean vault with no original sqlite index or network. Stop.
```

## Auditoria independente
```text
READ-ONLY review of this repository against LAYOUT_ENGINE.md, FILE_FORMAT.md, PRODUCT.md, PRIVACY.md, and AGENTS.md. Report with file and line any raw-Markdown UI, multiple effective layouts for one period, mutated historical layouts, values stored only in visual JSON or SQLite, retroactive failed occurrences, monthly rollups silently changing manual filters, deleted historic observations, unsafe layout execution, broken imports, or untested Qt interactions. Do not modify files.
```
