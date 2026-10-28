# Licensing review — maintainer decision required

**No project license has been selected or adopted.** This review is informational
and does not grant permission to use, modify, or redistribute Habit Workspace.
Do not add a `LICENSE` file, license classifier, or SPDX license expression
until the maintainer approves a choice.

Habit Workspace is intended to be **source-available**, not described as
OSI-approved open-source software. Source visibility by itself grants no reuse
rights. Until a license is selected and included, assume all rights reserved.
This is not legal advice; obtain qualified legal review before public release
and especially before commercial distribution.

## Candidate: PolyForm Noncommercial License 1.0.0

The maintainer is evaluating the
[official PolyForm Noncommercial 1.0.0 terms](https://polyformproject.org/licenses/noncommercial/1.0.0/)
and its [SPDX license listing](https://spdx.org/licenses/PolyForm-Noncommercial-1.0.0.html).
The license is not yet adopted.

At a high level, the license grants copyright permissions to use the software
for permitted purposes, and additional permissions to distribute copies and to
make and distribute changes or new works for those purposes. The official text
expressly treats personal research, experimentation, testing for public
knowledge, study, private entertainment, hobbies, amateur pursuits, and
religious observance without anticipated commercial application as permitted
personal uses. It also explicitly permits use by specified noncommercial
organizations—including charitable organizations, educational institutions,
public research, public safety/health, environmental protection, and government
institutions—regardless of funding source or funding obligations.

The license does **not** grant commercial-purpose rights. A commercial use
would require separate, explicit authorization from the copyright holder or
another license that grants that use. The official text does not grant a right
to sublicense or transfer licenses, and requires recipients of distributed
copies to receive the license terms or their URL and any required notices.
Consult the official terms for the complete conditions, patent provisions,
termination rules, and definitions.

The phrase “noncommercial purpose” and its application to mixed-purpose,
employer-sponsored, hosted, or revenue-supported activity may require
interpretation. Do not promise that every free-of-charge or educational use is
automatically permitted; the license's specific terms control. Obtain legal
review and provide a clear contact path for permission requests before
adoption.

PolyForm Noncommercial is **not an OSI-approved open-source license**. If
adopted, the project should continue to call itself source-available and
noncommercially licensed, not unrestricted open source.

## Dependencies are separately licensed

The Habit Workspace license would cover only project-authored material for
which the maintainers have rights. It would not replace, narrow, or relicense
third-party dependencies. Their notices and license terms continue to apply.

The current dependency inventory reports PySide6, shiboken6, and the Qt for
Python distribution packages under the metadata expression
`LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only`. Qt modules and Qt for Python
also include components with additional third-party notices. The application
uses PySide6/Qt libraries; it does not currently distribute a bundled
application binary. If binaries or dependency bundles are distributed, review
the exact Qt modules, plugins, and transitive components shipped; include
required notices and license texts; and satisfy the selected LGPL/GPL or other
applicable terms. The dependency licenses do not grant commercial-use
permission for Habit Workspace's own code, and a noncommercial project license
cannot take away permissions that a dependency's own license grants to
recipients of that dependency.

Other currently pinned packages include MIT-licensed packages and packages
reported as Apache-2.0 OR BSD-2-Clause and BSD-2-Clause. Refer to
[the dependency inventory](dependencies.md) and each upstream package's
authoritative license files. Installed metadata is a triage aid, not a complete
redistribution audit.

## Contributors and future commercial licensing

Contributors generally retain copyright in their contributions. This project
currently has no CLA or copyright-assignment process. A contribution policy
that places accepted changes under a future project license does not by itself
mean contributors have assigned their copyright or granted every separate
commercial right.

If the maintainer later wants to offer commercial licensing or dual licensing,
the maintainer should first obtain express, documented rights from every
relevant copyright holder—typically through a carefully reviewed contributor
license agreement granting the necessary commercial sublicensing rights, or
through copyright assignment. Existing contributions cannot be assumed
relicensable merely because they were submitted to a public repository. Third
party code and dependency licenses need separate review as well.

## Decisions before publication

- Approve or reject PolyForm Noncommercial 1.0.0 after legal review.
- Identify the copyright holder(s), required copyright notice, and permission
  contact.
- Create the GitHub repository, configure its URL and private vulnerability /
  conduct-reporting channels, then add those URLs to package metadata and docs.
- Decide how existing commit author identities and agent-session identifiers
  should appear in public Git history.
- Decide the contribution terms and whether a CLA or equivalent is needed.
- Complete a release-specific Qt/module/notices review before distributing
  binaries.
- Add the exact approved license text and matching package metadata only after
  explicit maintainer approval.
