"""Phase 6.5A responsiveness benchmark on disposable synthetic vaults.

Generates non-sensitive vaults (small/medium/large), then times the operations a
person performs through ``WorkspaceController`` on the GUI thread: opening the
vault, navigating periods and searching, saving a check-in and a typed value,
manual reindex and the periodic watcher refresh (unchanged vs. modified vault).

The controller runs under a ``QCoreApplication`` without QML rendering, so the
numbers measure the synchronous Python/file/SQLite work a slot blocks the event
loop for, not frame rendering. Vaults live in a temporary directory and are
deleted afterwards. Usage::

    .venv/bin/python tools/benchmark_vault.py [--sizes small,medium,large] [--json out.json]
"""

import argparse
import json
import platform
import statistics
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from PySide6 import __version__ as pyside_version
from PySide6.QtCore import QCoreApplication, QSettings

from habit_workspace.application.layouts import LayoutService
from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.documents import Document
from habit_workspace.domain.habits import Habit
from habit_workspace.domain.layouts import (
    Binding,
    ChecklistConfig,
    Component,
    InputConfig,
    LayoutTemplate,
    NoteConfig,
)
from habit_workspace.domain.metrics import FieldDefinition, SourceSelection
from habit_workspace.domain.temporal import PeriodRef, Recurrence, TemporalScope
from habit_workspace.presentation.controllers import WorkspaceController
from habit_workspace.vault.format import encode
from habit_workspace.vault.habits import habit_document
from habit_workspace.vault.metrics import field_document

TZ = timezone(timedelta(hours=-3))
TODAY = date(2026, 10, 29)
SIZES = {
    # habits, typed fields, days of history, free notes
    "small": (8, 2, 60, 20),
    "medium": (25, 5, 365, 200),
    "large": (50, 10, 3 * 365, 1000),
}
NOTE_BODY = "Registro sintético de benchmark. " * 30


def write(root: Path, relative: str, document: Document) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encode(document))


def generate(root: Path, size: str) -> dict:
    habits_count, fields_count, days, notes = SIZES[size]
    session = VaultSession.create(root, f"Benchmark {size}")
    start = TODAY - timedelta(days=days - 1)
    habits = [
        Habit(
            uuid4(),
            f"Hábito {i:03}",
            TemporalScope(start, None),
            Recurrence.daily() if i % 3 else Recurrence.weekdays((1, 3, 5)),
            tags=("rotina",) if i % 2 else ("estudos",),
        )
        for i in range(habits_count)
    ]
    for habit in habits:
        write(root, f"Items/Habits/{habit.id}.md", habit_document(habit))
    active = datetime.combine(start, datetime.min.time(), TZ)
    fields = [
        FieldDefinition(uuid4(), f"Campo {i:02}", "integer", active, aggregation="sum")
        for i in range(fields_count)
    ]
    for field in fields:
        write(root, f"Items/Metrics/{field.id}.md", field_document(field))
    files = habits_count + fields_count
    for offset in range(days - 1):  # leave today unrecorded
        day = start + timedelta(days=offset)
        recorded = datetime.combine(day, datetime.min.time(), TZ).replace(hour=21)
        checkins = [
            {
                "id": str(uuid4()),
                "habit_id": str(h.id),
                "date": day.isoformat(),
                "state": ("done", "skipped", "missed")[(offset + j) % 5 % 3],
                "label_snapshot": h.name,
                "recorded_at": recorded.isoformat(),
            }
            for j, h in enumerate(habits)
            if h.is_scheduled(day) and (offset + j) % 4
        ]
        observations = [
            {
                "id": str(uuid4()),
                "field_id": str(f.id),
                "field_label_snapshot": f.name,
                "observed_date": day.isoformat(),
                "recorded_at": recorded.isoformat(),
                "value": (offset * 7 + j) % 90,
            }
            for j, f in enumerate(fields)
        ]
        hw = {"schema_version": 4, "kind": "day_page", "id": str(uuid4()), "date": day.isoformat()}
        hw |= {"checkins": checkins} if checkins else {}
        hw |= {"observations": observations} if observations else {}
        write(root, f"Pages/Days/{hw['id']}.md", Document.from_metadata({"hw": hw}, ""))
        files += 1
    for i in range(notes):
        hw = {"schema_version": 4, "kind": "note", "id": str(uuid4()), "title": f"Nota {i:04}"}
        write(root, f"Notes/{hw['id']}.md", Document.from_metadata({"hw": hw}, NOTE_BODY))
        files += 1
    session.scan()
    week = PeriodRef.containing("week", TODAY)
    layout = LayoutTemplate(
        uuid4(),
        1,
        "Semana de benchmark",
        (
            Component(
                uuid4(),
                "checklist",
                "Rotina",
                ChecklistConfig(
                    SourceSelection("by_tags", tags=("rotina",), value_types=("habit",))
                ),
            ),
            Component(
                uuid4(),
                "integer_input",
                fields[0].name,
                InputConfig("integer"),
                binding=Binding(fields[0].id, "metric"),
            ),
            Component(uuid4(), "note", "Notas", NoteConfig()),
        ),
    )
    LayoutService(session).save_revision(week, layout, active)
    return dict(
        habits=habits_count,
        fields=fields_count,
        days=days,
        notes=notes,
        files=files + 2,
        bytes=sum(p.stat().st_size for p in root.rglob("*") if p.is_file()),
        habit_ids=[str(h.id) for h in habits],
        field_id=str(fields[0].id),
    )


def timed(action, repeat: int) -> dict:
    samples = []
    for _ in range(repeat):
        started = time.perf_counter()
        action()
        samples.append((time.perf_counter() - started) * 1000)
    return dict(
        median_ms=round(statistics.median(samples), 1),
        max_ms=round(max(samples), 1),
        n=repeat,
    )


def measure(root: Path, info: dict, repeat: int, settings_path: Path) -> dict:
    app = QCoreApplication.instance() or QCoreApplication([])
    settings = QSettings(str(settings_path), QSettings.Format.IniFormat)
    controller = WorkspaceController(settings=settings, today=TODAY)
    results = {}
    try:

        def open_vault():
            assert controller.openVault(str(root)), controller.state["notice"]

        results["open_vault"] = timed(open_vault, repeat)
        # Keep the periodic timer from firing between measurements.
        controller.watcher.periodic.stop()
        days = iter(range(10_000))
        results["navigate_day"] = timed(
            lambda: controller.navigate(
                "day", (TODAY - timedelta(days=next(days) % 30)).isoformat()
            ),
            repeat,
        )
        results["navigate_week"] = timed(
            lambda: controller.navigate("week", TODAY.isoformat()), repeat
        )
        results["navigate_month"] = timed(
            lambda: controller.navigate("month", TODAY.isoformat()), repeat
        )
        results["search"] = timed(lambda: controller.setQuery(f"Nota {next(days)}"), repeat)
        controller.setQuery("")
        controller.navigate("day", TODAY.isoformat())
        habit = info["habit_ids"][1]
        states = iter(["done", ""] * repeat)
        previous = {"value": None}

        def checkin_simple():
            state = next(states)
            expected = json.dumps(previous["value"])
            assert controller.setCheckin(habit, state, expected), controller.state["notice"]
            previous["value"] = state or None

        results["checkin_save"] = timed(checkin_simple, repeat)
        values = iter(range(1, 10_000))
        last = {"value": None}

        def observation():
            value = next(values)
            ok = controller.saveObservation(
                info["field_id"], "", str(value), json.dumps(last["value"])
            )
            assert ok, controller.state["notice"]
            last["value"] = value

        results["typed_value_save"] = timed(observation, repeat)
        results["manual_reindex"] = timed(controller.reindex, repeat)
        watcher = controller.watcher
        results["watcher_refresh_unchanged"] = timed(watcher.refresh, repeat)
        note = next((root / "Notes").iterdir())
        counter = iter(range(10_000))

        def modified():
            raw = note.read_bytes()
            note.write_bytes(raw.rstrip(b"\n") + f" {next(counter)}\n".encode())
            watcher.refresh()

        results["watcher_refresh_modified"] = timed(modified, repeat)
        started = time.perf_counter()
        controller.session.scan()
        results["breakdown_session_scan_ms"] = round((time.perf_counter() - started) * 1000, 1)
        from habit_workspace.vault.scanner import scan

        started = time.perf_counter()
        report = scan(root)
        results["breakdown_file_scan_ms"] = round((time.perf_counter() - started) * 1000, 1)
        started = time.perf_counter()
        controller.session.index.rebuild(report)
        results["breakdown_index_rebuild_ms"] = round((time.perf_counter() - started) * 1000, 1)
        started = time.perf_counter()
        controller._state = {}
        controller._publish()
        results["breakdown_publish_state_ms"] = round((time.perf_counter() - started) * 1000, 1)
    finally:
        controller.close()
        app.processEvents()
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sizes", default="small,medium,large")
    parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--gui", action="store_true", help="Measure a rendered Qt Quick window")
    parser.add_argument("--profile", type=Path, help="Write cProfile scan diagnostics")
    args = parser.parse_args()
    report = {
        "environment": dict(
            python=sys.version.split()[0],
            pyside6=pyside_version,
            platform=platform.platform(),
            processor=platform.processor() or platform.machine(),
        ),
        "results": {},
    }
    with TemporaryDirectory(prefix="hw-bench-") as temporary:
        for size in args.sizes.split(","):
            root = Path(temporary) / size
            started = time.perf_counter()
            info = generate(root, size)
            generated = round(time.perf_counter() - started, 1)
            if args.gui:
                from benchmark_gui import measure_gui

                results = measure_gui(root, info, args.repeat, Path(temporary) / f"{size}.ini")
            else:
                results = measure(root, info, args.repeat, Path(temporary) / f"{size}.ini")
            if args.profile:
                import cProfile
                import pstats

                from habit_workspace.vault.scanner import scan

                profiler = cProfile.Profile()
                profiler.runcall(scan, root)
                with args.profile.open("w") as stream:
                    pstats.Stats(profiler, stream=stream).sort_stats("cumulative").print_stats(45)
            info = {k: v for k, v in info.items() if k not in ("habit_ids", "field_id")}
            report["results"][size] = dict(vault=info, generate_s=generated, timings=results)
            print(f"\n== {size}: {info}", flush=True)
            for name, value in results.items():
                print(f"  {name:32} {value}", flush=True)
    if args.json:
        args.json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
