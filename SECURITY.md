# Security Policy

Habit Workspace is pre-alpha. Do not use it as the sole store for important or
sensitive information. Vault files are plaintext and are not encrypted by the
application.

## Reporting a vulnerability

Please do not report exploitable vulnerabilities in public issues or pull
requests. Use **Report a vulnerability** in the
[repository's Security tab](https://github.com/walterneto0/habit-workspace/security/advisories/new)
when private vulnerability reporting is enabled. If it is unavailable, contact
the repository owner privately; do not include vault contents or credentials
in the initial report.

Include the affected version or commit, platform, impact, and a minimal
reproduction using synthetic data. Allow maintainers reasonable time to
investigate and prepare a fix before public disclosure.

## Supported versions

There are no stable releases yet. Security fixes are considered for the current
development branch. Older commits and pre-alpha snapshots may not receive
updates.

## Scope and user data

Security reports are particularly useful for file parsing, path containment,
untrusted JSON/YAML/Markdown handling, atomic writes, dependency vulnerabilities,
and privacy leaks. Never send a real vault, private export, token, or secret in a
report; create a minimal synthetic example instead.
