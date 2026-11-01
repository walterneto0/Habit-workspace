from datetime import date

import pytest
from PySide6.QtCore import QCoreApplication, QSettings

from habit_workspace.application.content import ContentService
from habit_workspace.application.vault import VaultSession
from habit_workspace.presentation.controllers import WorkspaceController
from habit_workspace.presentation.period_selection import PeriodChoices


@pytest.mark.parametrize(
    "value",
    ["year/2026", "month/2026-10", "week/2026-W53", "week/2020-W53", "day/2027-01-01"],
)
def test_selector_roundtrip(value):
    choices = PeriodChoices()
    parts = choices.describe(value)
    options = choices.options(parts["scale"], parts["year"], parts["month"])
    assert next(o["value"] for o in options if o["part"] == parts["part"]) == value
    assert choices.label(value) and "/" not in choices.label(value)


def test_selector_iso_boundaries_and_invalid_dates():
    choices = PeriodChoices()
    weeks = choices.options("week", "2026", 1)
    assert len(weeks) == 53
    assert weeks[-1]["value"] == "week/2026-W53"
    assert "28/12/2026" in weeks[-1]["label"] and "03/01/2027" in weeks[-1]["label"]
    assert len(choices.options("week", "2027", 1)) == 52
    assert len(choices.options("day", "2028", 2)) == 29
    assert len(choices.options("day", "2027", 2)) == 28
    for scale, year, month in [("day", "2026", 13), ("week", "", 1), ("year", "bad", 1)]:
        assert choices.options(scale, year, month) == []
    assert choices.describe("") == {}


@pytest.mark.parametrize("home,cadence", [("day/2026-10-29", "week"), ("week/2026-W44", "month")])
def test_invalid_goal_selection_preserves_draft_before_dispatch(tmp_path, home, cadence):
    QCoreApplication.instance() or QCoreApplication([])
    w = WorkspaceController(
        settings=QSettings(str(tmp_path / "prefs"), QSettings.IniFormat), today=date(2026, 10, 29)
    )
    try:
        w.createVault(str(tmp_path / "vault"), "Test")
        w.navigate("year", "2026-10-29")
        w.planning.create("goal")
        assert w.planning.form["cadence"] == "home_only"
        w.planning.save(dict(title="Draft", body="Keep", home=home, cadence=cadence))
        assert not w.actions.busy
        assert w.planning.form["cadence"] == cadence
        assert w.planning.form["body"] == "Keep" and w.planning.form["error"]
        assert not w.session.report.documents
    finally:
        w.close()


@pytest.mark.parametrize(
    "kind,period", [("note", ""), ("note", "month/2026-10"), ("review", "week/2020-W53")]
)
def test_existing_period_association_is_not_replaced_by_current_page(tmp_path, kind, period):
    QCoreApplication.instance() or QCoreApplication([])
    w = WorkspaceController(
        settings=QSettings(str(tmp_path / "prefs"), QSettings.IniFormat), today=date(2026, 10, 29)
    )
    try:
        s = VaultSession.create(tmp_path / "vault", "Test")
        doc = ContentService(s).create("Existing", "Body", period, kind=kind)
        w._attach(s)
        w.navigate("day", "2026-10-29")
        w.content.edit(str(doc.document.id))
        assert w.content.form["period"] == period
    finally:
        w.close()
