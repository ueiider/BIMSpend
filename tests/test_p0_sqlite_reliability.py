import sqlite3
import builtins
import pytest
import threading
import time

from bimspend.db import Database
from bimspend.models import Project, ActivityEvent, AttributedTime, TimeEntry, TimeEntryState, TeamMember


def test_wal_timeout_and_two_connections_preserve_writes(tmp_path):
    path = str(tmp_path / "preview.db")
    first = Database(path)
    second = Database(path)
    try:
        assert first.conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert first.conn.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
        first.upsert_project(Project("first", "First", "Synthetic", 100, 50))
        second.upsert_project(Project("second", "Second", "Synthetic", 100, 50))
        assert {p.id for p in first.list_projects()} == {"first", "second"}
    finally:
        first.close()
        second.close()


@pytest.mark.gui
def test_startup_without_external_adapter_modules(tmp_path, monkeypatch):
    import tkinter as tk
    from bimspend.app.shell import BIMSpendApp
    original_import = builtins.__import__

    def without_optional(name, *args, **kwargs):
        if name.startswith("bimspend.adapters.activitywatch") or name.startswith("bimspend.adapters.miru"):
            raise ImportError("External adapter unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_optional)
    root = tk.Tk()
    root.withdraw()
    app = BIMSpendApp(root=root, db_path=str(tmp_path / "preview.db"))
    try:
        assert app.db.list_projects()
        assert app.db.list_events()
    finally:
        app.db.close()
        root.destroy()


def test_version_tracking_preserves_legacy_project(tmp_path):
    path = str(tmp_path / "legacy.db")
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT NOT NULL, client TEXT NOT NULL, standard_rate REAL NOT NULL, loaded_cost_rate REAL NOT NULL, is_billable INTEGER NOT NULL, created_at TEXT NOT NULL)")
        conn.execute("INSERT INTO projects VALUES ('old','Legacy','Synthetic',90,45,1,'2026-01-01T00:00:00Z')")
    db = Database(path)
    try:
        assert db.get_project("old").name == "Legacy"
        assert db.conn.execute("SELECT version FROM schema_version").fetchall()[0][0] == 1
    finally:
        db.close()
    reopened = Database(path)
    try:
        assert reopened.conn.execute("SELECT count(*) FROM schema_version").fetchone()[0] == 4
        assert reopened.get_project("old").name == "Legacy"
    finally:
        reopened.close()


def test_nested_transaction_rolls_back_all_writes(tmp_path):
    db = Database(str(tmp_path / "atomic.db"))
    with pytest.raises(sqlite3.IntegrityError):
        with db.transaction():
            db.upsert_project(Project("first", "First", "Synthetic", 100, 50))
            db.upsert_project(Project("invalid", "Bad", None, 100, 50))
    assert db.list_projects() == []
    db.upsert_project(Project("after", "After", "Synthetic", 100, 50))
    assert [p.id for p in db.list_projects()] == ["after"]
    db.close()


def test_writer_waits_for_real_sqlite_lock_then_succeeds(tmp_path):
    path = str(tmp_path / "locked.db")
    first = Database(path)
    started = threading.Event()
    outcome = []

    def writer():
        started.set()
        second = Database(path)
        try:
            second.upsert_project(Project("second", "Second", "Synthetic", 100, 50))
            outcome.append("committed")
        finally:
            second.close()

    with first.transaction():
        first.upsert_project(Project("first", "First", "Synthetic", 100, 50))
        thread = threading.Thread(target=writer)
        thread.start()
        assert started.wait(2)
        time.sleep(0.15)
        assert not outcome
    thread.join(timeout=3)
    assert not thread.is_alive()
    assert outcome == ["committed"]
    assert {p.id for p in first.list_projects()} == {"first", "second"}
    first.close()


def test_archive_roundtrip_and_unique_source_attribution(tmp_path):
    path = str(tmp_path / "archive.db")
    db = Database(path)
    db.upsert_project(Project("p", "Project", "Synthetic", 100, 50))
    db.ingest_event(ActivityEvent("ev", "synthetic", "source-1", "designer_01", "Revit", "safe",
                                  "2026-01-01T01:00:00Z", "2026-01-01T01:15:00Z", 15))
    suggestion = AttributedTime("a", "ev", "p", 15, 1, "manual", is_archived=True)
    db.upsert_attributed_time(suggestion)
    entry = TimeEntry("e", "a", "p", "designer_01", 15, state=TimeEntryState.APPROVED, is_archived=True)
    db.upsert_time_entry(entry)
    with pytest.raises(sqlite3.IntegrityError):
        db.upsert_time_entry(TimeEntry("other", "a", "p", "designer_01", 15))
    assert db.conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == 4
    db.close()
    reopened = Database(path)
    assert reopened.list_attributed_time()[0].is_archived
    assert reopened.get_time_entry("e").is_archived
    assert reopened.get_time_entry("e").state == TimeEntryState.APPROVED
    assert reopened.conn.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0] == 4
    assert reopened.conn.execute("PRAGMA foreign_key_check").fetchall() == []
    reopened.close()


def test_duplicate_legacy_rows_block_migration_without_deletion(tmp_path):
    path = str(tmp_path / "legacy-duplicates.db")
    db = Database(path)
    db.upsert_project(Project("p", "Project", "Synthetic", 100, 50))
    db.ingest_event(ActivityEvent("ev", "synthetic", "ext-1", "designer_01", "Revit", "safe",
                                  "2026-01-01T01:00:00Z", "2026-01-01T01:15:00Z", 15))
    db.upsert_attributed_time(AttributedTime("a", "ev", "p", 15, 1, "manual"))
    db.upsert_time_entry(TimeEntry("e1", "a", "p", "designer_01", 15))
    db.conn.execute("DROP INDEX ux_time_entries_attribution")
    db.conn.execute("DELETE FROM schema_version WHERE version=2")
    db.conn.execute("INSERT INTO time_entries SELECT 'e2',attributed_time_id,project_id,user_id,minutes,state,standard_rate,loaded_cost_rate,billed_minutes,review_notes,reviewed_by,reviewed_at,submitted_by,submitted_at,created_at,is_archived FROM time_entries WHERE id='e1'")
    db.conn.commit()
    db.close()
    with pytest.raises(RuntimeError, match="manual reconciliation"):
        Database(path)
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT count(*) FROM time_entries").fetchone()[0] == 2
        assert conn.execute("SELECT max(version) FROM schema_version").fetchone()[0] == 4


def test_reject_newer_schema_without_mutating_file(tmp_path):
    path = str(tmp_path / "future.db")
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE schema_version (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
        conn.execute("INSERT INTO schema_version VALUES (99, '2099-01-01T00:00:00Z')")
    with pytest.raises(RuntimeError, match="newer"):
        Database(path)
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT count(*) FROM sqlite_master WHERE name='projects'").fetchone()[0] == 0


def test_user_identity_map_created_on_migration(tmp_path):
    """P0-004: Historical user_ids from time_entries are mapped to user_identity_map on migration."""
    path = str(tmp_path / "identity.db")
    db = Database(path)
    db.upsert_project(Project("p1", "Project", "Synthetic", 100, 50))
    db.ingest_event(ActivityEvent("ev1", "synthetic", "ext-1", "designer_01", "Revit", "safe",
                                  "2026-01-01T01:00:00Z", "2026-01-01T01:15:00Z", 15))
    db.upsert_attributed_time(AttributedTime("a1", "ev1", "p1", 15, 1, "manual"))
    db.upsert_time_entry(TimeEntry("e1", "a1", "p1", "designer_01", 15,
                                   state=TimeEntryState.APPROVED))
    maps = db.get_user_identity_maps()
    assert len(maps) == 1
    assert maps[0].historical_user_id == "designer_01"
    assert maps[0].mapped_member_id is None
    assert maps[0].mapping_status == "unresolved"
    assert db.resolve_user_id("designer_01") is None
    assert "designer_01" in db.list_unresolved_user_ids()
    db.close()


def test_map_user_id_to_team_member(tmp_path):
    """P0-004: Authorized mapping of historical user_id to team_member."""
    path = str(tmp_path / "identity_map.db")
    db = Database(path)
    db.upsert_project(Project("p1", "Project", "Synthetic", 100, 50))
    db.upsert_member(TeamMember("m1", "Alice", "designer", 95))
    db.ingest_event(ActivityEvent("ev1", "synthetic", "ext-1", "designer_01", "Revit", "safe",
                                  "2026-01-01T01:00:00Z", "2026-01-01T01:15:00Z", 15))
    db.upsert_attributed_time(AttributedTime("a1", "ev1", "p1", 15, 1, "manual"))
    db.upsert_time_entry(TimeEntry("e1", "a1", "p1", "designer_01", 15,
                                   state=TimeEntryState.APPROVED))
    db.map_user_id("designer_01", "m1", "admin_01", "manual reconciliation")
    assert db.resolve_user_id("designer_01") == "m1"
    assert "designer_01" not in db.list_unresolved_user_ids()
    maps = db.get_user_identity_maps()
    assert len(maps) == 1
    assert maps[0].mapping_status == "mapped"
    assert maps[0].mapped_member_id == "m1"
    assert maps[0].mapped_by == "admin_01"
    assert maps[0].reason == "manual reconciliation"
    db.close()


def test_unmap_user_id_returns_to_unresolved(tmp_path):
    """P0-004: Unmapping returns historical user_id to unresolved status."""
    path = str(tmp_path / "unmap.db")
    db = Database(path)
    db.upsert_project(Project("p1", "Project", "Synthetic", 100, 50))
    db.upsert_member(TeamMember("m1", "Alice", "designer", 95))
    db.ingest_event(ActivityEvent("ev1", "synthetic", "ext-1", "designer_01", "Revit", "safe",
                                  "2026-01-01T01:00:00Z", "2026-01-01T01:15:00Z", 15))
    db.upsert_attributed_time(AttributedTime("a1", "ev1", "p1", 15, 1, "manual"))
    db.upsert_time_entry(TimeEntry("e1", "a1", "p1", "designer_01", 15,
                                   state=TimeEntryState.APPROVED))
    db.map_user_id("designer_01", "m1", "admin_01", "manual reconciliation")
    assert db.resolve_user_id("designer_01") == "m1"
    db.unmap_user_id("designer_01", "admin_01", "error in mapping")
    assert db.resolve_user_id("designer_01") is None
    assert "designer_01" in db.list_unresolved_user_ids()
    maps = db.get_user_identity_maps()
    assert maps[0].mapping_status == "unresolved"
    assert maps[0].mapped_member_id is None
    db.close()


def test_map_nonexistent_member_raises(tmp_path):
    """P0-004: Mapping to a non-existent team member raises ValueError."""
    path = str(tmp_path / "map_nonexistent.db")
    db = Database(path)
    db.upsert_project(Project("p1", "Project", "Synthetic", 100, 50))
    db.ingest_event(ActivityEvent("ev1", "synthetic", "ext-1", "designer_01", "Revit", "safe",
                                  "2026-01-01T01:00:00Z", "2026-01-01T01:15:00Z", 15))
    db.upsert_attributed_time(AttributedTime("a1", "ev1", "p1", 15, 1, "manual"))
    db.upsert_time_entry(TimeEntry("e1", "a1", "p1", "designer_01", 15,
                                   state=TimeEntryState.APPROVED))
    with pytest.raises(ValueError, match="Unknown team member id"):
        db.map_user_id("designer_01", "nonexistent", "admin_01", "bad mapping")
    assert db.resolve_user_id("designer_01") is None
    assert "designer_01" in db.list_unresolved_user_ids()
    db.close()


def test_identity_map_repeatable_on_reopen(tmp_path):
    """P0-004: Identity map migration is repeatable on database reopen."""
    path = str(tmp_path / "repeatable.db")
    db = Database(path)
    db.upsert_project(Project("p1", "Project", "Synthetic", 100, 50))
    db.ingest_event(ActivityEvent("ev1", "synthetic", "ext-1", "designer_01", "Revit", "safe",
                                  "2026-01-01T01:00:00Z", "2026-01-01T01:15:00Z", 15))
    db.upsert_attributed_time(AttributedTime("a1", "ev1", "p1", 15, 1, "manual"))
    db.upsert_time_entry(TimeEntry("e1", "a1", "p1", "designer_01", 15,
                                   state=TimeEntryState.PENDING_REVIEW))
    db.close()
    db2 = Database(path)
    maps = db2.get_user_identity_maps()
    assert len(maps) == 1
    assert maps[0].historical_user_id == "designer_01"
    assert maps[0].mapping_status == "unresolved"
    assert db2.conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == 4
    db2.close()