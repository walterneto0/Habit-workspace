"""Command-line and desktop entry point without import-time side effects."""

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Habit Workspace")
    parser.add_argument(
        "--smoke-test", action="store_true", help="Load QML, process events, and exit."
    )
    parser.add_argument("--vault", type=Path, help="Open a vault and watch external edits in QML")
    commands = parser.add_subparsers(dest="command")
    from habit_workspace.application.cli import configure

    configure(commands.add_parser("vault", help="Phase 1 local vault diagnostics"))
    args = parser.parse_args()
    if args.command == "vault":
        from habit_workspace.application.cli import run as run_cli

        return run_cli(args)
    from habit_workspace.bootstrap import run

    return run(smoke_test=args.smoke_test, vault_directory=args.vault)


if __name__ == "__main__":
    raise SystemExit(main())
