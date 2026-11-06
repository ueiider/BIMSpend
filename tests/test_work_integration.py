"""Independent integration regressions against synthetic fixtures only."""
import json
import sqlite3
import tkinter as tk
from pathlib import Path

import pytest

from bimspend.correlation import correlate_events
from bimspend.db import Database
from bimspend.identity import Actor, Role, current_auth
from bimspend.models import ActivityEvent, Project, TimeEntryState
from bimspend.review import approve_entry, bill_entry, reject_entry, submit_entry
from bimspend.app.shell import BIMSpendApp

FIXTURES = Path(__file__).resolve().parents[1] / "data" / "synthetic"


def _set_actor(user_id: str, role: Role, company_id: str | None = None):
    current_auth.clear()
    current_auth.set_actor(Actor(id=user_id, role=role, company_id=company_id or "c1"))


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
    # Designer submits own entry
    _set_actor(source.user_id, Role.DESIGNER)
    submit_entry(entry)
    assert entry.state == TimeEntryState.SUBMITTED and entry.billed_minutes == 0
    # Manager approves
    _set_actor("manager_demo", Role.MANAGER)
    with pytest.raises(ValueError):
        bill_entry(entry, 30)
    approve_entry(entry)
    assert entry.state == TimeEntryState.APPROVED and entry.billed_minutes == 0
    db.upsert_time_entry(entry)
    # Manager bills
    bill_entry(entry, min(30, entry.minutes))
    db.upsert_time_entry(entry)
    db.close()
    db = Database(str(tmp_path / "flow.db"))
    assert db.get_time_entry(entry.id).state == TimeEntryState.BILLED
    assert len(db.list_events()) == len(events) - 1  # fixture has duplicate source/external ID
    db.close()


@pytest.mark.gui
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


@pytest.mark.gui
def test_desktop_actions_project_attribution_and_review(tmp_path, monkeypatch):
    from tkinter import messagebox, simpledialog
    monkeypatch.setattr(messagebox, "showinfo", lambda *args: None)
    monkeypatch.setattr(messagebox, "showerror", lambda *args: (_ for _ in ()).throw(AssertionError(args)))
    monkeypatch.setattr(messagebox, "askyesno", lambda *args: True)
    root = tk.Tk()
    root.withdraw()
    app = BIMSpendApp(root=root, db_path=str(tmp_path / "actions.db"))
    try:
        app.show_screen("projects")
        screen = app.screens["projects"]
        original_count = len(app.db.list_projects())
        from bimspend.app.screens.projects import ProjectDialog

        def make_project(dialog):
            dialog.name_var.set("Integration Test Project")
            dialog.client_var.set("Synthetic Client")
            dialog.rate_var.set("180")
            dialog.cost_var.set("95")
            dialog._save()

        root.after(20, lambda: make_project(next(
            w for w in screen.winfo_children() if isinstance(w, ProjectDialog)
        )))
        screen._new_project()
        added = next(p for p in app.db.list_projects() if p.name == "Integration Test Project")
        assert len(app.db.list_projects()) == original_count + 1
        assert added.id.startswith("proj_")

        def edit_project(dialog):
            dialog.name_var.set("Renamed Integration Project")
            dialog._save()

        root.after(20, lambda: edit_project(next(
            w for w in screen.winfo_children() if isinstance(w, ProjectDialog)
        )))
        screen._edit_project(added.id)
        assert app.db.get_project(added.id).name == "Renamed Integration Project"
        screen._archive_project(added.id)
        assert app.db.get_project(added.id).is_archived
        assert app.db.get_project(added.id).name == "Renamed Integration Project"
        assert all(app.db.get_project(screen.tree.item(i, "tags")[0]).id != added.id for i in screen.tree.get_children())

        app.show_screen("activity_timeline")
        timeline = app.screens["activity_timeline"]
        unmatched = next(a for a in app.db.list_attributed_time() if a.project_id is None)
        item = next(i for i in timeline.tree.get_children() if timeline.tree.item(i, "text") == unmatched.activity_event_id)
        timeline.tree.selection_set(item)
        active = next(p for p in app.db.list_projects() if not p.is_archived)
        monkeypatch.setattr(simpledialog, "askstring", lambda *args: active.id)
        timeline._assign_selected()
        assert next(a for a in app.db.list_attributed_time() if a.id == unmatched.id).project_id == active.id
        entry_id = "entry_" + unmatched.id
        assert app.db.get_time_entry(entry_id).state == TimeEntryState.PENDING_REVIEW

        app.show_screen("timesheet_review")
        timesheet = app.screens["timesheet_review"]
        pending_item = next(i for i in timesheet.pending_tree.get_children() if timesheet.pending_tree.item(i, "text") == entry_id)
        timesheet.pending_tree.selection_set(pending_item)
        monkeypatch.setattr(simpledialog, "askfloat", lambda *args, **kwargs: 42)
        _set_actor("designer_01", Role.DESIGNER)
        timesheet._edit_selected()
        assert app.db.get_time_entry(entry_id).minutes == 42
        pending_item = next(i for i in timesheet.pending_tree.get_children()
                            if timesheet.pending_tree.item(i, "text") == entry_id)
        timesheet.pending_tree.selection_set(pending_item)
        timesheet._submit_selected()
        assert app.db.get_time_entry(entry_id).state == TimeEntryState.SUBMITTED
        submitted_item = next(i for i in timesheet.submitted_tree.get_children() if timesheet.submitted_tree.item(i, "text") == entry_id)
        timesheet.submitted_tree.selection_set(submitted_item)
        _set_actor("manager_demo", Role.MANAGER)
        timesheet._approve_selected()
        approved = app.db.get_time_entry(entry_id)
        assert approved.state == TimeEntryState.APPROVED
        assert approved.billed_minutes == 0
        assert approved.reviewed_by == "manager_demo"
        approved_item = next(i for i in timesheet.approved_tree.get_children()
                             if timesheet.approved_tree.item(i, "text") == entry_id)
        timesheet.approved_tree.selection_set(approved_item)
        monkeypatch.setattr(simpledialog, "askfloat", lambda *args, **kwargs: 30)
        timesheet._bill_selected()
        billed = app.db.get_time_entry(entry_id)
        assert billed.state == TimeEntryState.BILLED
        assert billed.billed_minutes == 30
        history = app.db.list_entry_history(entry_id)
        assert [row["action"] for row in history] == [
            "created", "edited", "submitted", "approved", "billed"]
        assert history[-1]["actor_id"] == "manager_demo"
    finally:
        app.destroy()


def test_runner_can_repeat_without_resetting_states_or_project_edits(tmp_path, monkeypatch, capsys):
    from bimspend.runner import run
    current_auth.clear()
    monkeypatch.chdir(tmp_path)
    run()
    db = Database("bimspend_demo.db")
    before_events = len(db.list_events())
    before_entries = [(e.id, e.state, e.billed_minutes) for e in db.list_time_entries()]
    project = db.list_projects()[0]
    project.name = "Locally edited synthetic project"
    db.upsert_project(project)
    db.close()
    run()
    assert "Locally edited synthetic project" in capsys.readouterr().out
    db = Database("bimspend_demo.db")
    assert len(db.list_events()) == before_events
    assert [(e.id, e.state, e.billed_minutes) for e in db.list_time_entries()] == before_entries
    assert db.get_project(project.id).name == "Locally edited synthetic project"
    db.close()


def test_billed_time_retains_approved_cost_and_hours():
    from bimspend.dashboard import project_summary
    from bimspend.models import TimeEntry
    project = Project("p", "Synthetic project", "Client", 150, 90)
    entry = TimeEntry("e", "a", "p", "designer", 120,
                      state=TimeEntryState.BILLED,
                      standard_rate=150, loaded_cost_rate=90, billed_minutes=60)
    summary = project_summary(project, 120, 120, [entry])
    assert entry.is_approved
    assert summary["approved_hours"] == 2
    assert summary["billed_hours"] == 1
    assert summary["labor_cost_aud"] == 180
    assert summary["standard_value_aud"] == 300


def test_domain_edit_ownership_and_audit_survives_restart(tmp_path):
    from bimspend.review import edit_entry
    from bimspend.models import TimeEntry
    from bimspend.identity import current_auth
    current_auth.clear()
    path = str(tmp_path / "audit.db")
    db = Database(path)
    project = Project("p", "Synthetic project", "Client", 150, 80)
    db.upsert_project(project)
    event = ActivityEvent("e", "synthetic", "source-1", "designer_01", "Revit",
                          "Synthetic title", "2026-01-01T00:00:00Z",
                          "2026-01-01T01:00:00Z", 60)
    db.ingest_event(event)
    from bimspend.models import AttributedTime
    db.upsert_attributed_time(AttributedTime("a", "e", "p", 60, 1.0, "manual"))
    entry = TimeEntry("t", "a", "p", "designer_01", 60)
    db.upsert_time_entry(entry)
    # Non-owner designer cannot edit (authenticated mode)
    _set_actor("designer_02", Role.DESIGNER, "c1")
    with pytest.raises(PermissionError):
        edit_entry(entry, 30)
    # Invalid minutes raises ValueError (with authenticated actor)
    _set_actor("designer_01", Role.DESIGNER, "c1")
    with pytest.raises(ValueError):
        edit_entry(entry, 0)
    # Owner designer can edit
    edit_entry(entry, 30)
    db.upsert_time_entry(entry, actor_id="designer_01")
    submit_entry(entry)
    db.upsert_time_entry(entry, actor_id="designer_01")
    # Cannot edit after submission (not pending)
    with pytest.raises(ValueError):
        edit_entry(entry, 20)
    db.close()
    db = Database(path)
    assert db.get_time_entry("t").minutes == 30
    assert [row["action"] for row in db.list_entry_history("t")] == [
        "created", "edited", "submitted"]
    assert db.list_entry_history("t")[1]["actor_id"] == "designer_01"
    db.close()