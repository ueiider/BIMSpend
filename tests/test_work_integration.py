"""Independent integration regressions against synthetic fixtures only."""
import json
import sqlite3
import tkinter as tk
from pathlib import Path

import pytest

from bimspend.correlation import correlate_events
from bimspend.db import Database
from bimspend.models import ActivityEvent, Project, TimeEntryState
from bimspend.review import approve_entry, bill_entry, reject_entry, submit_entry
from bimspend.app.shell import BIMSpendApp

FIXTURES = Path(__file__).resolve().parents[1] / "data" / "synthetic"


def test_archive_persists_without_changing_billability_or_name(tmp_path):
    path = tmp_path / "archive.db"
    db = Database(str(path))
    project = Project("new-id", "Name", "Client", 150, 80, False)
    db.upsert_project(project)
    project.is_archived = True
    db.upsert_project(project)
    db.close()
    db = Database(str(path))
    saved = db.get_project("new-id")
    assert saved.is_archived is True
    assert saved.is_billable is False
    assert saved.name == "Name"
    db.close()


def test_titles_and_untrusted_payload_are_not_persisted(tmp_path):
    path = tmp_path / "private.db"
    db = Database(str(path))
    secret = "private-document-name"
    event = ActivityEvent(
        id="evt-private", source="activitywatch", external_id="opaque-1",
        user_id="synthetic", app_name="Revit", window_title=secret,
        started_at="2026-01-01T01:00:00Z", ended_at="2026-01-01T01:10:00Z",
        duration_minutes=10, raw_payload={"document": secret},
    )
    assert db.ingest_event(event) is True
    assert db.ingest_event(event) is False
    assert secret not in path.read_bytes().decode("utf-8", errors="ignore")
    saved = db.list_events()[0]
    assert saved.raw_payload is None
    assert saved.window_title.startswith("[HASH:")
    db.close()


def test_designer_submit_manager_approval_and_explicit_billing(tmp_path):
    db = Database(str(tmp_path / "flow.db"))
    projects = [Project.from_dict(p) for p in json.loads((FIXTURES / "projects.json").read_text())]
    events = [ActivityEvent.from_dict(e) for e in json.loads((FIXTURES / "events.json").read_text())]
    for project in projects:
        db.upsert_project(project)
    for event in events:
        db.ingest_event(event)
    suggestions = correlate_events(events, projects)
    assert any(s.project_id is None for s in suggestions)
    from bimspend.review import suggest_entry
    matched = next(s for s in suggestions if s.project_id)
    db.upsert_attributed_time(matched)
    source = next(e for e in events if e.id == matched.activity_event_id)
    entry = suggest_entry(matched, db.get_project(matched.project_id), source.user_id)
    db.upsert_time_entry(entry)
    submit_entry(entry, source.user_id)
    assert entry.state == TimeEntryState.SUBMITTED and entry.billed_minutes == 0
    with pytest.raises(ValueError):
        bill_entry(entry, 30, "manager_demo")
    approve_entry(entry, "manager_demo")
    assert entry.state == TimeEntryState.APPROVED and entry.billed_minutes == 0
    db.upsert_time_entry(entry)
    bill_entry(entry, min(30, entry.minutes), "billing_demo")
    db.upsert_time_entry(entry)
    db.close()
    db = Database(str(tmp_path / "flow.db"))
    assert db.get_time_entry(entry.id).state == TimeEntryState.BILLED
    assert len(db.list_events()) == len(events) - 1  # fixture has duplicate source/external ID
    db.close()


def test_desktop_initialization_navigation_seed_and_restart(tmp_path):
    path = str(tmp_path / "desktop.db")
    root = tk.Tk()
    root.withdraw()
    app = BIMSpendApp(root=root, db_path=path)
    try:
        for screen in ("overview", "projects", "project_detail", "activity_timeline", "timesheet_review"):
            app.show_screen(screen)
        root.update_idletasks()
        events = app.db.list_events()
        entries = app.db.list_time_entries()
        assert events and entries
        assert all(e.state == TimeEntryState.PENDING_REVIEW for e in entries)
        assert any(a.project_id is None for a in app.db.list_attributed_time())
        counts = (len(events), len(entries))
    finally:
        app.destroy()
    root = tk.Tk()
    root.withdraw()
    app = BIMSpendApp(root=root, db_path=path)
    try:
        assert (len(app.db.list_events()), len(app.db.list_time_entries())) == counts
    finally:
        app.destroy()
