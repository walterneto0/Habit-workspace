"""First-use canonical capture and context-preserving details without a layout."""

from test_tracking import desktop  # noqa: F401


def test_first_habit_without_studio_and_contextual_details(desktop):  # noqa: F811
    desktop.setCaptureDate("2026-10-28")
    desktop.newHabit()
    assert desktop.saveHabit({"name": "Ler", "bind": False})
    row = desktop.state["habits"]["rows"][0]
    assert row["cell"]["state"] == "unrecorded" and row["cell"]["editable"]
    original = desktop.state["period"], desktop.state["tracking"]["date"]
    desktop.showHabit(row["id"])
    assert desktop.state["selected"]["habit"]["id"] == row["id"]
    desktop.editHabit(row["id"])
    assert desktop.saveHabit({"name": "Ler mais", "tags": "estudos"})
    desktop.returnToTracking()
    assert (desktop.state["period"], desktop.state["tracking"]["date"]) == original
    assert desktop.state["habits"]["rows"][0]["id"] == row["id"]
    assert desktop.setCheckin(row["id"], "done", "null")
    assert desktop.state["habits"]["rows"][0]["cell"]["recorded"] == "done"
