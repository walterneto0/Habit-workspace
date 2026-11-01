"""Reproducible rendered image measurements; synthetic disposable vault only."""

import json
import random
import threading
import time
from datetime import date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from benchmark_gui import wait
from PySide6.QtCore import QSettings, QTimer
from PySide6.QtGui import QGuiApplication, QImage
from PySide6.QtQuickControls2 import QQuickStyle
from verify_phase65b import Journey

from habit_workspace.application.layouts import LayoutService
from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.layouts import Component, ImageConfig, LayoutTemplate
from habit_workspace.domain.temporal import PeriodRef
from habit_workspace.presentation import layout_assets
from habit_workspace.presentation.controllers import WorkspaceController


def main():
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication([])
    with TemporaryDirectory(prefix="hw-7b1-images-") as tmp:
        base = Path(tmp)
        vault = VaultSession.create(base / "vault", "Synthetic image benchmark")
        assets = vault.root / "Assets"
        assets.mkdir(exist_ok=True)
        rng = random.Random(7)
        paths, fixtures = [], []
        for index, extension in enumerate(("png", "jpg", "webp") * 2):
            raw = rng.randbytes(4_000_000)
            if extension == "png":
                raw = raw.translate(bytes(i & 0xE0 for i in range(256)))
            image = QImage(raw, 2000, 2000, 2000, QImage.Format_Grayscale8)
            path = assets / f"synthetic-{index}.{extension}"
            assert image.save(str(path), quality=60 if extension != "png" else -1)
            assert path.stat().st_size <= 2 * 1024 * 1024
            paths.append(path)
            fixtures.append(dict(format=extension, bytes=path.stat().st_size, pixels=4_000_000))
        layout = LayoutTemplate(
            uuid4(),
            1,
            "Image benchmark",
            tuple(
                Component(uuid4(), "image", p.name, ImageConfig("Assets/" + p.name)) for p in paths
            ),
        )
        LayoutService(vault).save_revision(
            PeriodRef("week/2026-W44"), layout, datetime.now().astimezone()
        )
        w = WorkspaceController(
            today=date(2026, 10, 29),
            settings=QSettings(str(base / "prefs"), QSettings.IniFormat),
        )
        ui = Journey(app, w)
        decode, gaps, frames = [], [], []
        original = layout_assets._decode

        def measured(*args):
            start = time.perf_counter()
            result = original(*args)
            decode.append(
                dict(
                    ms=(time.perf_counter() - start) * 1000,
                    main=threading.current_thread() is threading.main_thread(),
                )
            )
            return result

        layout_assets._decode = measured
        last = [time.perf_counter()]
        timer = QTimer()
        timer.setInterval(5)

        def tick():
            now = time.perf_counter()
            gaps.append(max(0, (now - last[0]) * 1000 - 5))
            last[0] = now

        timer.timeout.connect(tick)
        ui.window.frameSwapped.connect(lambda: frames.append(time.perf_counter()))
        results = {}

        def measure(name, action):
            gaps.clear()
            frames.clear()
            decode.clear()
            last[0] = time.perf_counter()
            timer.start()
            start = time.perf_counter()
            action()
            returned = time.perf_counter()
            wait(app, lambda: not w.actions.tasks.active)
            # Also wait for any GUI-side media request to be scheduled and rendered.
            ui.settle()
            wait(app, lambda: not w.actions.tasks.active)
            ui.settle()
            # The baseline's synchronous Images have no named readiness property;
            # they finish before navigation returns. New Images explicitly await Ready.
            if any(
                i.objectName().startswith("layout-image-") and i.property("decoded") is not None
                for i in ui.walk()
            ):
                wait(
                    app,
                    lambda: (
                        len(
                            [
                                i
                                for i in ui.walk()
                                if i.objectName().startswith("layout-image-")
                                and i.property("decoded")
                            ]
                        )
                        == len(paths)
                    ),
                )
            ui.settle()
            tick()
            results[name] = dict(
                slot_ms=round((returned - start) * 1000, 2),
                rendered_ms=round((frames[-1] - start) * 1000, 2),
                heartbeat_excess_ms=round(max(gaps, default=0), 2),
                decode_count=len(decode),
                main_thread_decodes=sum(d["main"] for d in decode),
                decode_ms=round(sum(d["ms"] for d in decode), 2),
            )
            timer.stop()

        try:
            w.actions.openVault(str(vault.root))
            wait(app, lambda: w.state["hasVault"] and not w.actions.opening)
            w.watcher.periodic.stop()
            layout_assets._CACHE.clear()
            measure("first_page_open", lambda: w.navigate("week", "2026-10-29"))
            for repeat in range(3):
                w.navigate("day", "2026-10-29")
                ui.settle()
                measure(f"repeat_navigation_{repeat + 1}", lambda: w.navigate("week", "2026-10-29"))
            measure("unrelated_publish", w._publish)
            measure("unchanged_refresh", w.actions.tasks.refresh)
            # A valid external replacement must invalidate exactly one cached asset.
            replacement = QImage(2000, 2000, QImage.Format_Grayscale8)
            replacement.fill(80)
            assert replacement.save(str(paths[0]))
            measure("external_image_edit", w._publish)
            print(
                json.dumps(
                    dict(
                        platform=app.platformName(),
                        fixtures=fixtures,
                        results=results,
                        qmlWarnings=ui.errors,
                    ),
                    indent=2,
                )
            )
        finally:
            timer.stop()
            layout_assets._decode = original
            w.close()
            ui.engine.deleteLater()
            app.processEvents()


if __name__ == "__main__":
    main()
