import pytest

from bimspend.integrations import (ActivityWatchLocalClient, AttributionRules,
                                    MiruMockExport, parse_activitywatch, parse_revit, suggest)
from bimspend.models import Project


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
