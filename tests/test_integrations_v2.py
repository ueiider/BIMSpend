import pytest

from bimspend.integrations import (ActivityWatchLocalClient, AttributionRules,
                                    MiruMockExport, ingest_synthetic_batch, parse_activitywatch, parse_revit, suggest)
from bimspend.models import Project, TimeEntryState
from bimspend.db import Database


def test_disabled_network_and_loopback_validation():
    with pytest.raises(PermissionError):
        ActivityWatchLocalClient().buckets()
    for endpoint in ("http://example.com", "http://127.0.0.1.evil.com", "https://127.0.0.1:5600"):
        with pytest.raises(ValueError):
            ActivityWatchLocalClient(endpoint)


def test_activitywatch_timezone_and_idle_exclusion():
    window = parse_activitywatch("window-host", "currentwindow", [
        {"id": 1, "timestamp": "2026-01-01T10:00:00+10:00", "duration": 3600,
         "data": {"app": "Revit", "title": "private title"}}], "designer_01")[0]
    idle = parse_activitywatch("afk-host", "afkstatus", [
        {"id": 2, "timestamp": "2026-01-01T00:30:00Z", "duration": 600,
         "data": {"status": "afk"}}], "designer_01")[0]
    assert window.started_at == "2026-01-01T00:00:00+00:00"
    assert idle.is_afk and idle.window_title == ""
    project = Project("p1", "Project", "Client", 120, 60)
    segments = suggest([window, idle, window], [project], AttributionRules({}, {"Revit": "p1"}))
    assert sum(s.attributed_minutes for s in segments) == 50
    assert all(s.project_id == "p1" for s in segments)


def test_revit_overlap_priority_and_unknown_document():
    project = Project("p1", "Project", "Client", 120, 60)
    window = parse_activitywatch("w", "currentwindow", [
        {"id": 1, "timestamp": "2026-01-01T00:00:00Z", "duration": 3600,
         "data": {"app": "Revit", "title": "private"}}], "designer_01")
    revit = parse_revit([{"schema_version": 1, "event_id": "r1", "kind": "active",
                          "document_id": "model-01", "started_at": "2026-01-01T00:15:00Z",
                          "ended_at": "2026-01-01T00:45:00Z"}], "designer_01")
    segments = suggest(window + revit, [project], AttributionRules({"model-01": "p1"}, {}))
    assert sum(s.attributed_minutes for s in segments) == 60
    assert sum(s.attributed_minutes for s in segments if s.project_id == "p1") == 30
    assert sum(s.attributed_minutes for s in segments if s.project_id is None) == 30
    assert [(s.id, s.project_id) for s in segments] == [(s.id, s.project_id) for s in suggest(window + revit, [project], AttributionRules({"model-01": "p1"}, {}))]
    assert all(s.project_id is None for s in suggest(revit, [project], AttributionRules({}, {})))
    with pytest.raises(ValueError):
        parse_revit([{"schema_version": 2}], "designer_01")


def test_miru_mock_requires_explicit_approved_export():
    mock = MiruMockExport()
    with pytest.raises(PermissionError):
        mock.export("e", "p", 30, approved=True, explicitly_requested=False)
    assert mock.export("e", "p", 30, approved=True, explicitly_requested=True) == mock.export("e", "p", 30, approved=True, explicitly_requested=True)


def test_batch_flows_to_pending_cost_without_destroying_corrections(tmp_path):
    db = Database(str(tmp_path / "preview.db"))
    db.upsert_project(Project("p1", "Project", "Client", 120, 60, budget_aud=1000))
    rows = [{"id": 7, "timestamp": "2026-01-01T00:00:00Z", "duration": 1800,
             "data": {"app": "Revit", "title": "private title"}}]
    events = parse_activitywatch("test-bucket", "currentwindow", rows, "designer_01")
    rule = AttributionRules({}, {"Revit": "p1"})
    assert ingest_synthetic_batch(db, events, rule) == {"events": 1, "suggestions": 1, "pending_entries": 1}
    entry = db.list_time_entries()[0]
    assert entry.state == TimeEntryState.PENDING_REVIEW
    assert entry.loaded_cost_rate == 60 and entry.minutes == 30
    assert db.list_events()[0].window_title != "private title"
    assert ingest_synthetic_batch(db, events, rule) == {"events": 0, "suggestions": 0, "pending_entries": 0}
    assert len(db.list_time_entries()) == 1


@pytest.mark.gui
def test_gui_integrations_import_and_navigation(tmp_path):
    import tkinter as tk
    from bimspend.app.shell import BIMSpendApp
    root = tk.Tk()
    root.withdraw()
    app = BIMSpendApp(root=root, db_path=str(tmp_path / "gui-v2.db"))
    try:
        app.show_screen("integrations")
        screen = app.screens["integrations"]
        screen.load_events()
        screen.preview()
        assert "Synthetic preview" in screen.last_result
        screen.import_events()
        assert "pending entries" in screen.last_result
        event_count = len(app.db.list_events())
        screen.import_events()
        assert len(app.db.list_events()) == event_count
        app.show_screen("activity_timeline")
        app.show_screen("timesheet_review")
    finally:
        app.db.close()
        root.destroy()
