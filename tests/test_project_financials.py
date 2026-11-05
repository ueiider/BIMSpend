import sqlite3
import pytest
from bimspend.db import Database
from bimspend.dashboard import project_summary
from bimspend.models import Project, TimeEntry, TimeEntryState


def test_budget_persists_and_migrates_old_projects(tmp_path):
    path = str(tmp_path / "legacy.db")
    con = sqlite3.connect(path)
    con.execute("""CREATE TABLE projects (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, client TEXT NOT NULL,
        standard_rate REAL NOT NULL, loaded_cost_rate REAL NOT NULL,
        is_billable INTEGER NOT NULL, is_archived INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL)""")
    con.commit()
    con.close()
    db = Database(path)
    project = Project("p", "Project", "Client", 150, 80, budget_aud=1000)
    db.upsert_project(project)
    with pytest.raises(ValueError):
        db.upsert_project(Project("bad", "Bad", "Client", 100, 80,
                                  budget_aud=-1))
    db.close()
    db = Database(path)
    assert db.get_project("p").budget_aud == 1000
    db.close()


def test_budget_actual_uses_approved_cost_and_includes_billed():
    project = Project("p", "Project", "Client", 200, 90, budget_aud=150)
    entry = TimeEntry("e", "a", "p", "designer_01", 120,
                      state=TimeEntryState.BILLED, standard_rate=200,
                      loaded_cost_rate=90, billed_minutes=90)
    summary = project_summary(project, 120, 120, [entry])
    assert summary["budget_aud"] == 150
    assert summary["labor_cost_aud"] == 180
    assert summary["budget_remaining_aud"] == -30
    assert summary["budget_used_percent"] == 120
    assert summary["approved_hours"] == 2
    assert summary["billed_hours"] == 1.5


def test_unset_budget_is_distinct_from_zero():
    project = Project("p", "Project", "Client", 200, 90)
    summary = project_summary(project, 0, 0, [])
    assert summary["budget_aud"] is None
    assert summary["budget_used_percent"] is None
