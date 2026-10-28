"""Qt adapter integration against real temporary canonical files."""

from datetime import date
from uuid import uuid4

import pytest
from PySide6.QtCore import QCoreApplication, QSettings, QUrl
from test_vault import note

from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.documents import Document
from habit_workspace.presentation.controllers import WorkspaceController


@pytest.fixture
def desktop(tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    settings = QSettings(str(tmp_path / "preferences.ini"), QSettings.Format.IniFormat)
    controller = WorkspaceController(settings=settings, today=date(2026, 10, 29))
    yield controller
    controller.close()
    app.processEvents()


def test_create_switch_failure_and_watcher_lifetime(desktop, tmp_path):
    assert desktop.createVault(str(tmp_path / "one"), "Primeiro")
    first_watcher = desktop.watcher
    assert desktop.state["vaultName"] == "Primeiro"
    assert not desktop.openVault(str(tmp_path / "missing"))
    assert desktop.state["vaultName"] == "Primeiro"
    assert desktop.createVault(str(tmp_path / "two"), "Segundo")
    assert not first_watcher.periodic.isActive()
    assert not first_watcher.paths
    assert desktop.state["vaultName"] == "Segundo"
    assert len(desktop.state["recentVaults"]) == 2


def test_virtual_navigation_uses_metadata_and_never_materializes_pages(desktop, tmp_path):
    session = VaultSession.create(tmp_path / "vault", "Teste")
    document = Document.from_metadata(
        {
            "hw": {
                "schema_version": 4,
                "kind": "week_page",
                "id": str(uuid4()),
                "period": "week/2026-W44",
                "title": "Semana pessoal",
            }
        },
        "Notas da semana",
    )
    loaded = session.create_document("Unrelated/nested/page.md", document)
    desktop.openVault(str(session.root))
    before = {p.relative_to(session.root): p.read_bytes() for p in session.root.rglob("*.md")}
    desktop.navigate("week")
    assert desktop.state["period"] == "week/2026-W44"
    assert desktop.state["documents"][0]["id"] == str(document.id)
    desktop.selectDocument(str(document.id))
    moved = loaded.path.with_name("moved.md")
    loaded.path.rename(moved)
    desktop.reindex()
    assert desktop.state["selected"]["path"].endswith("moved.md")
    desktop.navigate("month")
    assert desktop.state["documents"] == []
    assert len(list(session.root.rglob("*.md"))) == len(before)
    assert moved.read_bytes() == next(iter(before.values()))


def test_import_preview_cancel_conflict_missing_reference_and_reindex(desktop, tmp_path):
    source = VaultSession.create(tmp_path / "source", "Origem")
    missing = str(uuid4())
    doc = note(body="Texto preservado", origin_page_id=missing)
    loaded = source.create_document("Notes/a.md", doc)
    desktop.createVault(str(tmp_path / "target"), "Destino")
    url = QUrl.fromLocalFile(str(loaded.path)).toString()
    assert desktop.previewImport(url, False)
    assert desktop.state["importPreview"]["missingCount"] == 1
    assert not desktop.session.report.documents
    desktop.cancelImport()
    assert not desktop.session.report.documents
    desktop.previewImport(url, False)
    assert desktop.confirmImport()
    assert len(desktop.state["issues"]) == 1
    desktop.selectDocument(str(doc.id))
    assert desktop.state["selected"]["excerpt"] == "Texto preservado"
    desktop.session.index.path.unlink()
    desktop.reindex()
    assert desktop.session.index.path.exists()
    raw = desktop.session.report.documents[0].path.read_bytes()
    loaded.path.write_bytes(loaded.path.read_bytes() + b"\nChanged")
    desktop.previewImport(url, False)
    assert desktop.state["importPreview"]["conflict"]
    assert not desktop.confirmImport()
    assert desktop.session.report.documents[0].path.read_bytes() == raw


def test_preview_changed_source_requires_new_review_and_plain_note_opt_in(desktop, tmp_path):
    desktop.createVault(str(tmp_path / "vault"), "Teste")
    source = tmp_path / "plain.md"
    source.write_text("# Minha nota\n\nTexto", encoding="utf-8")
    assert not desktop.previewImport(str(source), False)
    assert desktop.previewImport(str(source), True)
    source.write_text("Mudou", encoding="utf-8")
    assert not desktop.confirmImport()
    assert not desktop.session.report.documents
    desktop.previewImport(str(source), True)
    assert desktop.confirmImport()


def test_duplicate_ids_visible_without_selecting_winner(desktop, tmp_path):
    desktop.createVault(str(tmp_path / "vault"), "Teste")
    loaded = desktop.session.create_document("Notes/a.md", note())
    (loaded.path.parent / "b.md").write_bytes(loaded.path.read_bytes())
    desktop.reindex()
    assert len(desktop.state["documents"]) == 2
    assert desktop.state["issues"]
    desktop.selectDocument(str(loaded.document.id))
    assert desktop.state["selected"] == {}
    assert desktop.state["noticeError"]


def test_preferences_persist_without_document_changes(desktop):
    desktop.setTheme("light")
    desktop.setReducedMotion(True)
    desktop.setSidebarCollapsed(True)
    other = WorkspaceController(settings=desktop.settings)
    try:
        assert other.state["theme"] == "light"
        assert other.state["reducedMotion"]
        assert other.state["sidebarCollapsed"]
    finally:
        other.close()


def test_imported_daily_snapshot_is_readable_without_recreating_habit(desktop, tmp_path):
    desktop.createVault(str(tmp_path / "vault"), "Teste")
    doc = Document.from_metadata(
        {
            "hw": {
                "schema_version": 4,
                "kind": "day_page",
                "id": str(uuid4()),
                "date": "2026-10-29",
                "checkins": [
                    {
                        "id": str(uuid4()),
                        "habit_id": str(uuid4()),
                        "date": "2026-10-29",
                        "state": "skipped",
                        "label_snapshot": "Leitura",
                        "recorded_at": "2026-10-29T12:00:00-03:00",
                    }
                ],
            }
        },
        "Nota preservada",
    )
    desktop.session.create_document("Arbitrary/page.md", doc)
    desktop.reindex()
    desktop.selectDocument(str(doc.id))
    assert desktop.state["selected"]["records"] == [{"label": "Leitura", "value": "Dispensado"}]
    assert desktop.state["selected"]["missing"] == 1
    assert len(desktop.session.report.documents) == 1


def test_reindex_failure_is_not_reported_as_success(desktop, tmp_path, monkeypatch):
    desktop.createVault(str(tmp_path / "vault"), "Teste")

    def fail():
        raise OSError("injected read failure")

    monkeypatch.setattr(desktop.session, "scan", fail)
    desktop.reindex()
    assert desktop.state["noticeError"]
    assert "injected read failure" in desktop.state["notice"]


def test_preview_discloses_habit_reference_pointing_to_a_note(desktop, tmp_path):
    desktop.createVault(str(tmp_path / "vault"), "Teste")
    target = note()
    desktop.session.create_document("Notes/target.md", target)
    source = VaultSession.create(tmp_path / "source", "Origem")
    document = Document.from_metadata(
        {
            "hw": {
                "schema_version": 4,
                "kind": "day_page",
                "id": str(uuid4()),
                "date": "2026-10-29",
                "checkins": [
                    {
                        "id": str(uuid4()),
                        "habit_id": str(target.id),
                        "date": "2026-10-29",
                        "state": "done",
                        "label_snapshot": "Hábito importado",
                        "recorded_at": "2026-10-29T12:00:00-03:00",
                    }
                ],
            }
        },
        "Texto preservado",
    )
    loaded = source.create_document("Pages/page.md", document)
    assert desktop.previewImport(str(loaded.path), False)
    assert desktop.state["importPreview"]["missingCount"] == 1
    assert desktop.confirmImport()
    assert desktop.state["selected"]["missing"] == 1


def test_habit_visible_across_virtual_views_without_io_or_duplication(
    desktop, tmp_path, monkeypatch
):
    from habit_workspace.application.habits import HabitService
    from habit_workspace.domain.temporal import PeriodRef, Recurrence, TemporalScope

    desktop.createVault(str(tmp_path / "vault"), "Temporal")
    service = HabitService(desktop.session)
    loaded = service.create(
        name="Read",
        period=PeriodRef.parse("day/2026-10-27"),
        scope=TemporalScope.from_inclusive(date(2026, 10, 27), date(2026, 12, 31)),
        recurrence=Recurrence.weekdays((1, 2, 3, 4, 5)),
    )
    raw = loaded.loaded.path.read_bytes()

    def forbidden(*args, **kwargs):
        raise AssertionError("Navigation must not scan or generate occurrences")

    monkeypatch.setattr(desktop.session, "scan", forbidden)
    monkeypatch.setattr(Recurrence, "occurrences", forbidden)
    for view in ("year", "month", "week", "day"):
        desktop.navigate(view, "2026-10-29")
        assert [row["id"] for row in desktop.state["documents"]] == [str(loaded.habit.id)]
    desktop.navigate("month", "2027-01-01")
    assert desktop.state["documents"] == []
    assert loaded.loaded.path.read_bytes() == raw
    assert len(desktop.session.report.documents) == 1
