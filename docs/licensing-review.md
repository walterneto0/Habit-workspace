# Licensing and contributor-rights notes

The maintainer has adopted the official
[PolyForm Noncommercial License 1.0.0](../LICENSE) for Habit Workspace's
original source code. The complete unmodified license text is in `LICENSE`,
with the project's required copyright notice appended.

Habit Workspace is **source-available**, not OSI-approved open-source software.
The license permits use, study, modification, and redistribution for permitted
noncommercial purposes under its terms. Commercial use requires separate
authorization from the relevant copyright holder(s). This summary is not a
substitute for the complete license or legal advice.

The project listing is at
[github.com/walterneto0/habit-workspace](https://github.com/walterneto0/habit-workspace).

## What the license permits and restricts

The official terms grant copyright permissions to use the software for
permitted purposes and additional permissions to distribute copies and make
changes or new works for those purposes. The text identifies personal research,
experimentation, testing for public knowledge, personal study, private
entertainment, hobbies, amateur pursuits, and religious observance without
anticipated commercial application as permitted personal uses. It also
identifies charitable organizations, educational institutions, public research
organizations, public safety or health organizations, environmental protection
organizations, and government institutions as permitted noncommercial
organizations, regardless of funding source or obligations.

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
review and provide a clear contact path for commercial permission requests.

PolyForm Noncommercial is **not an OSI-approved open-source license**. Describe
the project as source-available and noncommercially licensed, not unrestricted
open source.

## Dependencies are separately licensed

The Habit Workspace license covers only project-authored material for which the
copyright holder(s) have rights. It does not replace, narrow, or relicense
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

External contributors retain copyright in their contributions; there is no
automatic assignment of ownership to the maintainer. Under the contribution
policy, accepted contributions are distributed as part of the project under
PolyForm Noncommercial 1.0.0 for permitted noncommercial purposes. No CLA or
copyright-assignment process is currently in place. This project license does
not itself provide the maintainer separate commercial sublicensing rights to
external contributors' work.

If the maintainer later wants to offer commercial licensing or dual licensing,
the maintainer should first obtain express, documented rights from every
relevant copyright holder—typically through a carefully reviewed contributor
license agreement granting the necessary commercial sublicensing rights, or
through copyright assignment. Existing contributions cannot be assumed
relicensable merely because they were submitted to a public repository. Third
party code and dependency licenses need separate review as well.

## Remaining considerations

- The existing Git history is intentionally preserved, including its author
  identities and agent-session identifiers. Public publication will expose that
  existing metadata; it is preserved at the maintainer's direction.
- Configure GitHub's private vulnerability-reporting and conduct-reporting
  contacts as repository settings.
- Complete a release-specific Qt/module/notices review before distributing
  binaries.
- For any future commercial or dual-licensing offer, obtain express rights from
  each relevant copyright holder (for example through an appropriately reviewed
  CLA or copyright assignment). Existing contributor rights cannot be presumed.
