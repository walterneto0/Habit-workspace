"""Blocked decoders must leave the GUI alive and cannot publish stale pixels."""

import base64
import threading
from datetime import date, datetime
from uuid import uuid4

from PySide6.QtCore import QCoreApplication, QSettings, QTimer
from PySide6.QtGui import QImage
from test_vault_tasks import wait

from habit_workspace.application.layouts import LayoutService
from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.layouts import Component, ImageConfig, LayoutTemplate
from habit_workspace.domain.temporal import PeriodRef
from habit_workspace.presentation import layout_assets
from habit_workspace.presentation.controllers import WorkspaceController
from habit_workspace.presentation.vault_tasks import VaultTasks


def test_gui_alive_during_cold_decode_and_stale_page_rejected(tmp_path, monkeypatch):
    app = QCoreApplication.instance() or QCoreApplication([])
    s = VaultSession.create(tmp_path / "vault", "Images")
    (s.root / "Assets").mkdir(exist_ok=True)
    path = s.root / "Assets/local.png"
    image = QImage(2000, 2000, QImage.Format_RGB32)
    image.fill(0xFF336699)
    assert image.save(str(path))
    layout = LayoutTemplate(
        uuid4(),
        1,
        "Images",
        (Component(uuid4(), "image", "Local", ImageConfig("Assets/local.png")),),
    )
    LayoutService(s).save_revision(PeriodRef("week/2026-W44"), layout, datetime.now().astimezone())
    entered, release = threading.Event(), threading.Event()
    original, threads = layout_assets._decode, []

    def blocked(*args):
        threads.append(threading.current_thread())
        entered.set()
        assert release.wait(5)
        return original(*args)

    monkeypatch.setattr(layout_assets, "_decode", blocked)
    layout_assets._CACHE.clear()
    w = WorkspaceController(
        today=date(2026, 10, 29), settings=QSettings(str(tmp_path / "prefs"), QSettings.IniFormat)
    )
    ticks = []
    timer = QTimer()
    timer.setInterval(1)
    timer.timeout.connect(lambda: ticks.append(True))
    try:
        w._attach(s)
        w.navigate("week", "2026-10-29")
        wait(entered.is_set)
        timer.start()
        wait(lambda: len(ticks) >= 3)
        assert not w.actions.busy, "image reads never lock forms/capture"
        w.navigate("day", "2026-11-02")
        expected = w.state["composition"]
        release.set()
        wait(lambda: not w.actions.tasks.active)
        app.processEvents()
        assert w.state["period"] == "day/2026-11-02"
        assert w.state["composition"] == expected
        w.navigate("week", "2026-10-29")
        wait(lambda: bool(w.state["composition"]["blocks"][0].get("imageSource")))
        assert all(t is not threading.main_thread() for t in threads)
        count = len(threads)
        w._publish()
        assert len(threads) == count
        # Asset-only changes do not change the document fingerprint. A normal
        # background refresh must still revalidate visible image revisions.
        previous = w.state["composition"]["blocks"][0]["imageSource"]
        image.fill(0xFF998877)
        assert image.save(str(path))
        w.actions.tasks.refresh()
        wait(lambda: not w.actions.tasks.active)
        wait(lambda: bool(w.state["composition"]["blocks"][0].get("imageSource")))
        assert w.state["composition"]["blocks"][0]["imageSource"] != previous
        assert len(threads) == count + 1
        # Containment is revalidated even when pixels are cached.
        path.unlink()
        path.symlink_to(tmp_path / "outside.png")
        w._publish()
        block = w.state["composition"]["blocks"][0]
        assert not block.get("imageSource") and "indisponível" in block["detail"]
    finally:
        timer.stop()
        release.set()
        w.close()


def test_changed_image_during_decode_never_reuses_old_revision(tmp_path, monkeypatch):
    QCoreApplication.instance() or QCoreApplication([])
    path = tmp_path / "local.png"
    image = QImage(20, 20, QImage.Format_RGB32)
    image.fill(0xFF112233)
    assert image.save(str(path))
    original = layout_assets._decode

    def edited(*args):
        image.fill(0xFF998877)
        assert image.save(str(path))
        return original(*args)

    monkeypatch.setattr(layout_assets, "_decode", edited)
    old = layout_assets.image_revision(tmp_path, "local.png")
    result = layout_assets.load_images(tmp_path, ("local.png",))
    assert result[0][1] == old
    assert old != layout_assets.image_revision(tmp_path, "local.png")
    assert layout_assets.cached_source(layout_assets.image_revision(tmp_path, "local.png")) is None


def test_preview_dimensions_original_bytes_and_batch_memory_limits(tmp_path, monkeypatch):
    image = QImage(2000, 2000, QImage.Format_RGB32)
    image.fill(0xFF112233)
    path = tmp_path / "local.png"
    assert image.save(str(path))
    original = path.read_bytes()
    source = layout_assets.image_source(tmp_path, "local.png")
    preview = QImage.fromData(base64.b64decode(source.split(",", 1)[1]))
    assert preview.width() == preview.height() == 1024
    assert path.read_bytes() == original
    monkeypatch.setattr(layout_assets, "_CACHE_BYTES", len(source) + 10)
    rows = layout_assets.load_images(tmp_path, ("local.png", "local.png"))
    assert rows[0][2] and not rows[1][2] and rows[1][3]
    rows = layout_assets.markdown_images(tmp_path, "![a](Assets/local.png)", lambda _: source)
    assert rows[0]["source"]
    rows = layout_assets.markdown_images(tmp_path, "![a](Assets/local.png)" * 2, lambda _: source)
    assert rows[0]["source"] and not rows[1]["source"] and rows[1]["error"]


def test_media_queue_coalesces_and_preserves_accepted_write(tmp_path, monkeypatch):
    QCoreApplication.instance() or QCoreApplication([])
    s = VaultSession.create(tmp_path / "vault", "Queue")
    entered, release = threading.Event(), threading.Event()
    calls, completed = [], []

    def blocked(_root, paths):
        calls.append(paths)
        entered.set()
        assert release.wait(5)
        return []

    monkeypatch.setattr(layout_assets, "load_images", blocked)
    tasks = VaultTasks(s.root)
    tasks.completed.connect(lambda *args: completed.append(args[0]))
    try:
        tasks.media(dict(context="page", generation=1, paths=("old.png",)))
        assert entered.wait(2)
        for generation in range(2, 20):
            tasks.media(dict(context="page", generation=generation, paths=(str(generation),)))
        assert len(tasks._media_pending) == 1
        assert tasks.capture(
            "planning_save",
            dict(
                loaded=None,
                fields=dict(title="Accepted"),
                kind="task",
                period=PeriodRef("day/2026-10-29"),
            ),
        )
        release.set()
        wait(lambda: not tasks.active)
        assert completed == ["layout_media", "planning_save", "layout_media"]
        assert calls == [("old.png",), ("19",)]
        assert not tasks.saving
        assert VaultSession.open(s.root).report.documents[0].document.title == "Accepted"
    finally:
        release.set()
        tasks.close()
