import pytest
from bimspend.db import Database
from bimspend.estimating import estimate_from_history
from bimspend.models import Project, TimeEntry, TimeEntryState, ActivityEvent, AttributedTime


def test_estimate_uses_approved_other_projects_and_rate(tmp_path):
    db = Database(str(tmp_path / "estimate.db"))
    for project in (Project("target", "Target", "Client", 150, 80),
                    Project("p1", "Reference 1", "Client", 150, 80),
                    Project("p2", "Reference 2", "Client", 150, 80)):
        db.upsert_project(project)
    assert estimate_from_history(db, "target") is None
    for i, (project_id, minutes, state) in enumerate(
            (("p1", 120, TimeEntryState.BILLED),
             ("p2", 240, TimeEntryState.APPROVED),
             ("p2", 600, TimeEntryState.PENDING_REVIEW),
             ("target", 900, TimeEntryState.APPROVED))):
        db.ingest_event(ActivityEvent(f"ev{i}", "synthetic", f"ext{i}", "designer_01",
                                      "Revit", "Synthetic", "2026-01-01T00:00:00Z",
                                      "2026-01-01T01:00:00Z", minutes))
        db.upsert_attributed_time(AttributedTime(f"att{i}", f"ev{i}", project_id,
                                                 minutes, 1.0, "manual"))
        db.upsert_time_entry(TimeEntry(f"entry{i}", f"att{i}", project_id,
                                        "designer_01", minutes, state=state))
    estimate = estimate_from_history(db, "target")
    assert estimate.reference_projects == 2
    assert (estimate.low_hours, estimate.high_hours, estimate.median_hours) == (2, 4, 3)
    assert estimate.estimated_cost_aud == 240
    assert "incomplete" in estimate.assumptions
    db.close()


@pytest.mark.gui
def test_estimating_screen_opens_with_no_history(tmp_path):
    import tkinter as tk
    from bimspend.app.shell import BIMSpendApp
    root = tk.Tk()
    root.withdraw()
    app = BIMSpendApp(root=root, db_path=str(tmp_path / "ui.db"))
    try:
        app.show_screen("estimating")
        screen = app.screens["estimating"]
        screen._calculate()
        assert "No other projects" in screen.result.cget("text")
    finally:
        app.destroy()
