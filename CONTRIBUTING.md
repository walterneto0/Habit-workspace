# Contributing

Thank you for helping improve Habit Workspace. The project is pre-alpha, so
focused, reviewable contributions are especially useful.

## Before opening an issue or pull request

- Check the [roadmap](ROADMAP.md), [product requirements](PRODUCT.md), and
  relevant file-format and architecture specifications.
- Keep work within completed behavior or an explicitly requested roadmap phase.
  Phase 5 has not started; repository-preparation work must not implement it.
- Search existing issues and pull requests once the public repository is
  available.
- Do not attach real vault files, personal data, credentials, private logs, or
  screenshots containing personal information.

## Development setup

The currently verified environment is Linux x86_64 with Python 3.14:

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-deps --no-build-isolation -e '.[dev]'
```

Choose a test vault outside the checkout. The tests and phase verification
scripts use temporary vaults.

## Checks

Run these before requesting review:

```bash
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m pytest -q
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python -m habit_workspace --smoke-test
```

When changes affect existing vault behavior, also run the relevant
`tools/verify_phase*.py` checks. Report commands that were not run and any
platform limitations. Do not claim visual/native verification from offscreen
tests alone.

## Contribution expectations

- Make small, coherent changes with tests for behavior or format changes.
- Preserve file-first ownership: canonical data belongs in vault files, never
  only in SQLite.
- Treat imported Markdown, YAML, JSON, archives, paths, and images as untrusted.
- Preserve unknown metadata and original files on validation failures.
- Keep domain code independent of Qt; do not execute content from vault files.
- Update English repository documentation when behavior changes. The initial
  in-app language remains Brazilian Portuguese.
- Do not add dependencies without a clear need and license review.

## Licensing and provenance

Habit Workspace's original source code is licensed under the
[PolyForm Noncommercial License 1.0.0](LICENSE). The project is
source-available, not OSI-approved open-source software. Contributions that are
accepted and distributed as part of the project are made available under those
terms for permitted noncommercial purposes.

Contributors retain copyright in their contributions; submission does not
assign ownership to the maintainer. By submitting a contribution for inclusion,
you confirm you have the right to contribute it and authorize its distribution
as part of Habit Workspace under the project license. This does not grant
commercial-use rights or authorize separate commercial sublicensing of your
contribution. No CLA or copyright-assignment process is currently in place.
Include attribution and license information for third-party material, and do
not submit work you cannot legally contribute.

If a future commercial or dual-licensing model is considered, contributor
permissions will need to be addressed explicitly with relevant copyright
holders before relying on contributed work for that purpose.

## Pull requests

Use the pull request template. Explain the problem and scope, list the tests
actually run, and call out data-format, privacy, licensing, or compatibility
implications. The maintainer may ask for revisions or defer work that conflicts
with the current roadmap.
