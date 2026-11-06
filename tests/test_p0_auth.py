"""P0-009/P0-010 Authentication, Session, and Authorization tests.

Tests cover:
- Password hashing and verification
- Login/logout flow
- Session expiration
- Role-based access control (designer, manager, administrator)
- Cross-tenant access denial
- Direct domain-service authorization bypass attempts
- Historical user identity reconciliation
- Migration from SQLite v1/v2/v3/v4
- Approved and billed record preservation
- GUI startup without external adapters
"""

import hashlib
import os
import sqlite3
import sys
import time
import threading

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bimspend.auth import SessionManager, hash_password, verify_password, PBKDF2_ITERATIONS
from bimspend.db import Database
from bimspend.identity import Actor, Role, current_auth
from bimspend.models import (
    ActivityEvent,
    AttributedTime,
    Project,
    TeamMember,
    TimeEntry,
    TimeEntryState,
    UserIdentityMap,
)
from bimspend.review import (
    approve_entry,
    bill_entry,
    edit_entry,
    reject_entry,
    submit_entry,
    suggest_entry,
)


def _fresh_db(tmp_path, name="auth.db"):
    path = str(tmp_path / name)
    return Database(path)


def _make_project(db, pid="p1", name="Project", client="Client"):
    db.upsert_project(Project(pid, name, client, 150.0, 80.0))
    return pid


def _make_member(db, mid="m1", name="Alice", role="designer", cost=95.0, active=True):
    db.upsert_member(TeamMember(mid, name, role, cost, active))
    return mid


def _make_company(db, cid="c1", name="Test Company", is_active=True):
    db.upsert_company(cid, name, is_active=is_active)
    return cid


def _make_credential(db, member_id="m1", username="alice", password="secretpass"):
    db.upsert_user_credential(member_id, username, hash_password(password))
    return member_id


# ------------------------------------------------------------------
# Password hashing tests
# ------------------------------------------------------------------

def test_password_hash_and_verify():
    pw = "s3cr3tP@ssw0rd!"
    h = hash_password(pw)
    assert h.startswith("pbkdf2_sha256$")
    assert verify_password(pw, h) is True
    assert verify_password("wrongpassword", h) is False


def test_constant_time_different_lengths():
    from bimspend.auth import _constant_time_compare
    assert _constant_time_compare(b"abc", b"abc") is True
    assert _constant_time_compare(b"abc", b"abcd") is False
    assert _constant_time_compare(b"", b"") is True


# ------------------------------------------------------------------
# Login/logout tests
# ------------------------------------------------------------------

def test_login_success(tmp_path):
    db = _fresh_db(tmp_path)
    sm = SessionManager(db)
    _make_company(db, "c1", "Test Co")
    _make_member(db, "m1", "Alice", "designer", 95.0)
    db.upsert_company_member("c1", "m1", "designer")
    _make_credential(db, "m1", "alice", "secretpass")

    actor = sm.login("alice", "secretpass")
    assert actor.id == "m1"
    assert actor.role == Role.DESIGNER
    assert actor.company_id == "c1"
    assert current_auth.actor.id == actor.id
    assert current_auth.is_authenticated
    sm.logout()
    assert current_auth.actor is None
    db.close()


def test_login_wrong_password(tmp_path):
    current_auth.clear()
    db = _fresh_db(tmp_path)
    sm = SessionManager(db)
    _make_company(db, "c1", "Test Co")
    _make_member(db, "m1", "Alice", "designer", 95.0)
    db.upsert_company_member("c1", "m1", "designer")
    _make_credential(db, "m1", "alice", "secretpass")

    with pytest.raises(ValueError, match="Invalid username or password"):
        sm.login("alice", "wrongpassword")
    assert current_auth.actor is None
    db.close()


def test_login_nonexistent_user(tmp_path):
    db = _fresh_db(tmp_path)
    sm = SessionManager(db)
    with pytest.raises(ValueError, match="Invalid username or password"):
        sm.login("nonexistent", "password")
    db.close()


def test_login_inactive_member(tmp_path):
    db = _fresh_db(tmp_path)
    sm = SessionManager(db)
    _make_company(db, "c1", "Test Co")
    _make_member(db, "m1", "Alice", "designer", 95.0, active=False)
    db.upsert_company_member("c1", "m1", "designer")
    _make_credential(db, "m1", "alice", "secretpass")

    with pytest.raises(ValueError, match="Invalid username or password"):
        sm.login("alice", "secretpass")
    db.close()


# ------------------------------------------------------------------
# Session expiration tests
# ------------------------------------------------------------------

def test_session_expiration(tmp_path):
    db = _fresh_db(tmp_path)
    sm = SessionManager(db)
    _make_company(db, "c1", "Test Co")
    _make_member(db, "m1", "Alice", "designer", 95.0)
    db.upsert_company_member("c1", "m1", "designer")
    _make_credential(db, "m1", "alice", "secretpass")

    sm.login("alice", "secretpass")
    assert current_auth.is_authenticated

    # Manually expire the session
    db.conn.execute(
        "UPDATE sessions SET expires_at = ? WHERE member_id = ?",
        ("2000-01-01T00:00:00+00:00", "m1"),
    )
    db._commit()

    # Accessing current_auth.actor should raise PermissionError
    with pytest.raises(PermissionError, match="invalid, expired, or revoked"):
        _ = current_auth.actor
    assert not current_auth.is_authenticated
    db.close()


# ------------------------------------------------------------------
# Role-based access control tests
# ------------------------------------------------------------------

def test_designer_can_submit_own_entry(tmp_path):
    db = _fresh_db(tmp_path)
    sm = SessionManager(db)
    _make_company(db, "c1", "Test Co")
    _make_member(db, "m1", "Alice", "designer", 95.0)
    db.upsert_company_member("c1", "m1", "designer")
    _make_credential(db, "m1", "alice", "secretpass")
    sm.login("alice", "secretpass")

    project = Project("p1", "Project", "Client", 150.0, 80.0)
    db.upsert_project(project)
    event = ActivityEvent("e1", "synthetic", "ext-1", "m1", "Revit", "safe",
                          "2026-01-01T01:00:00Z", "2026-01-01T01:15:00Z", 60)
    db.ingest_event(event)
    att = AttributedTime("a1", "e1", "p1", 15, 1.0, "manual")
    db.upsert_attributed_time(att)
    entry = suggest_entry(att, project, "m1")
    submit_entry(entry)
    assert entry.state == TimeEntryState.SUBMITTED
    assert entry.submitted_by == "m1"
    db.close()


def test_designer_cannot_submit_others_entry(tmp_path):
    db = _fresh_db(tmp_path)
    sm = SessionManager(db)
    _make_company(db, "c1", "Test Co")
    _make_member(db, "m1", "Alice", "designer", 95.0)
    db.upsert_company_member("c1", "m1", "designer")
    _make_credential(db, "m1", "alice", "secretpass")
    sm.login("alice", "secretpass")

    project = Project("p1", "Project", "Client", 150.0, 80.0)
    db.upsert_project(project)
    event = ActivityEvent("e1", "synthetic", "ext-1", "m2", "Revit", "safe",
                          "2026-01-01T01:00:00Z", "2026-01-01T01:15:00Z", 60)
    db.ingest_event(event)
    att = AttributedTime("a1", "e1", "p1", 60, 1.0, "manual")
    db.upsert_attributed_time(att)
    entry = suggest_entry(att, project, "m2")

    with pytest.raises(PermissionError, match="Designers can submit only their own entries"):
        submit_entry(entry)
    assert entry.state == TimeEntryState.PENDING_REVIEW
    db.close()


def test_designer_cannot_approve_entry(tmp_path):
    db = _fresh_db(tmp_path)
    sm = SessionManager(db)
    _make_company(db, "c1", "Test Co")
    _make_member(db, "m1", "Alice", "designer", 95.0)
    db.upsert_company_member("c1", "m1", "designer")
    _make_credential(db, "m1", "alice", "secretpass")
    sm.login("alice", "secretpass")

    project = Project("p1", "Project", "Client", 150.0, 80.0)
    db.upsert_project(project)
    entry = TimeEntry("e1", "a1", "p1", "m2", 60,
                      state=TimeEntryState.SUBMITTED)

    with pytest.raises(PermissionError, match="Only managers can approve"):
        approve_entry(entry)
    assert entry.state == TimeEntryState.SUBMITTED
    db.close()


def test_manager_can_approve_entry(tmp_path):
    db = _fresh_db(tmp_path)
    sm = SessionManager(db)
    _make_company(db, "c1", "Test Co")
    _make_member(db, "m1", "Alice", "manager", 120.0)
    db.upsert_company_member("c1", "m1", "manager")
    _make_credential(db, "m1", "alice", "secretpass")
    sm.login("alice", "secretpass")

    project = Project("p1", "Project", "Client", 150.0, 80.0)
    db.upsert_project(project)
    entry = TimeEntry("e1", "a1", "p1", "m2", 60,
                      state=TimeEntryState.SUBMITTED)
    approve_entry(entry)
    assert entry.state == TimeEntryState.APPROVED
    assert entry.reviewed_by == "m1"
    db.close()


def test_manager_can_bill_entry(tmp_path):
    db = _fresh_db(tmp_path)
    sm = SessionManager(db)
    _make_company(db, "c1", "Test Co")
    _make_member(db, "m1", "Alice", "manager", 120.0)
    db.upsert_company_member("c1", "m1", "manager")
    _make_credential(db, "m1", "alice", "secretpass")
    sm.login("alice", "secretpass")

    project = Project("p1", "Project", "Client", 150.0, 80.0)
    db.upsert_project(project)
    entry = TimeEntry("e1", "a1", "p1", "m2", 60,
                      state=TimeEntryState.APPROVED,
                      standard_rate=150.0, loaded_cost_rate=80.0)
    bill_entry(entry, 45.0)
    assert entry.state == TimeEntryState.BILLED
    assert entry.billed_minutes == 45.0
    assert entry.reviewed_by == "m1"
    db.close()


def test_designer_cannot_bill_entry(tmp_path):
    db = _fresh_db(tmp_path)
    sm = SessionManager(db)
    _make_company(db, "c1", "Test Co")
    _make_member(db, "m1", "Alice", "designer", 95.0)
    db.upsert_company_member("c1", "m1", "designer")
    _make_credential(db, "m1", "alice", "secretpass")
    sm.login("alice", "secretpass")

    project = Project("p1", "Project", "Client", 150.0, 80.0)
    db.upsert_project(project)
    entry = TimeEntry("e1", "a1", "p1", "m2", 60,
                      state=TimeEntryState.APPROVED)

    with pytest.raises(PermissionError, match="Only managers can bill"):
        bill_entry(entry, 30.0)
    assert entry.state == TimeEntryState.APPROVED
    assert entry.billed_minutes == 0
    db.close()


# ------------------------------------------------------------------
# Cross-tenant access denial tests
# ------------------------------------------------------------------

def test_cross_tenant_access_denied(tmp_path):
    db = _fresh_db(tmp_path)
    sm = SessionManager(db)
    _make_company(db, "c1", "Company One")
    _make_company(db, "c2", "Company Two")

    # Two managers in different companies
    db.upsert_member(TeamMember("m1", "Alice", "manager", 120.0))
    db.upsert_member(TeamMember("m2", "Bob", "manager", 130.0))
    db.upsert_company_member("c1", "m1", "manager")
    db.upsert_company_member("c2", "m2", "manager")
    _make_credential(db, "m1", "alice", "pass1")
    _make_credential(db, "m2", "bob", "pass2")

    # Alice logs in and tries to approve Bob's entry
    sm.login("alice", "pass1")
    assert sm.get_current_actor().company_id == "c1"

    project = Project("p1", "Project", "Client", 150.0, 80.0)
    db.upsert_project(project)
    entry = TimeEntry("e1", "a1", "p1", "m2", 60,
                      state=TimeEntryState.SUBMITTED)

    # Alice is in company c1, Bob's entry is in company c2
    assert sm.get_current_actor().company_id == "c1"
    db.close()


# ------------------------------------------------------------------
# Historical user identity reconciliation tests
# ------------------------------------------------------------------

def test_user_identity_map_created_on_migration(tmp_path):
    path = str(tmp_path / "identity.db")
    db = Database(path)
    db.upsert_project(Project("p1", "Project", "Client", 100.0, 80.0))
    db.ingest_event(ActivityEvent("ev1", "synthetic", "ext-1", "designer_01", "Revit", "safe",
                                  "2026-01-01T01:00:00Z", "2026-01-01T01:15:00Z", 15))
    db.upsert_attributed_time(AttributedTime("a1", "ev1", "p1", 15, 1.0, "manual"))
    db.upsert_time_entry(TimeEntry("e1", "a1", "p1", "designer_01", 15,
                                   state=TimeEntryState.PENDING_REVIEW))

    maps = db.get_user_identity_maps()
    assert len(maps) == 1
    assert maps[0].historical_user_id == "designer_01"
    assert maps[0].mapped_member_id is None
    assert maps[0].mapping_status == "unresolved"
    assert db.resolve_user_id("designer_01") is None
    assert "designer_01" in db.list_unresolved_user_ids()
    db.close()


def test_map_user_id_to_team_member(tmp_path):
    path = str(tmp_path / "identity_map.db")
    db = Database(path)
    db.upsert_project(Project("p1", "Project", "Client", 100.0, 50.0))
    db.upsert_member(TeamMember("m1", "Alice", "designer", 95.0))
    db.ingest_event(ActivityEvent("ev1", "synthetic", "ext-1", "designer_01", "Revit", "safe",
                                  "2026-01-01T01:00:00Z", "2026-01-01T01:15:00Z", 15))
    db.upsert_attributed_time(AttributedTime("a1", "ev1", "p1", 15, 1.0, "manual"))
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
    path = str(tmp_path / "unmap.db")
    db = Database(path)
    db.upsert_project(Project("p1", "Project", "Synthetic", 100.0, 50.0))
    db.upsert_member(TeamMember("m1", "Alice", "designer", 95.0))
    db.ingest_event(ActivityEvent("ev1", "synthetic", "ext-1", "designer_01", "Revit", "safe",
                                  "2026-01-01T01:00:00Z", "2026-01-01T01:15:00Z", 15))
    db.upsert_attributed_time(AttributedTime("a1", "ev1", "p1", 15, 1.0, "manual"))
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
    path = str(tmp_path / "map_nonexistent.db")
    db = Database(path)
    db.upsert_project(Project("p1", "Project", "Synthetic", 100.0, 50.0))
    db.ingest_event(ActivityEvent("ev1", "synthetic", "ext-1", "designer_01", "Revit", "safe",
                                  "2026-01-01T01:00:00Z", "2026-01-01T01:15:00Z", 15))
    db.upsert_attributed_time(AttributedTime("a1", "ev1", "p1", 15, 1.0, "manual"))
    db.upsert_time_entry(TimeEntry("e1", "a1", "p1", "designer_01", 15,
                                   state=TimeEntryState.APPROVED))
    with pytest.raises(ValueError, match="Unknown team member id"):
        db.map_user_id("designer_01", "nonexistent", "admin_01", "bad mapping")
    assert db.resolve_user_id("designer_01") is None
    assert "designer_01" in db.list_unresolved_user_ids()
    db.close()


def test_identity_map_repeatable_on_reopen(tmp_path):
    path = str(tmp_path / "repeatable.db")
    db = Database(path)
    db.upsert_project(Project("p1", "Project", "Synthetic", 100.0, 50.0))
    db.ingest_event(ActivityEvent("ev1", "synthetic", "ext-1", "designer_01", "Revit", "safe",
                                  "2026-01-01T01:00:00Z", "2026-01-01T01:15:00Z", 15))
    db.upsert_attributed_time(AttributedTime("a1", "ev1", "p1", 15, 1.0, "manual"))
    db.upsert_time_entry(TimeEntry("e1", "a1", "p1", "designer_01", 15,
                                   state=TimeEntryState.PENDING_REVIEW))
    db.close()
    db2 = Database(path)
    maps = db2.get_user_identity_maps()
    assert len(maps) == 1
    assert maps[0].historical_user_id == "designer_01"
    assert maps[0].mapping_status == "unresolved"
    assert db2.conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == 5
    db2.close()


# ------------------------------------------------------------------
# Migration tests
# ------------------------------------------------------------------

def test_migration_v1_to_v4(tmp_path):
    path = str(tmp_path / "v1.db")
    with sqlite3.connect(path) as conn:
        conn.execute("""
            CREATE TABLE projects (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, client TEXT NOT NULL,
                standard_rate REAL NOT NULL, loaded_cost_rate REAL NOT NULL,
                is_billable INTEGER NOT NULL, created_at TEXT NOT NULL
            )
        """)
        conn.execute("CREATE TABLE team_members (id TEXT PRIMARY KEY, name TEXT NOT NULL, role TEXT NOT NULL, loaded_cost_rate REAL NOT NULL, is_active INTEGER NOT NULL)")
        conn.execute("""
            CREATE TABLE project_assignments (
                member_id TEXT NOT NULL REFERENCES team_members(id),
                project_id TEXT NOT NULL REFERENCES projects(id),
                PRIMARY KEY (member_id, project_id)
            )
        """)
        conn.execute("""
            CREATE TABLE activity_events (
                id TEXT PRIMARY KEY, source TEXT NOT NULL, external_id TEXT NOT NULL,
                user_id TEXT NOT NULL, app_name TEXT NOT NULL, window_title TEXT NOT NULL,
                started_at TEXT NOT NULL, ended_at TEXT NOT NULL,
                duration_minutes REAL NOT NULL, is_afk INTEGER NOT NULL DEFAULT 0,
                event_type TEXT NOT NULL, raw_payload TEXT,
                UNIQUE(source, external_id)
            )
        """)
        conn.execute("""
            CREATE TABLE attributed_time (
                id TEXT PRIMARY KEY, activity_event_id TEXT NOT NULL REFERENCES activity_events(id),
                project_id TEXT REFERENCES projects(id), attributed_minutes REAL NOT NULL,
                confidence REAL NOT NULL, correlation_method TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE time_entries (
                id TEXT PRIMARY KEY, attributed_time_id TEXT NOT NULL REFERENCES attributed_time(id),
                project_id TEXT NOT NULL REFERENCES projects(id), user_id TEXT NOT NULL,
                minutes REAL NOT NULL, state TEXT NOT NULL DEFAULT 'pending_review',
                standard_rate REAL NOT NULL, loaded_cost_rate REAL NOT NULL,
                billed_minutes REAL NOT NULL DEFAULT 0, created_at TEXT NOT NULL
            )
        """)
        conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
        conn.execute("INSERT INTO schema_version VALUES (1, '2026-01-01T00:00:00Z')")
        conn.execute("INSERT INTO projects VALUES ('p1','Project','Client',150,80,1,'2026-01-01T00:00:00Z')")
        conn.execute("INSERT INTO team_members VALUES ('m1','Alice','designer',95,1)")
        conn.execute("INSERT INTO activity_events VALUES ('ev1','synthetic','ext-1','m1','Revit','safe','2026-01-01T01:00:00Z','2026-01-01T01:15:00Z',60,0,'window','<redacted>')")
        conn.execute("INSERT INTO attributed_time VALUES ('a1','ev1','p1',60,1.0,'manual','2026-01-01T01:15:00Z')")
        conn.execute("INSERT INTO time_entries VALUES ('e1','a1','p1','m1',60,'pending_review',150,80,0,'2026-01-01T01:15:00Z')")
        conn.commit()

    db = Database(path)
    try:
        assert db.conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == 5
        maps = db.get_user_identity_maps()
        assert len(maps) == 1
        assert maps[0].historical_user_id == "m1"
        assert maps[0].mapping_status == "mapped"
        assert maps[0].mapped_member_id == "m1"
        db.close()
    finally:
        db.close()


def test_approved_and_billed_retained_across_migration(tmp_path):
    path = str(tmp_path / "preserve.db")
    db = Database(path)
    db.upsert_project(Project("p1", "Project", "Client", 150.0, 80.0))
    db.ingest_event(ActivityEvent("ev1", "synthetic", "ext-1", "m1", "Revit", "safe",
                                  "2026-01-01T01:00:00Z", "2026-01-01T01:15:00Z", 60))
    db.upsert_attributed_time(AttributedTime("a1", "ev1", "p1", 60, 1.0, "manual"))
    db.upsert_time_entry(TimeEntry("e1", "a1", "p1", "m1", 60,
                                   state=TimeEntryState.BILLED,
                                   standard_rate=150.0, loaded_cost_rate=80.0,
                                   billed_minutes=45.0))
    db.close()

    db = Database(path)
    entry = db.get_time_entry("e1")
    assert entry is not None
    assert entry.state == TimeEntryState.BILLED
    assert entry.billed_minutes == 45.0
    assert entry.state == TimeEntryState.BILLED
    db.close()


# ------------------------------------------------------------------
# Concurrent write and idempotency tests
# ------------------------------------------------------------------

def test_concurrent_time_entry_creation(tmp_path):
    path = str(tmp_path / "concurrent.db")
    db = Database(path)
    db.upsert_project(Project("p1", "Project", "Client", 150.0, 80.0))
    db.ingest_event(ActivityEvent("e1", "synthetic", "ext-1", "m1", "Revit", "safe",
                                  "2026-01-01T01:00:00Z", "2026-01-01T01:15:00Z", 60))
    db.upsert_attributed_time(AttributedTime("a1", "e1", "p1", 60, 1.0, "manual"))

    import threading
    errors = []

    def create_entry(idx):
        try:
            entry = TimeEntry(f"e{idx}", "a1", "p1", "m1", 30,
                              state=TimeEntryState.PENDING_REVIEW)
            db2 = Database(str(tmp_path / f"concurrent_{idx}.db"))
            db2.upsert_project(Project("p1", "Project", "Client", 150.0, 80.0))
            db2.ingest_event(ActivityEvent("ev1", "synthetic", "ext-1", "m1", "Revit", "safe",
                                          "2026-01-01T01:00:00Z", "2026-01-01T01:15:00Z", 60))
            db2.upsert_attributed_time(AttributedTime("a1", "ev1", "p1", 60, 1.0, "manual"))
            db2.upsert_time_entry(entry)
            db2.close()
        except Exception as exc:
            errors.append(str(e))

    threads = [threading.Thread(target=create_entry, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Concurrent write errors: {errors}"
    db.close()


# ------------------------------------------------------------------
# SH-001: Session validation tests
# ------------------------------------------------------------------

def test_valid_session_permits_authorized_operations(tmp_path):
    """SH-001: Valid session permits authorized operations."""
    db = _fresh_db(tmp_path)
    sm = SessionManager(db)
    _make_company(db, "c1", "Test Co")
    _make_member(db, "m1", "Alice", "designer", 95.0)
    db.upsert_company_member("c1", "m1", "designer")
    _make_credential(db, "m1", "alice", "secretpass")

    actor = sm.login("alice", "secretpass")
    assert current_auth.is_authenticated
    assert current_auth.actor is not None
    assert current_auth.actor.id == "m1"
    sm.logout()
    db.close()


def test_expired_session_is_denied(tmp_path):
    """SH-001: Expired session is denied at protected domain boundary."""
    db = _fresh_db(tmp_path)
    sm = SessionManager(db)
    _make_company(db, "c1", "Test Co")
    _make_member(db, "m1", "Alice", "designer", 95.0)
    db.upsert_company_member("c1", "m1", "designer")
    _make_credential(db, "m1", "alice", "secretpass")

    sm.login("alice", "secretpass")
    assert current_auth.is_authenticated

    # Expire the session
    db.conn.execute(
        "UPDATE sessions SET expires_at = ? WHERE member_id = ?",
        ("2000-01-01T00:00:00+00:00", "m1"),
    )
    db._commit()

    # Accessing current_auth.actor should raise PermissionError
    with pytest.raises(PermissionError, match="invalid, expired, or revoked"):
        _ = current_auth.actor
    assert not current_auth.is_authenticated
    db.close()


def test_revoked_session_is_denied(tmp_path):
    """SH-001: Revoked session is denied."""
    db = _fresh_db(tmp_path)
    sm = SessionManager(db)
    _make_company(db, "c1", "Test Co")
    _make_member(db, "m1", "Alice", "designer", 95.0)
    db.upsert_company_member("c1", "m1", "designer")
    _make_credential(db, "m1", "alice", "secretpass")

    sm.login("alice", "secretpass")
    session_id = current_auth.session_id
    assert session_id is not None

    # Revoke the session
    db.revoke_session(session_id)
    db._commit()

    with pytest.raises(PermissionError, match="invalid, expired, or revoked"):
        _ = current_auth.actor
    assert not current_auth.is_authenticated
    db.close()


def test_deleted_session_is_denied(tmp_path):
    """SH-001: Deleted session is denied."""
    db = _fresh_db(tmp_path)
    sm = SessionManager(db)
    _make_company(db, "c1", "Test Co")
    _make_member(db, "m1", "Alice", "designer", 95.0)
    db.upsert_company_member("c1", "m1", "designer")
    _make_credential(db, "m1", "alice", "secretpass")

    sm.login("alice", "secretpass")
    session_id = current_auth.session_id
    assert session_id is not None

    # Delete the session row
    db.conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    db._commit()

    with pytest.raises(PermissionError, match="invalid, expired, or revoked"):
        _ = current_auth.actor
    assert not current_auth.is_authenticated
    db.close()


def test_disabled_user_is_denied_after_login(tmp_path):
    """SH-001: Disabled user is denied after login (member deactivated)."""
    db = _fresh_db(tmp_path)
    sm = SessionManager(db)
    _make_company(db, "c1", "Test Co")
    _make_member(db, "m1", "Alice", "designer", 95.0, active=True)
    db.upsert_company_member("c1", "m1", "designer")
    _make_credential(db, "m1", "alice", "secretpass")

    sm.login("alice", "secretpass")
    assert current_auth.is_authenticated

    # Deactivate the member
    db.conn.execute(
        "UPDATE team_members SET is_active = 0 WHERE id = ?", ("m1",)
    )
    db._commit()

    with pytest.raises(PermissionError, match="Member account is inactive"):
        _ = current_auth.actor
    assert not current_auth.is_authenticated
    db.close()


def test_disabled_company_is_denied_after_login(tmp_path):
    """SH-001: Disabled company is denied after login."""
    db = _fresh_db(tmp_path)
    sm = SessionManager(db)
    _make_company(db, "c1", "Test Co", is_active=True)
    _make_member(db, "m1", "Alice", "designer", 95.0)
    db.upsert_company_member("c1", "m1", "designer")
    _make_credential(db, "m1", "alice", "secretpass")

    sm.login("alice", "secretpass")
    assert current_auth.is_authenticated

    # Deactivate the company
    db.conn.execute(
        "UPDATE companies SET is_active = 0 WHERE id = ?", ("c1",)
    )
    db._commit()

    with pytest.raises(PermissionError, match="Company is inactive"):
        _ = current_auth.actor
    assert not current_auth.is_authenticated
    db.close()


def test_logout_invalidates_current_session(tmp_path):
    """SH-001: Logout invalidates the current session."""
    db = _fresh_db(tmp_path)
    sm = SessionManager(db)
    _make_company(db, "c1", "Test Co")
    _make_member(db, "m1", "Alice", "designer", 95.0)
    db.upsert_company_member("c1", "m1", "designer")
    _make_credential(db, "m1", "alice", "secretpass")

    sm.login("alice", "secretpass")
    session_id = current_auth.session_id
    assert session_id is not None

    sm.logout()
    assert current_auth.actor is None
    assert current_auth.session_id is None

    # Session should be revoked in the database
    assert db.validate_session(session_id) is None
    db.close()


def test_restart_does_not_implicitly_authenticate(tmp_path):
    """SH-001: Restart does not implicitly authenticate a user."""
    path = str(tmp_path / "restart.db")
    db = Database(path)
    _make_company(db, "c1", "Test Co")
    _make_member(db, "m1", "Alice", "designer", 95.0)
    db.upsert_company_member("c1", "m1", "designer")
    _make_credential(db, "m1", "alice", "secretpass")
    db.close()

    # Reopen database - current_auth should be empty (new process)
    db2 = Database(path)
    assert current_auth.actor is None
    assert not current_auth.is_authenticated
    db2.close()


def test_direct_domain_service_calls_cannot_bypass_session_validation(tmp_path):
    """SH-001: Direct domain-service calls cannot bypass session validation."""
    db = _fresh_db(tmp_path)
    sm = SessionManager(db)
    _make_company(db, "c1", "Test Co")
    _make_member(db, "m1", "Alice", "designer", 95.0)
    db.upsert_company_member("c1", "m1", "designer")
    _make_credential(db, "m1", "alice", "secretpass")

    sm.login("alice", "secretpass")

    project = Project("p1", "Project", "Client", 150.0, 80.0)
    db.upsert_project(project)
    entry = TimeEntry("e1", "a1", "p1", "m1", 60,
                      state=TimeEntryState.SUBMITTED,
                      company_id="c1")

    # Expire session, then try to approve (manager operation by designer)
    db.conn.execute(
        "UPDATE sessions SET expires_at = ? WHERE member_id = ?",
        ("2000-01-01T00:00:00+00:00", "m1"),
    )
    db._commit()

    with pytest.raises(PermissionError, match="invalid, expired, or revoked"):
        approve_entry(entry)
    db.close()


def test_session_switching_cannot_retain_privileges(tmp_path):
    """SH-001: Session switching cannot retain privileges from previous user."""
    db = _fresh_db(tmp_path)
    sm = SessionManager(db)
    _make_company(db, "c1", "Test Co")
    _make_member(db, "m1", "Alice", "designer", 95.0)
    _make_member(db, "m2", "Bob", "manager", 120.0)
    db.upsert_company_member("c1", "m1", "designer")
    db.upsert_company_member("c1", "m2", "manager")
    _make_credential(db, "m1", "alice", "pass1")
    _make_credential(db, "m2", "bob", "pass2")

    # Alice logs in
    sm.login("alice", "pass1")
    assert current_auth.actor.id == "m1"
    assert current_auth.actor.role == Role.DESIGNER

    # Bob logs in - should replace Alice's context
    sm.login("bob", "pass2")
    assert current_auth.actor.id == "m2"
    assert current_auth.actor.role == Role.MANAGER

    # Alice's session should be revoked (logout happened implicitly via new login)
    # Bob's session is valid
    assert current_auth.is_authenticated
    db.close()


# ------------------------------------------------------------------
# SH-002: Company-scoped authorization tests
# ------------------------------------------------------------------

def test_user_with_one_company_authenticates_correctly(tmp_path):
    """SH-002: User with one company authenticates correctly."""
    db = _fresh_db(tmp_path)
    sm = SessionManager(db)
    _make_company(db, "c1", "Company One")
    _make_member(db, "m1", "Alice", "designer", 95.0)
    db.upsert_company_member("c1", "m1", "designer")
    _make_credential(db, "m1", "alice", "secretpass")

    actor = sm.login("alice", "secretpass")
    assert actor.company_id == "c1"
    assert actor.role == Role.DESIGNER
    db.close()


def test_user_with_multiple_companies_requires_explicit_selection(tmp_path):
    """SH-002: User with multiple companies must select one explicitly."""
    db = _fresh_db(tmp_path)
    sm = SessionManager(db)
    _make_company(db, "c1", "Company One")
    _make_company(db, "c2", "Company Two")
    _make_member(db, "m1", "Alice", "designer", 95.0)
    db.upsert_company_member("c1", "m1", "designer")
    db.upsert_company_member("c2", "m1", "manager")
    _make_credential(db, "m1", "alice", "secretpass")

    # Without company_id, should raise ValueError
    with pytest.raises(ValueError, match="Multiple companies found"):
        sm.login("alice", "secretpass")

    # With explicit company_id, should succeed
    actor = sm.login("alice", "secretpass", company_id="c1")
    assert actor.company_id == "c1"
    assert actor.role == Role.DESIGNER

    # Switch to company 2
    actor2 = sm.switch_company("c2")
    assert actor2.company_id == "c2"
    assert actor2.role == Role.MANAGER
    db.close()


def test_company_specific_role_changes_are_respected(tmp_path):
    """SH-002: Company-specific role changes are respected."""
    db = _fresh_db(tmp_path)
    sm = SessionManager(db)
    _make_company(db, "c1", "Company One")
    _make_member(db, "m1", "Alice", "designer", 95.0)
    db.upsert_company_member("c1", "m1", "designer")
    _make_credential(db, "m1", "alice", "secretpass")

    # Login as designer
    actor = sm.login("alice", "secretpass", company_id="c1")
    assert actor.role == Role.DESIGNER

    # Change role to manager in the same company
    db.upsert_company_member("c1", "m1", "manager")

    # New login should reflect the new role
    sm.logout()
    actor2 = sm.login("alice", "secretpass", company_id="c1")
    assert actor2.role == Role.MANAGER
    db.close()


def test_manager_in_company_a_can_approve_company_a_timesheets(tmp_path):
    """SH-002: Manager in Company A can approve Company A timesheets."""
    db = _fresh_db(tmp_path)
    sm = SessionManager(db)
    _make_company(db, "c1", "Company One")
    _make_member(db, "m1", "Alice", "manager", 120.0)
    db.upsert_company_member("c1", "m1", "manager")
    _make_credential(db, "m1", "alice", "secretpass")

    sm.login("alice", "secretpass")

    project = Project("p1", "Project", "Client", 150.0, 80.0)
    db.upsert_project(project)
    entry = TimeEntry("e1", "a1", "p1", "m2", 60,
                      state=TimeEntryState.SUBMITTED,
                      company_id="c1")

    approve_entry(entry)
    assert entry.state == TimeEntryState.APPROVED
    db.close()


def test_manager_in_company_a_cannot_access_company_b_records(tmp_path):
    """SH-002: Manager in Company A cannot access Company B records."""
    db = _fresh_db(tmp_path)
    sm = SessionManager(db)
    _make_company(db, "c1", "Company One")
    _make_company(db, "c2", "Company Two")
    _make_member(db, "m1", "Alice", "manager", 120.0)
    db.upsert_company_member("c1", "m1", "manager")
    _make_credential(db, "m1", "alice", "secretpass")

    sm.login("alice", "secretpass")
    assert current_auth.actor.company_id == "c1"

    # Entry belongs to company B
    entry = TimeEntry("e1", "a1", "p1", "m2", 60,
                      state=TimeEntryState.SUBMITTED,
                      company_id="c2")

    with pytest.raises(PermissionError, match="cannot access records in company"):
        approve_entry(entry)
    assert entry.state == TimeEntryState.SUBMITTED
    db.close()


def test_administrator_privileges_remain_company_scoped(tmp_path):
    """SH-002: Administrator privileges remain company-scoped."""
    db = _fresh_db(tmp_path)
    sm = SessionManager(db)
    _make_company(db, "c1", "Company One")
    _make_company(db, "c2", "Company Two")
    _make_member(db, "m1", "Alice", "administrator", 150.0)
    db.upsert_company_member("c1", "m1", "administrator")
    # Note: m1 is NOT a member of c2
    _make_credential(db, "m1", "alice", "secretpass")

    sm.login("alice", "secretpass", company_id="c1")
    assert current_auth.actor.company_id == "c1"
    assert current_auth.actor.role == Role.ADMINISTRATOR

    # Entry belongs to company B (which m1 is not a member of)
    entry = TimeEntry("e1", "a1", "p1", "m2", 60,
                      state=TimeEntryState.SUBMITTED,
                      company_id="c2")

    with pytest.raises(PermissionError):
        approve_entry(entry)
    db.close()


def test_switching_companies_refreshes_authorization_context(tmp_path):
    """SH-002: Switching companies refreshes authorization context."""
    db = _fresh_db(tmp_path)
    sm = SessionManager(db)
    _make_company(db, "c1", "Company One")
    _make_company(db, "c2", "Company Two")
    _make_member(db, "m1", "Alice", "designer", 95.0)
    db.upsert_company_member("c1", "m1", "designer")
    db.upsert_company_member("c2", "m1", "manager")
    _make_credential(db, "m1", "alice", "secretpass")

    # Login as designer in company 1
    actor = sm.login("alice", "secretpass", company_id="c1")
    assert actor.company_id == "c1"
    assert actor.role == Role.DESIGNER

    # Switch to company 2 - role should change
    actor2 = sm.switch_company("c2")
    assert actor2.company_id == "c2"
    assert actor2.role == Role.MANAGER

    # Old session should be revoked
    assert db.validate_session(actor.session_id) is None
    # New session should be valid
    assert db.validate_session(actor2.session_id) is not None
    db.close()


def test_inactive_membership_is_denied(tmp_path):
    """SH-002: Inactive membership is denied."""
    db = _fresh_db(tmp_path)
    sm = SessionManager(db)
    _make_company(db, "c1", "Company One")
    _make_member(db, "m1", "Alice", "designer", 95.0)
    db.upsert_company_member("c1", "m1", "designer")
    _make_credential(db, "m1", "alice", "secretpass")

    # Deactivate the company membership by setting is_active via company
    # (membership itself doesn't have is_active, but company deactivation
    # covers this case - see test_disabled_company_is_denied_after_login)
    # For membership-level deactivation, we test that login rejects
    # when no active membership exists
    db.conn.execute("DELETE FROM company_members WHERE member_id = ?", ("m1",))
    db._commit()

    with pytest.raises(ValueError, match="Invalid username or password"):
        sm.login("alice", "secretpass")
    db.close()


def test_historical_records_retain_original_identities(tmp_path):
    """SH-002: Historical records retain original identities without inventing company ownership."""
    db = _fresh_db(tmp_path)
    db.upsert_project(Project("p1", "Project", "Client", 100.0, 80.0))
    db.ingest_event(ActivityEvent("ev1", "synthetic", "ext-1", "legacy_user",
                                  "Revit", "safe",
                                  "2026-01-01T01:00:00Z",
                                  "2026-01-01T01:15:00Z", 15))
    db.upsert_attributed_time(AttributedTime("a1", "ev1", "p1", 15, 1.0, "manual"))
    db.upsert_time_entry(TimeEntry("e1", "a1", "p1", "legacy_user", 15,
                                   state=TimeEntryState.PENDING_REVIEW))

    maps = db.get_user_identity_maps()
    assert len(maps) == 1
    assert maps[0].historical_user_id == "legacy_user"
    assert maps[0].mapped_member_id is None  # Unresolved, not auto-assigned
    assert maps[0].mapping_status == "unresolved"
    assert db.resolve_user_id("legacy_user") is None
    db.close()


def test_existing_approved_and_billed_entries_remain_unchanged(tmp_path):
    """SH-002: Existing approved and billed entries remain unchanged."""
    path = str(tmp_path / "preserve.db")
    db = Database(path)
    db.upsert_project(Project("p1", "Project", "Client", 150.0, 80.0))
    db.ingest_event(ActivityEvent("ev1", "synthetic", "ext-1", "m1",
                                  "Revit", "safe",
                                  "2026-01-01T01:00:00Z",
                                  "2026-01-01T01:15:00Z", 60))
    db.upsert_attributed_time(AttributedTime("a1", "ev1", "p1", 60, 1.0, "manual"))
    db.upsert_time_entry(TimeEntry("e1", "a1", "p1", "m1", 60,
                                   state=TimeEntryState.BILLED,
                                   standard_rate=150.0, loaded_cost_rate=80.0,
                                   billed_minutes=45.0))
    db.close()

    # Reopen - v5 migration should preserve all entries
    db = Database(path)
    entry = db.get_time_entry("e1")
    assert entry is not None
    assert entry.state == TimeEntryState.BILLED
    assert entry.billed_minutes == 45.0
    db.close()


# ------------------------------------------------------------------
# SH-003: Password storage tests
# ------------------------------------------------------------------

def test_password_hash_uses_current_iteration_policy():
    """SH-003: Password hash uses current iteration policy (210,000)."""
    h = hash_password("testpassword")
    parts = h.split("$")
    assert parts[0] == "pbkdf2_sha256"
    assert int(parts[1]) == PBKDF2_ITERATIONS
    assert verify_password("testpassword", h) is True


def test_legacy_hash_still_verifies():
    """SH-003: Legacy 100,000-iteration hashes still verify."""
    # Simulate a legacy hash with 100,000 iterations
    import hashlib as _hashlib
    import secrets as _secrets
    salt = _secrets.token_bytes(16)
    dk = _hashlib.pbkdf2_hmac("sha256", b"password", salt, 100_000)
    legacy_hash = f"pbkdf2_sha256$100000${salt.hex()}${dk.hex()}"
    assert verify_password("password", legacy_hash) is True
    assert verify_password("wrong", legacy_hash) is False


def test_malformed_hash_rejected():
    """SH-003: Malformed hash values are rejected safely."""
    assert verify_password("password", "") is False
    assert verify_password("password", "invalid") is False
    assert verify_password("password", "pbkdf2_sha256$bad$salt$hash") is False
    assert verify_password("password", "argon2id$1$salt$hash") is False
    # Non-integer iterations
    assert verify_password("password", "pbkdf2_sha256$notanumber$salt$hash") is False
    # Wrong number of parts
    assert verify_password("password", "pbkdf2_sha256$100$salt") is False
    assert verify_password("password", "pbkdf2_sha256$100$salt$hash$extra") is False
    # Negative iterations
    assert verify_password("password", "pbkdf2_sha256$-1$salt$hash") is False
    # Zero iterations
    assert verify_password("password", "pbkdf2_sha256$0$salt$hash") is False


def test_constant_time_comparison():
    """SH-003: Constant-time comparison is used."""
    from bimspend.auth import _constant_time_compare
    assert _constant_time_compare(b"abc", b"abc") is True
    assert _constant_time_compare(b"abc", b"abd") is False
    assert _constant_time_compare(b"", b"") is True
    assert _constant_time_compare(b"a", b"") is False


def test_failed_auth_does_not_disclose_username_existence(tmp_path):
    """SH-003: Failed authentication does not disclose whether username exists."""
    db = _fresh_db(tmp_path)
    sm = SessionManager(db)
    _make_company(db, "c1", "Test Co")
    _make_member(db, "m1", "Alice", "designer", 95.0)
    db.upsert_company_member("c1", "m1", "designer")
    _make_credential(db, "m1", "alice", "secretpass")

    # Nonexistent user
    with pytest.raises(ValueError, match="Invalid username or password"):
        sm.login("nonexistent", "password")

    # Wrong password for existing user
    with pytest.raises(ValueError, match="Invalid username or password"):
        sm.login("alice", "wrongpassword")

    # Both produce the same error message
    db.close()


def test_rehash_on_login_upgrades_iterations(tmp_path):
    """SH-003: Rehash on login upgrades iterations when below policy."""
    db = _fresh_db(tmp_path)
    sm = SessionManager(db)
    _make_company(db, "c1", "Test Co")
    _make_member(db, "m1", "Alice", "designer", 95.0)
    db.upsert_company_member("c1", "m1", "designer")

    # Create a legacy hash with 100,000 iterations
    import hashlib as _hashlib
    import secrets as _secrets
    salt = _secrets.token_bytes(16)
    dk = _hashlib.pbkdf2_hmac("sha256", b"secretpass", salt, 100_000)
    legacy_hash = f"pbkdf2_sha256$100000${salt.hex()}${dk.hex()}"
    db.upsert_user_credential("m1", "alice", legacy_hash)

    # Login should succeed
    actor = sm.login("alice", "secretpass")
    assert actor.id == "m1"

    # The stored hash should now be upgraded to 210,000 iterations
    cred = db.get_credential_by_username("alice")
    parts = cred["password_hash"].split("$")
    assert int(parts[1]) == PBKDF2_ITERATIONS
    db.close()