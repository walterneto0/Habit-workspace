# Habit Workspace — Fase 6: captura de hábitos e campos estruturados

> **Uso:** entregar este arquivo ao Claude Code na raiz do repositório e solicitar a implementação da Fase 6, seguindo o prompt abaixo. Este documento não substitui `AGENTS.md` nem as especificações presentes no repositório.

## Revisão do prompt anterior

O prompt original era adequado quanto a hábitos, privacidade e testes, mas precisava de cinco ajustes:

1. **Cobertura incompleta do roadmap:** a Fase 6 exige tanto *check-ins* de hábitos quanto **observações tipadas de campos configuráveis** (por exemplo, minutos estudados). Não basta marcar checkboxes.
2. **Risco de duplicar dados:** o contrato distingue `checkins` associados a `habit_id` de `observations` associados a `field_id`. Um fato não deve ser gravado nos dois formatos.
3. **Integração com o Layout Studio:** o usuário deve preencher dados em **modo de acompanhamento**, sem precisar abrir o editor de layouts a cada registro.
4. **Critérios de aceite:** é necessário testar o fluxo gráfico completo, incluindo persistência após reiniciar, edição de um valor já salvo e reconstrução do índice SQLite.
5. **Fluxo Git mais seguro:** confirmar primeiro que a Fase 5 está presente na base de trabalho e criar um PR; nunca fazer merge automaticamente nem sobrescrever alterações existentes.

---

## Prompt para Claude Code

You are the lead Python engineer continuing **Habit Workspace**, a file-first, offline desktop application built with **Python, PySide6, and Qt Quick/QML**.

**Implement Phase 6 — Habit Check-ins and Structured Data Capture.** The outcome must be a genuinely usable, visually polished tracking workflow through the graphical interface, not merely backend code.

### 1. Inspect the actual repository first

Read `AGENTS.md`, `ROADMAP.md`, `PRODUCT.md`, `ARCHITECTURE.md`, `FILE_FORMAT.md`, `LAYOUT_ENGINE.md`, `DESIGN_SYSTEM.md`, and `PRIVACY.md`. Review the Phase 3–5 verification reports and inspect the existing models, vault services, Layout Studio, QML renderer, tests, and Git status.

**The current repository files and implemented schemas are authoritative.** Earlier examples may differ from the current schema: do not silently create another schema or migrate user files. Confirm that Phase 5 is present in the working branch; if it is absent, stop and report the issue rather than reconstructing it.

Before editing, give a short implementation plan and identify any genuine conflict between the documents and existing code. Then proceed with Phase 6 in small, testable increments.

### 2. User-facing acceptance outcome

A person should be able to perform the following **entirely through the desktop interface**, without terminal commands or editing Markdown/JSON:

1. Open a vault and navigate to a concrete day or week.
2. Create a habit, giving it a name, optional tags, temporal scope, and daily/weekday recurrence.
3. Accept the origin page's default scope or override it explicitly.
4. Bind that habit to a compatible checklist in an existing layout, or create and bind it through an appropriate GUI workflow.
5. In **tracking mode**, mark an eligible date as completed; optionally use explicit missed/skipped statuses **only if supported by the existing canonical contract**.
6. Correct or clear the status without generating duplicate check-ins.
7. Fill in a configured numeric input (e.g., `Tempo de estudo: 40 minutos`) and save a **typed observation** for the selected date.
8. Navigate away, return, close the app, reopen the vault, and find the same habit status and numeric value.
9. View the same canonical habit from another relevant period without creating another habit document.

The UI must display clear validation and save feedback. Missing or future records are **not failures**.

### 3. Core domain and file-first rules

Reuse the existing `PeriodRef`, `TemporalScope`, recurrence, layout, metric-definition, and vault contracts. Do not duplicate domain rules in QML.

- A habit is a canonical entity with a stable UUID; its origin page does **not** permanently limit its scope.
- Expected dates are the intersection of recurrence and temporal scope. Handle ISO weeks crossing months or years correctly.
- A habit check-in is associated with `habit_id` and an occurrence date. A typed field value is an observation associated with `field_id` and an observation date.
- **Do not store the same fact in both `checkins` and `observations`.** A habit-bound checklist creates/updates check-ins; a custom boolean-field checklist creates/updates boolean observations, as documented in `FILE_FORMAT.md`.
- Canonical dated records live in the documented local files, including daily-page frontmatter when the existing schema requires it. Layout JSON is presentation and binding only; SQLite remains a disposable index.
- Repeated saves must be idempotent. Updating a value should replace/revise the intended logical record without duplicating it, following existing contracts.
- Preserve unknown metadata, stable IDs, historical records, external edits, and atomic-write protections. Report unresolved conflicts rather than overwriting silently.
- Scope or recurrence changes may make historical records out of scope; preserve those records and surface the distinction instead of deleting or converting them to failures.
- Never backfill missed statuses for days before a field or layout revision became effective.
- Removing/reordering a visual block must not remove its underlying habit, metric definition, check-ins, or observations.
- Normal operation must remain offline, with no accounts, telemetry, or cloud dependencies.

### 4. GUI integration — extend, do not rebuild

Keep the approved Linear-inspired appearance, theme tokens, spacing, and subtle animations.

Integrate with the existing Layout Studio and page renderer:

- **Layout editing mode:** configure checklist/input components and bind existing canonical sources or create supported new ones.
- **Tracking mode:** display the resolved components and permit entry of real values/check-ins, without entering Layout Studio.
- Show the selected date and distinguish *not scheduled*, *pending/future*, *unrecorded*, and explicit recorded statuses as supported by the domain.
- Offer a clear habit form for name, tags, scope and recurrence; validate dates, weekdays, and required fields.
- Render typed input controls according to existing field definitions, beginning with numeric input and other types already supported by the current contract where practical.
- Provide keyboard access, visible focus, error states, and explicit feedback on saved or rejected edits.
- Do not introduce dummy buttons, fabricated completion statistics, or a replacement UI framework.

Use Python application services and Qt models/signals to bridge to QML; keep persistence and business logic outside QML.

### 5. Scope discipline

**This is Phase 6 only.** Do not implement advanced charts/rollups (Phase 8), calendar/events and full note/image workflows (Phase 7), `.hwpack` export/backups (Phase 9), mobile, login, cloud sync, or unrelated redesigns.

Existing visual chart placeholders may remain placeholders, clearly indicated as not yet functional.

### 6. Tests and proof of functionality

Add deterministic tests in temporary vaults for:

1. Default and overridden scopes; weekday recurrence; month/ISO-week boundaries.
2. Habit creation, UUID identity, search/tags and binding to a checklist.
3. Creating, correcting and clearing a check-in for an eligible day.
4. Idempotent writes and no duplicate check-ins.
5. `unrecorded`/`future` not becoming `missed` automatically.
6. Typed numeric-field observation creation, editing, validation, and persistence by `field_id`.
7. No duplication between habit check-ins and field observations.
8. Data retained when block position, layout revision, or source visibility changes.
9. Correct behavior when a habit scope changes after check-ins already exist.
10. Reading existing vault documents; restart/reopen; deleting/rebuilding only a **test vault's** SQLite index.
11. Invalid/missing references, concurrent external edits and useful error handling.
12. Regression of Phases 1–5.

Run:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
```

Run existing phase-verification scripts where available. Verify native Qt interaction on a graphical Linux session if accessible, or report exactly what was tested offscreen instead. The GUI acceptance demonstration must include **both a habit check-in and a typed numeric observation**, saved and recovered in a new process.

Do not claim success for checks that were not executed.

### 7. Documentation and GitHub delivery

Create/update `docs/verification/phase-6.md` with implemented functionality, file contracts, executed commands and results, manual GUI steps, limitations, and roadmap acceptance status. Update `README.md`/`ROADMAP.md` only when necessary.

For Git:

- Inspect branch, status, and remote before making changes. Base the work on the latest approved Phase 5 code.
- Prefer feature branch `feat/phase-6-habit-tracking`; do not discard or overwrite uncommitted work or make destructive Git operations.
- At completion, inspect the diff for private vaults, secrets, SQLite files, test artifacts, and unrelated changes.
- After validations, commit and push the feature branch **if repository permissions and the handoff workflow allow it**; otherwise provide exact commands.
- Open or prepare a Pull Request into `main` with a concise description and tests. **Never merge automatically**; the owner will review and approve.

### 8. Final report and stopping rule

Summarize:

1. What is now usable in the GUI and how to test it.
2. Habit-check-in and numeric-observation storage behavior.
3. Files changed and actual tests executed.
4. Limitations, regressions, and unverified GUI behavior.
5. Branch/commit/PR status.
6. Whether all **actual Phase 6 criteria in `ROADMAP.md`** are met.

**Stop at Phase 6. Do not start Phase 7.** If some acceptance criterion cannot be met, state it plainly rather than labeling the phase complete.
