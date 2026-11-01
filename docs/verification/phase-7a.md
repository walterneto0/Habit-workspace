# Phase 7A — Remote CI verification (2026-10-31)

> Proposed repository path: `docs/verification/phase-7a.md`. This document reports observed GitHub evidence; it does not substitute for manual product acceptance.

- Repository: `walterneto0/Habit-workspace`
- Merged PR: [#12 — feat: add personal tasks and goals (Phase 7A)](https://github.com/walterneto0/Habit-workspace/pull/12)
- PR head: `6db3579afd9bf1c4e7050b2cb17c0b19ad6d22a3`
- Merge on `main`: `cd2dbc486678f7dc3b5db22e4165ba92781549e1`
- [PR CI run #41249245500](https://github.com/walterneto0/Habit-workspace/actions/runs/41249245500): **success**. Job steps: Ruff lint, Ruff format, pytest, QML smoke all success.
- Pytest in CI job logs: **313 passed in 110.22s**.
- Ruff format log: **118 files already formatted**.
- QML startup log: **one visible root window**.
- [Post-merge `main` CI #41249552782](https://github.com/walterneto0/Habit-workspace/actions/runs/41249552782): **success** at verification time.

## Implemented, per PR #12 file review

Canonical schema-v4 tasks and goals, direct planning views/forms, revision-aware asynchronous persistence, scoped/due/carryover projections and task bindings to existing lists/checklists. Tests cover the new planning domain and worker interactions. Native X11/offscreen GUI checks were also reported in the developer's local verification, but the CI run above is not equivalent to an automated X11 or human accessibility audit.

## Follow-up/limitation

Phase 7A's goal projection currently includes goals when their temporal scopes intersect child pages. This predates the clarified product requirement: goals must be owned by a home period, while child-period follow-up must be **explicitly configured**. Correct this in Phase 7B without rewriting historical files or inventing daily measurements. See `docs/planning/phase-7b-direction.md`.

No assertion is made about Windows/macOS, assistive technology or production safety. Maintain independent backups and use disposable data for tests.
