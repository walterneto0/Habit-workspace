"""Phase 6 desktop tracking flow through the Qt adapter, using temporary vaults."""

import json
from datetime import date, datetime, timedelta, timezone

import pytest
from PySide6.QtCore import QCoreApplication, QSettings, QThreadPool

from habit_workspace.application.vault import VaultSession

TODAY = date(2026, 10, 29)
NOW = datetime(2026, 10, 29, 9, 0, tzinfo=timezone(timedelta(hours=-3)))


class FrozenDatetime(datetime):
    """Instants agree with the injected civil today; each reading advances one second."""

    ticks = 0

    @classmethod
    def now(cls, tz=None):
        cls.ticks += 1
        value = NOW + timedelta(seconds=cls.ticks)
        return value if tz is None else value.astimezone(tz)


class FrozenClock:
    """Injected controller clock: civil TODAY with FrozenDatetime instants."""

    def now(self):
        return FrozenDatetime.now().astimezone()

    def today(self):
        return TODAY


def controller(tmp_path):
    from habit_workspace.presentation.controllers import WorkspaceController

    QCoreApplication.instance() or QCoreApplication([])
    return WorkspaceController(
        settings=QSettings(str(tmp_path / "prefs"), QSettings.IniFormat), clock=FrozenClock()
    )


@pytest.fixture
def desktop(tmp_path):
    workspace = controller(tmp_path)
    workspace.createVault(str(tmp_path / "vault"), "Tracking")
    workspace.navigate("week", "2026-10-29")
    yield workspace
    QThreadPool.globalInstance().waitForDone()
    workspace.close()


def save_studio(workspace):
    studio = workspace.layoutStudio
    studio.prepare()
    studio.save()
    QThreadPool.globalInstance().waitForDone()
    QCoreApplication.instance().processEvents()
    assert not studio.draft, studio.message


def cells(workspace, kind=None):
    def walk(blocks):
        for block in blocks:
            yield from ((block, c) for c in block.get("capture", []))
            yield from walk(block.get("children", []))

    return [
        (block, cell)
        for block, cell in walk(workspace.state["composition"]["blocks"])
        if kind is None or cell["kind"] == kind
    ]


def build_tracking_layout(workspace, name="Estudar Python"):
    """GUI path: habit form with 'bind', plus a new numeric field in the Studio."""
    workspace.newHabit()
    form = workspace.state["habitForm"]
    assert form["open"] and form["scopeMode"] == "period"
    assert (form["start"], form["end"]) == ("2026-10-26", "2026-11-01")
    assert workspace.saveHabit(
        {
            "name": name,
            "tags": "Estudos, programação",
            "recurrence": "weekdays",
            "days": [1, 2, 3, 4, 5],
            "bind": True,
        }
    ), workspace.state["habitForm"]
    studio = workspace.layoutStudio
    assert studio.draft and studio.draft.view.blocks[-1].binding.kind == "habit"
    studio.addConfigured("integer_input", "", "Tempo de estudo", "estudos", {"unit": "minutes"})
    save_studio(workspace)


def test_gui_flow_checkin_and_numeric_observation_survive_restart(desktop, tmp_path):
    build_tracking_layout(desktop)
    assert desktop.state["tracking"]["date"] == "2026-10-29"
    ((block, habit),) = cells(desktop, "habit")
    assert habit["state"] == "pending" and habit["editable"]
    ((input_block, field),) = cells(desktop, "field")
    assert field["valueType"] == "integer" and field["unit"] == "minutes" and field["editable"]

    assert desktop.setCheckin(habit["id"], "done", habit["token"])
    assert desktop.state["tracking"]["feedback"]["error"] is False
    ((_, habit),) = cells(desktop, "habit")
    assert habit["state"] == "done"
    # Correction and idempotent repeat never duplicate.
    assert desktop.setCheckin(habit["id"], "skipped", habit["token"])
    ((_, habit),) = cells(desktop, "habit")
    assert desktop.setCheckin(habit["id"], "skipped", habit["token"])
    assert desktop.setCheckin(habit["id"], "done", habit["token"])

    assert not desktop.saveObservation(field["id"], input_block["id"], "quarenta", field["token"])
    assert desktop.state["tracking"]["feedback"]["error"] is True
    assert desktop.saveObservation(field["id"], input_block["id"], "40", field["token"])
    ((_, field),) = cells(desktop, "field")
    assert field["value"] == "40" and field["recorded"] is True

    day_pages = [d for d in desktop.session.report.documents if d.document.kind == "day_page"]
    assert len(day_pages) == 1
    hw = day_pages[0].document.metadata["hw"]
    assert [(r["habit_id"], r["state"]) for r in hw["checkins"]] == [(habit["id"], "done")]
    assert [(r["field_id"], r["value"]) for r in hw["observations"]] == [(field["id"], 40)]
    assert hw["observations"][0]["source_block_id"] == input_block["id"]

    # Navigate away and back, then reopen in a fresh controller (new "process" state).
    desktop.navigate("month", "2026-10-01")
    desktop.navigate("week", "2026-10-29")
    assert cells(desktop, "habit")[0][1]["state"] == "done"
    root = desktop.session.root
    desktop.close()
    again = controller(tmp_path / "second")
    assert again.openVault(str(root))
    again.navigate("week", "2026-10-29")
    assert cells(again, "habit")[0][1]["state"] == "done"
    assert cells(again, "field")[0][1]["value"] == "40"
    # Same canonical habit from a month and a day page; never a second document.
    for view in ("month", "day", "year"):
        again.navigate(view, "2026-10-29")
        assert [r["name"] for r in again.state["habits"]["rows"]] == ["Estudar Python"]
    assert sum(d.document.kind == "habit" for d in again.session.report.documents) == 1
    again.close()


def test_selected_date_states_and_validation(desktop):
    build_tracking_layout(desktop)
    desktop.setCaptureDate("2026-10-31")  # Saturday: not scheduled.
    ((_, habit),) = cells(desktop, "habit")
    assert habit["state"] == "not_scheduled" and not habit["editable"]
    assert not desktop.setCheckin(habit["id"], "done", habit["token"])
    desktop.setCaptureDate("2026-10-30")  # Friday, future.
    ((_, habit),) = cells(desktop, "habit")
    assert habit["state"] == "future" and not habit["editable"]
    ((_, field),) = cells(desktop, "field")
    assert not field["editable"]
    desktop.setCaptureDate("2026-10-27")  # Before the field's activation instant.
    ((_, habit),) = cells(desktop, "habit")
    assert habit["state"] == "unrecorded" and habit["editable"]
    ((_, field),) = cells(desktop, "field")
    assert not field["editable"] and "falha" in field["note"]
    desktop.setCaptureDate("2026-12-01")
    assert desktop.state["noticeError"] and desktop.state["tracking"]["date"] == "2026-10-27"
    desktop.moveCaptureDate(-1)
    assert desktop.state["tracking"]["date"] == "2026-10-26"
    desktop.moveCaptureDate(-1)  # Clamped to the period.
    assert desktop.state["tracking"]["date"] == "2026-10-26"
    assert not any(d.document.kind == "day_page" for d in desktop.session.report.documents)


def test_habit_form_validation_override_and_search(desktop):
    desktop.newHabit()
    assert not desktop.saveHabit({"name": "  "})
    assert "nome" in desktop.state["habitForm"]["error"]
    assert not desktop.saveHabit(
        {"name": "Ler", "scopeMode": "custom", "start": "2026-10-40", "end": ""}
    )
    assert "AAAA-MM-DD" in desktop.state["habitForm"]["error"]
    assert not desktop.saveHabit(
        {"name": "Ler", "scopeMode": "custom", "start": "2026-10-27", "end": "2026-10-01"}
    )
    assert not desktop.saveHabit({"name": "Ler", "recurrence": "weekdays", "days": []})
    assert desktop.state["habitForm"]["name"] == "Ler"  # Input retained after an error.
    assert desktop.saveHabit(
        {
            "name": "Ler",
            "tags": "Leitura",
            "scopeMode": "custom",
            "start": "2026-10-27",
            "end": "",
            "recurrence": "daily",
            "days": [],
        }
    )
    assert not desktop.state["habitForm"]
    habit = next(d for d in desktop.session.report.documents if d.document.kind == "habit")
    hw = habit.document.metadata["hw"]
    assert hw["scope"] == {"start": "2026-10-27", "end_exclusive": None}
    assert hw["tags"] == ["leitura"] and "origin_page_id" not in hw  # No page materialized.
    desktop.navigate("habits")
    desktop.setQuery("leitura")
    assert [r["id"] for r in desktop.state["documents"]] == [hw["id"]]
    desktop.setQuery(hw["id"][:8])
    assert [r["id"] for r in desktop.state["documents"]] == [hw["id"]]


def test_edit_scope_after_checkins_requires_acknowledgement(desktop):
    build_tracking_layout(desktop)
    desktop.setCaptureDate("2026-10-27")
    ((_, habit),) = cells(desktop, "habit")
    assert desktop.setCheckin(habit["id"], "done", habit["token"])
    desktop.editHabit(habit["id"])
    form = desktop.state["habitForm"]
    assert form["mode"] == "edit" and form["days"] == [1, 2, 3, 4, 5]
    assert not desktop.saveHabit({"days": [4]})
    assert desktop.state["habitForm"]["impact"]
    assert desktop.saveHabit({"days": [4], "acknowledge": True})
    ((_, habit),) = cells(desktop, "habit")
    assert habit["state"] == "done" and not habit["editable"] and habit["note"]
    assert desktop.state["habits"]["rows"][0]["outside"] == 1


def test_stale_external_edit_is_reported_and_not_overwritten(desktop):
    build_tracking_layout(desktop)
    ((_, habit),) = cells(desktop, "habit")
    stale = habit["token"]
    assert desktop.setCheckin(habit["id"], "done", stale)
    page = next(d for d in desktop.session.report.documents if d.document.kind == "day_page")
    page.path.write_text(page.path.read_text().replace("state: done", "state: skipped"))
    assert not desktop.setCheckin(habit["id"], "missed", json.dumps("done"))
    assert "Conflito" in desktop.state["notice"]
    ((_, habit),) = cells(desktop, "habit")
    assert habit["state"] == "skipped"  # Refreshed from the file, not overwritten.


def test_visual_changes_and_block_removal_keep_values(desktop):
    build_tracking_layout(desktop)
    ((_, habit),) = cells(desktop, "habit")
    ((input_block, field),) = cells(desktop, "field")
    desktop.setCheckin(habit["id"], "done", habit["token"])
    desktop.saveObservation(field["id"], input_block["id"], "40", field["token"])
    page = next(d for d in desktop.session.report.documents if d.document.kind == "day_page")
    raw = page.path.read_bytes()
    studio = desktop.layoutStudio
    studio.open()
    studio.command("columns")
    studio.select(len(studio.draft.view.blocks) - 1)
    studio.command("up")
    save_studio(desktop)
    assert page.path.read_bytes() == raw
    assert cells(desktop, "field")[0][1]["value"] == "40"
    studio.open()
    for kind in ("integer_input", "checklist"):
        studio.select(next(i for i, b in enumerate(studio.draft.view.blocks) if b.type == kind))
        studio.command("remove")
    save_studio(desktop)
    assert page.path.read_bytes() == raw
    assert not cells(desktop)
    kinds = [d.document.kind for d in desktop.session.report.documents]
    assert kinds.count("habit") == 1 and kinds.count("metric_definition") == 1
    assert desktop.state["habits"]["rows"][0]["stateLabel"] == "Concluído"


def test_index_rebuild_restores_tracking_state(desktop):
    build_tracking_layout(desktop)
    ((_, habit),) = cells(desktop, "habit")
    desktop.setCheckin(habit["id"], "done", habit["token"])
    before = desktop.state["composition"]
    desktop.session.index.path.unlink()
    desktop.reindex()
    assert desktop.session.index.path.exists()
    assert desktop.state["composition"] == before
    assert VaultSession.open(desktop.session.root).report.documents


def test_capture_blocked_while_studio_draft_is_open(desktop):
    build_tracking_layout(desktop)
    ((_, habit),) = cells(desktop, "habit")
    desktop.layoutStudio.open()
    assert not desktop.setCheckin(habit["id"], "done", habit["token"])
    desktop.layoutStudio.discard()
    assert desktop.setCheckin(habit["id"], "done", habit["token"])
