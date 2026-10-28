"""Command-line and desktop entry point without import-time side effects."""

import argparse


def main() -> int:
    parser = argparse.ArgumentParser(description="Habit Workspace")
    parser.add_argument(
        "--smoke-test", action="store_true", help="Load QML, process events, and exit."
    )
    args = parser.parse_args()
    from habit_workspace.bootstrap import run

    return run(smoke_test=args.smoke_test)


if __name__ == "__main__":
    raise SystemExit(main())
