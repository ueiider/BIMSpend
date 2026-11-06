"""SQLite persistence layer (stand-in for PostgreSQL).

Provides a small, dependency-free data store for the vertical slice. All
writes use parameterised queries. The activity_events table carries a
UNIQUE(source, external_id) constraint to enforce idempotent ingestion.

Schema versions:
  v1: Initial Build 01 schema (projects, activity_events, attributed_time,
      time_entries with basic columns).
  v2: Build 01+ fixes — added submitted_by/submitted_at to time_entries,
      title_redacted to activity_events, made attributed_time.project_id
      nullable for unassigned/ambiguous events.
  v3: User identity reconciliation — added user_identity_map table mapping
      historical user_ids from time_entries to team_members.
  v4: Authentication and authorization — added companies, company_members,
      user_credentials, and sessions tables for session-based auth.
  v5: Security hardening — added is_active to companies for company-level
      deactivation, and company_id to time_entries for cross-company
      access enforcement at the record level.
  v6: Activity event company scoping — added company_id to activity_events
      for tenant isolation of captured activity events.
  v7: Revit connector integration — added revit_sessions, revit_documents,
      revit_document_mappings, revit_correlation_evidence tables for
      Revit session tracking, document identity, and project correlation.
  v8: Automatic timesheet suggestions — added time_entry_suggestions table
      for auto-generated time entry suggestions awaiting designer review.
"""

from __future__ import annotations

import hashlib
import json
import math
import secrets
import sqlite3
import time
from contextlib import contextmanager
from functools import wraps
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from .models import (
    ActivityEvent,
    AttributedTime,
    Project,
    TeamMember,
    TimeEntry,
    TimeEntryState,
    TimeEntrySuggestion,
    UserIdentityMap,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_title(title: str) -> str:
    """Privacy hash for window titles that should not be stored in plain text.

    Returns a deterministic short hash so titles can be grouped without
    exposing sensitive text.
    """
    return f"[HASH:{hashlib.sha256(title.encode('utf-8')).hexdigest()[:8]}]"


def atomic_write(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        with self.transaction():
            return method(self, *args, **kwargs)
    return wrapper


class Database:
    """SQLite-backed store for projects, activity events, attributed time
    and time entries."""

    def __init__(self, path: str = "bimspend.db"):
        self.path = path
        self.conn = sqlite3.connect(path, timeout=5)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA busy_timeout = 5000")
        if path != ":memory:":
            self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._write_depth = 0
        if self.conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_version'").fetchone():
            version = self.conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
            if version is not None and version > 8:
                self.conn.close()
                raise RuntimeError(f"Database schema version {version} is newer than supported version 8")
        self._create_tables()
        self._migrate()

    @contextmanager
    def transaction(self):
        """One commit for a complete write batch, including nested DB methods."""
        outer = self._write_depth == 0
        if outer:
            for attempt in range(3):
                try:
                    self.conn.execute("BEGIN IMMEDIATE")
                    break
                except sqlite3.OperationalError as exc:
                    if "locked" not in str(exc).lower() or attempt == 2:
                        raise
                    time.sleep(0.05 * (attempt + 1))
        self._write_depth += 1
        try:
            yield
            if outer:
                self.conn.commit()
        except Exception:
            if outer:
                self.conn.rollback()
            raise
        finally:
            self._write_depth -= 1

    def _commit(self):
        if self._write_depth == 0:
            self.conn.commit()

    def _create_tables(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                client TEXT NOT NULL,
                standard_rate REAL NOT NULL,
                loaded_cost_rate REAL NOT NULL,
                is_billable INTEGER NOT NULL DEFAULT 1,
                is_archived INTEGER NOT NULL DEFAULT 0,
                budget_aud REAL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS team_members (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('designer', 'manager', 'administrator')),
                loaded_cost_rate REAL NOT NULL CHECK(loaded_cost_rate >= 0),
                is_active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS project_assignments (
                member_id TEXT NOT NULL REFERENCES team_members(id),
                project_id TEXT NOT NULL REFERENCES projects(id),
                PRIMARY KEY (member_id, project_id)
            );

            CREATE TABLE IF NOT EXISTS activity_events (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                external_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                app_name TEXT NOT NULL,
                window_title TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT NOT NULL,
                duration_minutes REAL NOT NULL,
                is_afk INTEGER NOT NULL DEFAULT 0,
                event_type TEXT NOT NULL,
                raw_payload TEXT,
                title_redacted INTEGER NOT NULL DEFAULT 0,
                UNIQUE(source, external_id)
            );

            CREATE TABLE IF NOT EXISTS attributed_time (
                id TEXT PRIMARY KEY,
                activity_event_id TEXT NOT NULL REFERENCES activity_events(id),
                project_id TEXT REFERENCES projects(id),
                attributed_minutes REAL NOT NULL,
                confidence REAL NOT NULL,
                correlation_method TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS time_entry_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                action TEXT NOT NULL,
                previous_state TEXT,
                new_state TEXT NOT NULL,
                previous_minutes REAL,
                new_minutes REAL NOT NULL,
                billed_minutes REAL NOT NULL,
                recorded_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS time_entries (
                id TEXT PRIMARY KEY,
                attributed_time_id TEXT NOT NULL REFERENCES attributed_time(id),
                project_id TEXT NOT NULL REFERENCES projects(id),
                user_id TEXT NOT NULL,
                minutes REAL NOT NULL,
                state TEXT NOT NULL DEFAULT 'pending_review',
                standard_rate REAL NOT NULL,
                loaded_cost_rate REAL NOT NULL,
                billed_minutes REAL NOT NULL DEFAULT 0,
                review_notes TEXT,
                reviewed_by TEXT,
                reviewed_at TEXT,
                submitted_by TEXT,
                submitted_at TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    @atomic_write
    def _migrate(self) -> None:
        """Apply schema migrations for existing databases.

        Adds columns that didn't exist in earlier Build 01 schema versions.
        Safe to run repeatedly (IF NOT EXISTS style via PRAGMA table_info).
        """
        cols = {row["name"] for row in self.conn.execute("PRAGMA table_info(projects)")}
        if "is_archived" not in cols:
            self.conn.execute("ALTER TABLE projects ADD COLUMN is_archived INTEGER NOT NULL DEFAULT 0")

        if "budget_aud" not in cols:
            self.conn.execute("ALTER TABLE projects ADD COLUMN budget_aud REAL")

        # activity_events: add title_redacted if missing
        cols = {row["name"] for row in self.conn.execute("PRAGMA table_info(activity_events)")}
        if "title_redacted" not in cols:
            self.conn.execute(
                "ALTER TABLE activity_events ADD COLUMN title_redacted INTEGER NOT NULL DEFAULT 0"
            )

        # attributed_time: make project_id nullable (already nullable in v2,
        # but older v1 may have NOT NULL). SQLite can't alter column nullability
        # easily, so we just ensure new inserts can be NULL.
        # No-op for SQLite; project_id column already allows NULL in v2 DDL.

        # time_entries: add submitted_by/submitted_at if missing
        cols = {row["name"] for row in self.conn.execute("PRAGMA table_info(time_entries)")}
        if "submitted_by" not in cols:
            self.conn.execute(
                "ALTER TABLE time_entries ADD COLUMN submitted_by TEXT"
            )
        if "submitted_at" not in cols:
            self.conn.execute(
                "ALTER TABLE time_entries ADD COLUMN submitted_at TEXT"
            )

        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        # Ensure v1 is always recorded
        self.conn.execute("INSERT OR IGNORE INTO schema_version(version, applied_at) VALUES (?, ?)", (1, _now_iso()))
        self._commit()
        # v2 migration: archive columns, unique index, query indexes
        if not self.conn.execute("SELECT 1 FROM schema_version WHERE version = 2").fetchone():
            with self.transaction():
                for table in ("attributed_time", "time_entries"):
                    cols = {row["name"] for row in self.conn.execute(f"PRAGMA table_info({table})")}
                    if "is_archived" not in cols:
                        self.conn.execute(f"ALTER TABLE {table} ADD COLUMN is_archived INTEGER NOT NULL DEFAULT 0")
                duplicate = self.conn.execute(
                    "SELECT attributed_time_id FROM time_entries GROUP BY attributed_time_id HAVING COUNT(*) > 1 LIMIT 1"
                ).fetchone()
                if duplicate:
                    raise RuntimeError("Legacy duplicate time entries require manual reconciliation; no rows were removed")
                self.conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_time_entries_attribution ON time_entries(attributed_time_id)")
                self.conn.execute("CREATE INDEX IF NOT EXISTS ix_attributed_event ON attributed_time(activity_event_id)")
                self.conn.execute("CREATE INDEX IF NOT EXISTS ix_attributed_project ON attributed_time(project_id)")
                self.conn.execute("CREATE INDEX IF NOT EXISTS ix_entry_project ON time_entries(project_id)")
                self.conn.execute("CREATE INDEX IF NOT EXISTS ix_entry_user_state ON time_entries(user_id,state)")
                self.conn.execute("INSERT INTO schema_version(version,applied_at) VALUES (2,?)", (_now_iso(),))
        # v3 migration: user identity reconciliation table
        if not self.conn.execute("SELECT 1 FROM schema_version WHERE version = 3").fetchone():
            with self.transaction():
                self.conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS user_identity_map (
                        id TEXT PRIMARY KEY,
                        historical_user_id TEXT NOT NULL UNIQUE,
                        mapped_member_id TEXT REFERENCES team_members(id),
                        mapping_status TEXT NOT NULL CHECK(mapping_status IN ('unresolved', 'mapped')),
                        mapped_by TEXT,
                        mapped_at TEXT,
                        reason TEXT,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                existing_user_ids = [
                    row[0]
                    for row in self.conn.execute("SELECT DISTINCT user_id FROM time_entries").fetchall()
                ]
                member_ids = {
                    row[0]
                    for row in self.conn.execute("SELECT id FROM team_members").fetchall()
                }
                for uid in existing_user_ids:
                    already = self.conn.execute(
                        "SELECT 1 FROM user_identity_map WHERE historical_user_id = ?", (uid,)
                    ).fetchone()
                    if already:
                        continue
                    if uid in member_ids:
                        self.conn.execute(
                            """INSERT INTO user_identity_map
                               (id, historical_user_id, mapped_member_id, mapping_status, mapped_by, mapped_at, reason, created_at)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                            (f"map_{uid}", uid, uid, "mapped", None, None, None, _now_iso()),
                        )
                    else:
                        self.conn.execute(
                            """INSERT INTO user_identity_map
                               (id, historical_user_id, mapped_member_id, mapping_status, mapped_by, mapped_at, reason, created_at)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                            (f"map_{uid}", uid, None, "unresolved", None, None, None, _now_iso()),
                        )
                self.conn.execute("INSERT INTO schema_version(version,applied_at) VALUES (3,?)", (_now_iso(),))
        # v4 migration: authentication and authorization — companies,
        # company_members, user_credentials, sessions tables
        if not self.conn.execute("SELECT 1 FROM schema_version WHERE version = 4").fetchone():
            with self.transaction():
                self.conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS companies (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                self.conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS company_members (
                        company_id TEXT NOT NULL REFERENCES companies(id),
                        member_id TEXT NOT NULL REFERENCES team_members(id),
                        role TEXT NOT NULL CHECK(role IN ('designer', 'manager', 'administrator')),
                        joined_at TEXT NOT NULL,
                        PRIMARY KEY (company_id, member_id)
                    )
                    """
                )
                self.conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS user_credentials (
                        id TEXT PRIMARY KEY,
                        member_id TEXT NOT NULL UNIQUE REFERENCES team_members(id),
                        username TEXT NOT NULL UNIQUE,
                        password_hash TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        is_active INTEGER NOT NULL DEFAULT 1
                    )
                    """
                )
                self.conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sessions (
                        id TEXT PRIMARY KEY,
                        member_id TEXT NOT NULL REFERENCES team_members(id),
                        company_id TEXT NOT NULL REFERENCES companies(id),
                        expires_at TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        revoked_at TEXT
                    )
                    """
                )
                self.conn.execute(
                    "CREATE INDEX IF NOT EXISTS ix_sessions_member ON sessions(member_id)"
                )
                self.conn.execute(
                    "CREATE INDEX IF NOT EXISTS ix_sessions_company ON sessions(company_id)"
                )
                self.conn.execute("INSERT INTO schema_version(version,applied_at) VALUES (4,?)", (_now_iso(),))
        # v5 migration: security hardening — company is_active flag and
        # company_id on time_entries for cross-company access enforcement
        if not self.conn.execute("SELECT 1 FROM schema_version WHERE version = 5").fetchone():
            with self.transaction():
                cols = {row["name"] for row in self.conn.execute("PRAGMA table_info(companies)")}
                if "is_active" not in cols:
                    self.conn.execute(
                        "ALTER TABLE companies ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1"
                    )
                cols = {row["name"] for row in self.conn.execute("PRAGMA table_info(time_entries)")}
                if "company_id" not in cols:
                    self.conn.execute(
                        "ALTER TABLE time_entries ADD COLUMN company_id TEXT REFERENCES companies(id)"
                    )
                self.conn.execute(
                    "INSERT INTO schema_version(version,applied_at) VALUES (5,?)", (_now_iso(),))
        # v6 migration: company_id on activity_events for tenant isolation
        if not self.conn.execute("SELECT 1 FROM schema_version WHERE version = 6").fetchone():
            with self.transaction():
                cols = {row["name"] for row in self.conn.execute("PRAGMA table_info(activity_events)")}
                if "company_id" not in cols:
                    self.conn.execute(
                        "ALTER TABLE activity_events ADD COLUMN company_id TEXT REFERENCES companies(id)"
                    )
                self.conn.execute(
                    "CREATE INDEX IF NOT EXISTS ix_activity_events_company ON activity_events(company_id)"
                )
                self.conn.execute(
                    "CREATE INDEX IF NOT EXISTS ix_activity_events_user_company ON activity_events(user_id, company_id)"
                )
                self.conn.execute(
                    "INSERT INTO schema_version(version,applied_at) VALUES (6,?)", (_now_iso(),))
        # v7 migration: Revit connector integration — revit_sessions,
        # revit_documents, revit_document_mappings, revit_correlation_evidence
        if not self.conn.execute("SELECT 1 FROM schema_version WHERE version = 7").fetchone():
            with self.transaction():
                self.conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS revit_sessions (
                        id TEXT PRIMARY KEY,
                        process_id INTEGER NOT NULL,
                        session_guid TEXT NOT NULL,
                        revit_version TEXT,
                        started_at TEXT NOT NULL,
                        last_activity_at TEXT NOT NULL,
                        is_active INTEGER NOT NULL DEFAULT 1,
                        company_id TEXT REFERENCES companies(id)
                    )
                    """
                )
                self.conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS revit_documents (
                        id TEXT PRIMARY KEY,
                        document_guid TEXT NOT NULL UNIQUE,
                        document_title TEXT NOT NULL,
                        document_path_hash TEXT,
                        is_workshared INTEGER NOT NULL DEFAULT 0,
                        central_path_hash TEXT,
                        document_type TEXT,
                        created_at TEXT NOT NULL,
                        last_seen_at TEXT NOT NULL,
                        company_id TEXT REFERENCES companies(id)
                    )
                    """
                )
                self.conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS revit_document_mappings (
                        id TEXT PRIMARY KEY,
                        document_guid TEXT NOT NULL REFERENCES revit_documents(document_guid),
                        project_id TEXT NOT NULL REFERENCES projects(id),
                        mapping_method TEXT NOT NULL CHECK(mapping_method IN ('explicit', 'stable_id', 'project_code', 'historical')),
                        confidence TEXT NOT NULL CHECK(confidence IN ('CONFIRMED', 'HIGH', 'MEDIUM', 'LOW', 'UNASSIGNED')),
                        mapped_by TEXT,
                        mapped_at TEXT NOT NULL,
                        reason TEXT,
                        is_active INTEGER NOT NULL DEFAULT 1
                    )
                    """
                )
                self.conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS revit_correlation_evidence (
                        id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL REFERENCES revit_sessions(id),
                        document_guid TEXT NOT NULL REFERENCES revit_documents(document_guid),
                        activity_event_id TEXT REFERENCES activity_events(id),
                        foreground_duration_seconds REAL NOT NULL,
                        is_afk INTEGER NOT NULL DEFAULT 0,
                        is_locked INTEGER NOT NULL DEFAULT 0,
                        correlation_confidence TEXT NOT NULL,
                        correlation_method TEXT,
                        recorded_at TEXT NOT NULL
                    )
                    """
                )
                self.conn.execute(
                    "CREATE INDEX IF NOT EXISTS ix_revit_sessions_company ON revit_sessions(company_id)"
                )
                self.conn.execute(
                    "CREATE INDEX IF NOT EXISTS ix_revit_sessions_active ON revit_sessions(is_active)"
                )
                self.conn.execute(
                    "CREATE INDEX IF NOT EXISTS ix_revit_documents_company ON revit_documents(company_id)"
                )
                self.conn.execute(
                    "CREATE INDEX IF NOT EXISTS ix_revit_documents_guid ON revit_documents(document_guid)"
                )
                self.conn.execute(
                    "CREATE INDEX IF NOT EXISTS ix_revit_mappings_project ON revit_document_mappings(project_id)"
                )
                self.conn.execute(
                    "CREATE INDEX IF NOT EXISTS ix_revit_mappings_document ON revit_document_mappings(document_guid)"
                )
                self.conn.execute(
                    "CREATE INDEX IF NOT EXISTS ix_revit_evidence_session ON revit_correlation_evidence(session_id)"
                )
                self.conn.execute(
                    "CREATE INDEX IF NOT EXISTS ix_revit_evidence_document ON revit_correlation_evidence(document_guid)"
                )
                self.conn.execute(
                    "CREATE INDEX IF NOT EXISTS ix_revit_evidence_activity ON revit_correlation_evidence(activity_event_id)"
                )
                self.conn.execute(
                    "INSERT INTO schema_version(version,applied_at) VALUES (7,?)", (_now_iso(),))
        # v8 migration: automatic timesheet suggestions — time_entry_suggestions
        # table for auto-generated suggestions awaiting designer review.
        if not self.conn.execute("SELECT 1 FROM schema_version WHERE version = 8").fetchone():
            with self.transaction():
                self.conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS time_entry_suggestions (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        company_id TEXT REFERENCES companies(id),
                        project_id TEXT REFERENCES projects(id),
                        start_time TEXT NOT NULL,
                        end_time TEXT NOT NULL,
                        suggested_minutes REAL NOT NULL,
                        confidence TEXT NOT NULL CHECK(confidence IN ('CONFIRMED', 'HIGH', 'MEDIUM', 'LOW', 'UNASSIGNED')),
                        evidence_ids TEXT NOT NULL DEFAULT '[]',
                        state TEXT NOT NULL DEFAULT 'pending_review',
                        edited_minutes REAL,
                        edited_project_id TEXT REFERENCES projects(id),
                        review_notes TEXT,
                        submitted_by TEXT,
                        submitted_at TEXT,
                        reviewed_by TEXT,
                        reviewed_at TEXT,
                        time_entry_id TEXT REFERENCES time_entries(id),
                        created_at TEXT NOT NULL
                    )
                    """
                )
                self.conn.execute(
                    "CREATE INDEX IF NOT EXISTS ix_suggestions_user ON time_entry_suggestions(user_id)"
                )
                self.conn.execute(
                    "CREATE INDEX IF NOT EXISTS ix_suggestions_user_state ON time_entry_suggestions(user_id,state)"
                )
                self.conn.execute(
                    "CREATE INDEX IF NOT EXISTS ix_suggestions_project ON time_entry_suggestions(project_id)"
                )
                self.conn.execute(
                    "CREATE INDEX IF NOT EXISTS ix_suggestions_time_entry ON time_entry_suggestions(time_entry_id)"
                )
                self.conn.execute(
                    "INSERT INTO schema_version(version,applied_at) VALUES (8,?)", (_now_iso(),))

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------
    @atomic_write
    def upsert_project(self, project: Project) -> None:
        values = (project.standard_rate, project.loaded_cost_rate)
        if any(not math.isfinite(v) or v < 0 for v in values):
            raise ValueError("Project rates must be finite nonnegative numbers.")
        if project.budget_aud is not None and (not math.isfinite(project.budget_aud) or project.budget_aud < 0):
            raise ValueError("Budget must be finite and nonnegative.")
        self.conn.execute(
            """
            INSERT INTO projects (id, name, client, standard_rate,
                                  loaded_cost_rate, is_billable, is_archived, budget_aud, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                client=excluded.client,
                standard_rate=excluded.standard_rate,
                loaded_cost_rate=excluded.loaded_cost_rate,
                is_billable=excluded.is_billable,
                is_archived=excluded.is_archived,
                budget_aud=excluded.budget_aud
            """,
            (
                project.id,
                project.name,
                project.client,
                project.standard_rate,
                project.loaded_cost_rate,
                1 if project.is_billable else 0,
                1 if project.is_archived else 0,
                project.budget_aud,
                project.created_at or _now_iso(),
            ),
        )
        self._commit()

    def get_project(self, project_id: str) -> Project | None:
        row = self.conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        return self._row_to_project(row) if row else None

    def list_projects(self) -> list[Project]:
        rows = self.conn.execute("SELECT * FROM projects ORDER BY name").fetchall()
        return [self._row_to_project(r) for r in rows]

    @staticmethod
    def _row_to_project(row: sqlite3.Row) -> Project:
        return Project(
            id=row["id"],
            name=row["name"],
            client=row["client"],
            standard_rate=row["standard_rate"],
            loaded_cost_rate=row["loaded_cost_rate"],
            is_billable=bool(row["is_billable"]),
            is_archived=bool(row["is_archived"]),
            budget_aud=row["budget_aud"],
            created_at=row["created_at"],
        )

    # ------------------------------------------------------------------
    # Local team roster and project assignments
    # ------------------------------------------------------------------
    @atomic_write
    def upsert_member(self, member: TeamMember) -> None:
        if not member.id.strip() or not member.name.strip():
            raise ValueError("Member ID and name are required.")
        if member.role not in ("designer", "manager", "administrator") or member.loaded_cost_rate < 0:
            raise ValueError("Invalid role or hourly cost.")
        self.conn.execute(
            """INSERT INTO team_members (id, name, role, loaded_cost_rate, is_active)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET name=excluded.name, role=excluded.role,
                   loaded_cost_rate=excluded.loaded_cost_rate,
                   is_active=excluded.is_active""",
            (member.id, member.name, member.role, member.loaded_cost_rate,
             int(member.is_active)),
        )
        self._commit()

    def list_members(self) -> list[TeamMember]:
        return [TeamMember(r["id"], r["name"], r["role"], r["loaded_cost_rate"],
                           bool(r["is_active"])) for r in
                self.conn.execute("SELECT * FROM team_members ORDER BY name").fetchall()]

    @atomic_write
    def assign_member(self, member_id: str, project_id: str) -> None:
        member = next((m for m in self.list_members() if m.id == member_id), None)
        project = self.get_project(project_id)
        if member is None or not member.is_active or project is None or project.is_archived:
            raise ValueError("Assignment requires an active member and project.")
        self.conn.execute(
            "INSERT OR IGNORE INTO project_assignments(member_id,project_id) VALUES (?,?)",
            (member_id, project_id),
        )
        self._commit()

    def list_assignments(self, member_id: str) -> list[str]:
        return [r["project_id"] for r in self.conn.execute(
            "SELECT project_id FROM project_assignments WHERE member_id = ? ORDER BY project_id",
            (member_id,),
        ).fetchall()]

    # ------------------------------------------------------------------
    # Activity events (idempotent ingestion via UNIQUE(source, external_id))
    # ------------------------------------------------------------------
    @atomic_write
    def ingest_event(
        self, event: ActivityEvent, company_id: Optional[str] = None
    ) -> bool:
        """Insert an activity event. Returns False if a duplicate
        (source, external_id) already exists — idempotent ingestion.

        company_id scopes the event to a company for tenant isolation.
        If not provided, falls back to event.company_id.
        """
        company_id = company_id or event.company_id
        try:
            self.conn.execute(
                """
                INSERT INTO activity_events
                    (id, source, external_id, user_id, company_id, app_name, window_title,
                     started_at, ended_at, duration_minutes, is_afk,
                     event_type, raw_payload, title_redacted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.source,
                    event.external_id,
                    event.user_id,
                    company_id,
                    event.app_name,
                    event.window_title if event.title_redacted else _hash_title(event.window_title),
                    event.started_at,
                    event.ended_at,
                    event.duration_minutes,
                    1 if event.is_afk else 0,
                    event.event_type,
                    None,  # Untrusted raw payload may contain titles or document paths.
                    1 if event.title_redacted else 0,
                ),
            )
            self._commit()
            return True
        except sqlite3.IntegrityError:
            # Duplicate (source, external_id) — ignore, idempotent.
            return False

    def list_events(self, user_id: str | None = None) -> list[ActivityEvent]:
        if user_id:
            rows = self.conn.execute(
                "SELECT * FROM activity_events WHERE user_id = ? ORDER BY started_at",
                (user_id,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM activity_events ORDER BY started_at"
            ).fetchall()
        return [self._row_to_event(r) for r in rows]

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> ActivityEvent:
        return ActivityEvent(
            id=row["id"],
            source=row["source"],
            external_id=row["external_id"],
            user_id=row["user_id"],
            company_id=row["company_id"],
            app_name=row["app_name"],
            window_title=row["window_title"],
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            duration_minutes=row["duration_minutes"],
            is_afk=bool(row["is_afk"]),
            event_type=row["event_type"],
            raw_payload=json.loads(row["raw_payload"]) if row["raw_payload"] else None,
            title_redacted=bool(row["title_redacted"]),
        )

    # ------------------------------------------------------------------
    # Attributed time (project_id may be NULL for unassigned events)
    # ------------------------------------------------------------------
    @atomic_write
    def upsert_attributed_time(self, at: AttributedTime) -> None:
        self.conn.execute(
            """
            INSERT INTO attributed_time
                (id, activity_event_id, project_id, attributed_minutes,
                 confidence, correlation_method, created_at, is_archived)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                activity_event_id=excluded.activity_event_id,
                project_id=excluded.project_id,
                attributed_minutes=excluded.attributed_minutes,
                confidence=excluded.confidence,
                correlation_method=excluded.correlation_method,
                created_at=excluded.created_at,
                is_archived=excluded.is_archived
            """,
            (
                at.id,
                at.activity_event_id,
                at.project_id,  # may be None for unassigned
                at.attributed_minutes,
                at.confidence,
                at.correlation_method,
                at.created_at or _now_iso(),
                int(at.is_archived),
            ),
        )
        self._commit()

    def list_attributed_time(self) -> list[AttributedTime]:
        rows = self.conn.execute(
            "SELECT * FROM attributed_time ORDER BY created_at"
        ).fetchall()
        return [self._row_to_attributed(r) for r in rows]

    @staticmethod
    def _row_to_attributed(row: sqlite3.Row) -> AttributedTime:
        return AttributedTime(
            id=row["id"],
            activity_event_id=row["activity_event_id"],
            project_id=row["project_id"],  # may be None
            attributed_minutes=row["attributed_minutes"],
            confidence=row["confidence"],
            correlation_method=row["correlation_method"],
            created_at=row["created_at"],
            is_archived=bool(row["is_archived"]),
        )

    # ------------------------------------------------------------------
    # Time entries
    # ------------------------------------------------------------------
    @atomic_write
    def upsert_time_entry(self, entry: TimeEntry, actor_id: str | None = None) -> None:
        previous = self.get_time_entry(entry.id)
        self.conn.execute(
            """
            INSERT INTO time_entries
                (id, attributed_time_id, project_id, user_id, minutes, state,
                 standard_rate, loaded_cost_rate, billed_minutes,
                 review_notes, reviewed_by, reviewed_at,
                 submitted_by, submitted_at, created_at, is_archived,
                 company_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                attributed_time_id=excluded.attributed_time_id,
                project_id=excluded.project_id,
                user_id=excluded.user_id,
                minutes=excluded.minutes,
                state=excluded.state,
                standard_rate=excluded.standard_rate,
                loaded_cost_rate=excluded.loaded_cost_rate,
                billed_minutes=excluded.billed_minutes,
                review_notes=excluded.review_notes,
                reviewed_by=excluded.reviewed_by,
                reviewed_at=excluded.reviewed_at,
                submitted_by=excluded.submitted_by,
                submitted_at=excluded.submitted_at,
                created_at=excluded.created_at,
                is_archived=excluded.is_archived,
                company_id=excluded.company_id
            """,
            (
                entry.id,
                entry.attributed_time_id,
                entry.project_id,
                entry.user_id,
                entry.minutes,
                entry.state.value,
                entry.standard_rate,
                entry.loaded_cost_rate,
                entry.billed_minutes,
                entry.review_notes,
                entry.reviewed_by,
                entry.reviewed_at,
                entry.submitted_by,
                entry.submitted_at,
                entry.created_at or _now_iso(),
                int(entry.is_archived),
                entry.company_id,
            ),
        )
        if previous is None or (previous.state != entry.state or
                                previous.minutes != entry.minutes or
                                previous.billed_minutes != entry.billed_minutes):
            action = ("created" if previous is None else
                      entry.state.value if previous.state != entry.state else "edited")
            self.conn.execute(
                """INSERT INTO time_entry_audit
                   (entry_id, actor_id, action, previous_state, new_state,
                    previous_minutes, new_minutes, billed_minutes, recorded_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (entry.id, actor_id or "unspecified_demo", action,
                 previous.state.value if previous else None, entry.state.value,
                 previous.minutes if previous else None, entry.minutes,
                 entry.billed_minutes, _now_iso()),
            )
        self._commit()
        # Register the entry's user_id in the identity map if not already present,
        # so historical activity can be attributed to team members without losing
        # the original identifier.
        existing_map = self.conn.execute(
            "SELECT 1 FROM user_identity_map WHERE historical_user_id = ?",
            (entry.user_id,),
        ).fetchone()
        if not existing_map:
            member_ids = {
                row[0]
                for row in self.conn.execute("SELECT id FROM team_members").fetchall()
            }
            if entry.user_id in member_ids:
                self.conn.execute(
                    """INSERT INTO user_identity_map
                       (id, historical_user_id, mapped_member_id, mapping_status, mapped_by, mapped_at, reason, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (f"map_{entry.user_id}", entry.user_id, entry.user_id, "mapped",
                     None, None, None, _now_iso()),
                )
            else:
                self.conn.execute(
                    """INSERT INTO user_identity_map
                       (id, historical_user_id, mapped_member_id, mapping_status, mapped_by, mapped_at, reason, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (f"map_{entry.user_id}", entry.user_id, None, "unresolved",
                     None, None, None, _now_iso()),
                )
            self._commit()

    # ------------------------------------------------------------------
    # Time entry suggestions
    # ------------------------------------------------------------------
    @atomic_write
    def upsert_suggestion(self, suggestion: TimeEntrySuggestion) -> bool:
        """Upsert a time entry suggestion.

        Returns True if inserted, False if duplicate (same id already exists).
        Idempotent — saving the same suggestion twice is a no-op.
        """
        import json

        try:
            self.conn.execute(
                """
                INSERT INTO time_entry_suggestions
                    (id, user_id, company_id, project_id, start_time, end_time,
                     suggested_minutes, confidence, evidence_ids, state,
                     edited_minutes, edited_project_id, review_notes,
                     submitted_by, submitted_at, reviewed_by, reviewed_at,
                     time_entry_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO NOTHING
                """,
                (
                    suggestion.id,
                    suggestion.user_id,
                    suggestion.company_id,
                    suggestion.project_id,
                    suggestion.start_time,
                    suggestion.end_time,
                    suggestion.suggested_minutes,
                    suggestion.confidence,
                    json.dumps(suggestion.evidence_ids),
                    suggestion.state,
                    suggestion.edited_minutes,
                    suggestion.edited_project_id,
                    suggestion.review_notes,
                    suggestion.submitted_by,
                    suggestion.submitted_at,
                    suggestion.reviewed_by,
                    suggestion.reviewed_at,
                    suggestion.time_entry_id,
                    suggestion.created_at,
                ),
            )
            self._commit()
            return True
        except sqlite3.IntegrityError:
            # Duplicate id — already exists
            return False

    def get_suggestion(self, suggestion_id: str) -> TimeEntrySuggestion | None:
        """Load a suggestion by id."""
        row = self.conn.execute(
            "SELECT * FROM time_entry_suggestions WHERE id = ?",
            (suggestion_id,),
        ).fetchone()
        return self._row_to_suggestion(row) if row else None

    def list_suggestions(
        self,
        user_id: str,
        state: Optional[str] = None,
    ) -> list[TimeEntrySuggestion]:
        """List suggestions for a user, optionally filtered by state."""
        if state:
            rows = self.conn.execute(
                "SELECT * FROM time_entry_suggestions WHERE user_id = ? AND state = ? ORDER BY start_time",
                (user_id, state),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM time_entry_suggestions WHERE user_id = ? ORDER BY start_time",
                (user_id,),
            ).fetchall()
        return [self._row_to_suggestion(r) for r in rows]

    @staticmethod
    def _row_to_suggestion(row: sqlite3.Row) -> TimeEntrySuggestion:
        import json

        return TimeEntrySuggestion(
            id=row["id"],
            user_id=row["user_id"],
            company_id=row["company_id"],
            project_id=row["project_id"],
            start_time=row["start_time"],
            end_time=row["end_time"],
            suggested_minutes=row["suggested_minutes"],
            confidence=row["confidence"],
            evidence_ids=json.loads(row["evidence_ids"]) if row["evidence_ids"] else [],
            state=row["state"],
            edited_minutes=row["edited_minutes"],
            edited_project_id=row["edited_project_id"],
            review_notes=row["review_notes"],
            submitted_by=row["submitted_by"],
            submitted_at=row["submitted_at"],
            reviewed_by=row["reviewed_by"],
            reviewed_at=row["reviewed_at"],
            time_entry_id=row["time_entry_id"],
            created_at=row["created_at"],
        )

    # ------------------------------------------------------------------
    # Authentication and session management
    # ------------------------------------------------------------------
    def upsert_company(self, company_id: str, name: str, is_active: bool = True) -> None:
        """Create or update a company."""
        self.conn.execute(
            """
            INSERT INTO companies (id, name, created_at, is_active)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                is_active=excluded.is_active
            """,
            (company_id, name, _now_iso(), int(is_active)),
        )
        self._commit()

    def get_company(self, company_id: str) -> dict[str, Any] | None:
        """Get a company by id."""
        row = self.conn.execute(
            "SELECT * FROM companies WHERE id = ?", (company_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_companies(self) -> list[dict[str, Any]]:
        """List all companies."""
        rows = self.conn.execute("SELECT * FROM companies ORDER BY name").fetchall()
        return [dict(row) for row in rows]

    def upsert_company_member(
        self, company_id: str, member_id: str, role: str
    ) -> None:
        """Assign a team member to a company with a role."""
        member = self.conn.execute(
            "SELECT 1 FROM team_members WHERE id = ?", (member_id,)
        ).fetchone()
        if member is None:
            raise ValueError(f"Unknown team member id: {member_id}")
        if role not in ("designer", "manager", "administrator"):
            raise ValueError(f"Invalid role: {role}")
        self.conn.execute(
            """
            INSERT INTO company_members (company_id, member_id, role, joined_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(company_id, member_id) DO UPDATE SET role=excluded.role
            """,
            (company_id, member_id, role, _now_iso()),
        )
        self._commit()

    def list_company_members(self, company_id: str) -> list[dict[str, Any]]:
        """List all members of a company with their roles."""
        rows = self.conn.execute(
            """
            SELECT cm.member_id, cm.role, cm.joined_at, tm.name, tm.loaded_cost_rate, tm.is_active
            FROM company_members cm
            JOIN team_members tm ON tm.id = cm.member_id
            WHERE cm.company_id = ?
            ORDER BY tm.name
            """,
            (company_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def list_member_companies(self, member_id: str) -> list[dict[str, Any]]:
        """List all companies a member belongs to."""
        rows = self.conn.execute(
            """
            SELECT cm.company_id, c.name, cm.role, cm.joined_at
            FROM company_members cm
            JOIN companies c ON c.id = cm.company_id
            WHERE cm.member_id = ?
            ORDER BY c.name
            """,
            (member_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def upsert_user_credential(
        self, member_id: str, username: str, password_hash: str
    ) -> None:
        """Create or update user credentials for a team member."""
        member = self.conn.execute(
            "SELECT 1 FROM team_members WHERE id = ?", (member_id,)
        ).fetchone()
        if member is None:
            raise ValueError(f"Unknown team member id: {member_id}")
        self.conn.execute(
            """
            INSERT INTO user_credentials (member_id, username, password_hash, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(member_id) DO UPDATE SET
                username=excluded.username,
                password_hash=excluded.password_hash
            """,
            (member_id, username, password_hash, _now_iso()),
        )
        self._commit()

    def get_credential_by_username(self, username: str) -> dict[str, Any] | None:
        """Get user credential by username."""
        row = self.conn.execute(
            """
            SELECT uc.id, uc.member_id, uc.username, uc.password_hash,
                   uc.created_at, uc.is_active, tm.name, tm.role, tm.is_active as member_active
            FROM user_credentials uc
            JOIN team_members tm ON tm.id = uc.member_id
            WHERE uc.username = ?
            """,
            (username,),
        ).fetchone()
        return dict(row) if row else None

    def create_session(
        self, member_id: str, company_id: str, ttl_minutes: int = 480
    ) -> str:
        """Create a session for a member in a company. Returns session id."""
        member = self.conn.execute(
            "SELECT 1 FROM team_members WHERE id = ? AND is_active = 1", (member_id,)
        ).fetchone()
        if member is None:
            raise ValueError(f"Unknown or inactive team member: {member_id}")
        company = self.conn.execute(
            "SELECT 1 FROM companies WHERE id = ?", (company_id,)
        ).fetchone()
        if company is None:
            raise ValueError(f"Unknown company: {company_id}")
        member_company = self.conn.execute(
            "SELECT 1 FROM company_members WHERE company_id = ? AND member_id = ?",
            (company_id, member_id),
        ).fetchone()
        if member_company is None:
            raise ValueError(f"Member {member_id} is not in company {company_id}")
        session_id = secrets.token_urlsafe(32)
        now = _now_iso()
        expires_at = (
            datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
        ).isoformat()
        self.conn.execute(
            """
            INSERT INTO sessions (id, member_id, company_id, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, member_id, company_id, expires_at, now),
        )
        self._commit()
        return session_id

    def validate_session(self, session_id: str) -> dict[str, Any] | None:
        """Validate a session and return member/company info if valid.

        Fail-closed: returns None if the session is expired, revoked,
        the member is inactive, or the company is inactive.
        """
        row = self.conn.execute(
            """
            SELECT s.id, s.member_id, s.company_id, s.expires_at, s.created_at,
                   s.revoked_at, tm.name, tm.role, tm.is_active as member_active,
                   c.name as company_name, c.is_active as company_active
            FROM sessions s
            JOIN team_members tm ON tm.id = s.member_id
            JOIN companies c ON c.id = s.company_id
            WHERE s.id = ?
            """,
            (session_id,),
        ).fetchone()
        if row is None:
            return None
        if row["revoked_at"] is not None:
            return None
        if row["member_active"] == 0:
            return None
        if row["company_active"] == 0:
            return None
        expires_at = datetime.fromisoformat(row["expires_at"])
        if expires_at < datetime.now(timezone.utc):
            return None
        return dict(row)

    def revoke_session(self, session_id: str) -> None:
        """Revoke a session."""
        self.conn.execute(
            "UPDATE sessions SET revoked_at = ? WHERE id = ?",
            (_now_iso(), session_id),
        )
        self._commit()

    def revoke_all_sessions_for_member(self, member_id: str) -> None:
        """Revoke all sessions for a member."""
        self.conn.execute(
            "UPDATE sessions SET revoked_at = ? WHERE member_id = ? AND revoked_at IS NULL",
            (_now_iso(), member_id),
        )
        self._commit()

    # ------------------------------------------------------------------
    # User identity reconciliation (existing methods)
    # ------------------------------------------------------------------
    def resolve_user_id(self, user_id: str) -> str | None:
        """Resolve a historical user_id to a team_member id, or None if unresolved."""
        row = self.conn.execute(
            "SELECT mapped_member_id FROM user_identity_map "
            "WHERE historical_user_id = ? AND mapping_status = 'mapped'",
            (user_id,),
        ).fetchone()
        return row[0] if row else None

    def list_unresolved_user_ids(self) -> list[str]:
        """Return user_ids that have no team_member mapping."""
        return [
            row[0]
            for row in self.conn.execute(
                "SELECT historical_user_id FROM user_identity_map WHERE mapping_status = 'unresolved'"
            ).fetchall()
        ]

    def get_user_identity_maps(self) -> list[UserIdentityMap]:
        """Return all user identity mappings."""
        rows = self.conn.execute(
            "SELECT * FROM user_identity_map ORDER BY historical_user_id"
        ).fetchall()
        return [self._row_to_user_identity_map(r) for r in rows]

    def map_user_id(
        self,
        historical_user_id: str,
        member_id: str,
        mapped_by: str,
        reason: str,
    ) -> None:
        """Authorized mapping of a historical user_id to a team_member."""
        member = self.conn.execute(
            "SELECT 1 FROM team_members WHERE id = ?", (member_id,)
        ).fetchone()
        if member is None:
            raise ValueError(f"Unknown team member id: {member_id}")
        existing = self.conn.execute(
            "SELECT 1 FROM user_identity_map WHERE historical_user_id = ?",
            (historical_user_id,),
        ).fetchone()
        if existing:
            self.conn.execute(
                """UPDATE user_identity_map
                   SET mapped_member_id = ?, mapping_status = 'mapped', mapped_by = ?,
                       mapped_at = ?, reason = ?
                   WHERE historical_user_id = ?""",
                (member_id, mapped_by, _now_iso(), reason, historical_user_id),
            )
        else:
            self.conn.execute(
                """INSERT INTO user_identity_map
                   (id, historical_user_id, mapped_member_id, mapping_status, mapped_by, mapped_at, reason, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    f"map_{historical_user_id}",
                    historical_user_id,
                    member_id,
                    "mapped",
                    mapped_by,
                    _now_iso(),
                    reason,
                    _now_iso(),
                ),
            )
        self._commit()

    def unmap_user_id(self, historical_user_id: str, mapped_by: str, reason: str) -> None:
        """Unmap a historical user_id, returning it to unresolved status."""
        self.conn.execute(
            """UPDATE user_identity_map
               SET mapped_member_id = NULL, mapping_status = 'unresolved', mapped_by = ?,
                   mapped_at = ?, reason = ?
               WHERE historical_user_id = ?""",
            (mapped_by, _now_iso(), reason, historical_user_id),
        )
        self._commit()

    @staticmethod
    def _row_to_user_identity_map(row: sqlite3.Row) -> UserIdentityMap:
        return UserIdentityMap(
            id=row["id"],
            historical_user_id=row["historical_user_id"],
            mapped_member_id=row["mapped_member_id"],
            mapping_status=row["mapping_status"],
            mapped_by=row["mapped_by"],
            mapped_at=row["mapped_at"],
            reason=row["reason"],
            created_at=row["created_at"],
        )

    def list_entry_history(self, entry_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT actor_id, action, previous_state, new_state, previous_minutes,"
            " new_minutes, billed_minutes, recorded_at FROM time_entry_audit"
            " WHERE entry_id = ? ORDER BY id", (entry_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    def get_time_entry(self, entry_id: str) -> TimeEntry | None:
        row = self.conn.execute(
            "SELECT * FROM time_entries WHERE id = ?", (entry_id,)
        ).fetchone()
        return self._row_to_entry(row) if row else None

    def list_time_entries(self, state: TimeEntryState | None = None) -> list[TimeEntry]:
        if state:
            rows = self.conn.execute(
                "SELECT * FROM time_entries WHERE state = ? ORDER BY created_at",
                (state.value,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM time_entries ORDER BY created_at"
            ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def list_time_entries_by_user(
        self, user_id: str, state: TimeEntryState | None = None
    ) -> list[TimeEntry]:
        if state:
            rows = self.conn.execute(
                "SELECT * FROM time_entries WHERE user_id = ? AND state = ? ORDER BY created_at",
                (user_id, state.value),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM time_entries WHERE user_id = ? ORDER BY created_at",
                (user_id,),
            ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    @staticmethod
    def _row_to_entry(row: sqlite3.Row) -> TimeEntry:
        return TimeEntry(
            id=row["id"],
            attributed_time_id=row["attributed_time_id"],
            project_id=row["project_id"],
            user_id=row["user_id"],
            minutes=row["minutes"],
            state=TimeEntryState(row["state"]),
            standard_rate=row["standard_rate"],
            loaded_cost_rate=row["loaded_cost_rate"],
            billed_minutes=row["billed_minutes"],
            review_notes=row["review_notes"],
            reviewed_by=row["reviewed_by"],
            reviewed_at=row["reviewed_at"],
            submitted_by=row["submitted_by"],
            submitted_at=row["submitted_at"],
            created_at=row["created_at"],
            is_archived=bool(row["is_archived"]),
            company_id=row["company_id"],
        )

    def close(self) -> None:
        self.conn.close()