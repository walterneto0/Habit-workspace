from copy import deepcopy

import pytest
from PySide6.QtGui import QImage

from habit_workspace.application.content import ContentService
from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.documents import DocumentError
from habit_workspace.presentation.layout_assets import import_image, markdown_images
from habit_workspace.vault.atomic_io import ConflictError


@pytest.mark.parametrize(
    "period", ["year/2026", "month/2026-12", "week/2026-W53", "day/2027-01-01"]
)
def test_review_roundtrip_restart_and_index(tmp_path, period):
    s = VaultSession.create(tmp_path / "vault", "Review")
    service = ContentService(s)
    review = service.create("Reflection", "# Human text", period, kind="review", rating=4)
    doc = deepcopy(review.document)
    doc.metadata["custom"] = {"keep": True}
    doc.metadata["hw"]["assessment"]["custom"] = "keep"
    doc.bom, doc.newline = True, "\r\n"
    review = s.save(review, doc)
    saved = service.save(review, "Edited", "Commentary\r\n", period, rating=2)
    with pytest.raises(ConflictError):
        service.save(review, "Stale", "draft", period, rating=1)
    assert saved.path.read_bytes().startswith(b"\xef\xbb\xbf")
    s.index.path.unlink()
    loaded = VaultSession.open(s.root).load(saved.document.id)
    assert loaded.document.metadata["hw"]["period"] == period
    assert loaded.document.metadata["hw"]["assessment"] == {"rating": 2, "custom": "keep"}
    assert loaded.document.metadata["custom"] == {"keep": True}
    assert loaded.document.body == "Commentary\r\n"
    assert len(s.report.documents) == 1
    assert service.create("Another", "", period, kind="review").document.id != saved.document.id


@pytest.mark.parametrize(
    "period,rating", [("", 3), ("week/2026-W54", 3), ("year/2026", True), ("month/2026-10", 6)]
)
def test_invalid_reviews(tmp_path, period, rating):
    s = VaultSession.create(tmp_path / "vault", "Test")
    with pytest.raises(ValueError):
        ContentService(s).create("Invalid", "", period, kind="review", rating=rating)
    assert not s.scan().documents


def png(path):
    image = QImage(20, 20, QImage.Format_RGB32)
    image.fill(0xFF336699)
    assert image.save(str(path), "PNG")
    return path


def test_image_ingestion_and_offline_preview(tmp_path):
    s = VaultSession.create(tmp_path / "vault", "Assets")
    source = png(tmp_path / "original.png")
    relative = import_image(s.root, source)
    other = import_image(s.root, source)
    assert relative != other and relative.startswith("Assets/")
    note = ContentService(s).create("Image", f"![Alternative]({relative})")
    rows = markdown_images(s.root, note.document.body)
    assert rows[0]["source"].startswith("data:image/png;base64,")
    assert rows[0]["alt"] == "Alternative"
    s.index.path.unlink()
    reopened = VaultSession.open(s.root).load(note.document.id)
    assert markdown_images(s.root, reopened.document.body)[0]["source"] == rows[0]["source"]
    (s.root / relative).write_bytes(b"corrupt")
    assert markdown_images(s.root, reopened.document.body)[0]["error"]
    (s.root / relative).unlink()
    assert markdown_images(s.root, reopened.document.body)[0]["error"]


def test_unsafe_images(tmp_path):
    root = tmp_path / "vault"
    root.mkdir()
    source = png(tmp_path / "image.png")
    link = tmp_path / "link.png"
    link.symlink_to(source)
    with pytest.raises(DocumentError):
        import_image(root, link)
    alias = tmp_path / "alias"
    alias.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(DocumentError):
        import_image(root, alias / source.name)
    wrong = tmp_path / "wrong.jpg"
    wrong.write_bytes(source.read_bytes())
    with pytest.raises(DocumentError):
        import_image(root, wrong)
    large = tmp_path / "large.png"
    large.write_bytes(b"x" * (2 * 1024 * 1024 + 1))
    with pytest.raises(DocumentError):
        import_image(root, large)
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "Assets").symlink_to(outside, target_is_directory=True)
    with pytest.raises(DocumentError):
        import_image(root, source)
    assert not list(outside.iterdir())
    for path in (
        "../image.png",
        "/tmp/image.png",
        "https://example.com/a.png",
        "Assets/../image.png",
    ):
        assert markdown_images(root, f"![unsafe]({path})")[0]["error"]
    assert not list(root.glob("*.md"))


def test_pixel_limit(tmp_path):
    root = tmp_path / "vault"
    root.mkdir()
    source = tmp_path / "large.png"
    image = QImage(2001, 2000, QImage.Format_RGB32)
    image.fill(0)
    assert image.save(str(source))
    with pytest.raises(DocumentError):
        import_image(root, source)


def test_review_import_duplicates_and_preserve_invalid(tmp_path):
    from habit_workspace.application.imports import ImportService

    source = VaultSession.create(tmp_path / "source", "Source")
    review = ContentService(source).create(
        "Week review", "Reflection", "week/2026-W53", kind="review", rating=3
    )
    target = VaultSession.create(tmp_path / "target", "Target")
    assert len(ImportService(target).import_files([review.path]).imported) == 1
    assert len(ImportService(target).import_files([review.path]).skipped) == 1
    review = ContentService(source).save(review, "Changed", "New", "week/2026-W53", rating=4)
    assert ImportService(target).import_files([review.path]).conflicting
    raw = review.path.read_bytes().replace(b"week/2026-W53", b"week/2026-W54")
    review.path.write_bytes(raw)
    assert source.scan().invalid
    assert review.path.read_bytes() == raw


def test_async_review_and_image_drafts(tmp_path, monkeypatch):
    from PySide6.QtCore import QCoreApplication, QSettings
    from test_vault_tasks import wait

    from habit_workspace.presentation.controllers import WorkspaceController

    QCoreApplication.instance() or QCoreApplication([])
    w = WorkspaceController(settings=QSettings(str(tmp_path / "prefs"), QSettings.IniFormat))
    assert w.createVault(str(tmp_path / "vault"), "Test")
    try:
        w.navigate("week", "2026-12-31")
        w.content.createReview()
        w.content.save(dict(title="Review", body="Unsaved", rating="6"))
        wait(lambda: not w.actions.busy)
        assert w.content.form["error"] and w.content.form["body"] == "Unsaved"
        w.content.save(dict(rating="4"))
        wait(lambda: not w.actions.busy)
        review = next(d for d in w.session.report.documents if d.document.kind == "review")
        assert review.document.metadata["hw"]["period"] == "week/2026-W53"
        w.navigate("day", "2026-12-31")
        assert not any(r["documentKind"] == "review" for r in w.state["documents"])
        w.navigate("notes")
        w.setQuery("Unsaved")
        assert w.state["documents"][0]["id"] == str(review.document.id)
        w.content.edit(str(review.document.id))
        source = png(tmp_path / "test.png")
        w.content.importImage(str(source), "Alt [text]", {"body": "Draft before import"})
        wait(lambda: not w.actions.busy)
        assert "Draft before import" in w.content.form["body"]
        assert "![Alt \\[text\\]](Assets/" in w.content.form["body"]
        w.content.save({})
        wait(lambda: not w.actions.busy)
        assert not w.content.form
        w.content.edit(str(review.document.id))
        review.path.write_bytes(review.path.read_bytes() + b"external")
        w.content.save(dict(body="Keep conflict draft"))
        wait(lambda: not w.actions.busy)
        assert w.content.form["error"] and w.content.form["body"] == "Keep conflict draft"
        w.content.importImage("https://example.com/a.png", "Alt", {})
        assert w.content.form["error"] and "Keep conflict draft" == w.content.form["body"]
    finally:
        w.close()


def test_image_cache_reuses_decoder_and_invalidates(tmp_path, monkeypatch):
    from habit_workspace.presentation import layout_assets

    root = tmp_path / "vault"
    root.mkdir()
    path = png(root / "test.png")
    real = layout_assets._decode
    calls = []

    def count(*args):
        calls.append(True)
        return real(*args)

    monkeypatch.setattr(layout_assets, "_decode", count)
    layout_assets.image_source(root, "test.png")
    layout_assets.image_source(root, "test.png")
    assert len(calls) == 1
    path.write_bytes(b"corrupt")
    with pytest.raises(DocumentError):
        layout_assets.image_source(root, "test.png")
    assert len(calls) == 2
