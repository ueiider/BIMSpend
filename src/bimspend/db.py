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
"""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import time
from contextlib import contextmanager
from functools import wraps
from datetime import datetime, timezone
from typing import Any

from .models import (
    ActivityEvent,
    AttributedTime,
    Project,
    TeamMember,
    TimeEntry,
    TimeEntryState,
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
            if version is not None and version > 2:
                self.conn.close()
                raise RuntimeError(f"Database schema version {version} is newer than supported version 2")
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
                role TEXT NOT NULL CHECK(role IN ('designer', 'manager')),
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
        self.conn.execute("INSERT OR IGNORE INTO schema_version(version, applied_at) VALUES (?, ?)", (1, _now_iso()))
        self._commit()
        if self.conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] < 2:
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
        if member.role not in ("designer", "manager") or member.loaded_cost_rate < 0:
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
    def ingest_event(self, event: ActivityEvent) -> bool:
        """Insert an activity event. Returns False if a duplicate
        (source, external_id) already exists — idempotent ingestion."""
        try:
            self.conn.execute(
                """
                INSERT INTO activity_events
                    (id, source, external_id, user_id, app_name, window_title,
                     started_at, ended_at, duration_minutes, is_afk,
                     event_type, raw_payload, title_redacted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.source,
                    event.external_id,
                    event.user_id,
                    event.app_name,
                    _hash_title(event.window_title) if not event.title_redacted else "[REDACTED]",
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
                 submitted_by, submitted_at, created_at, is_archived)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                is_archived=excluded.is_archived
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
        )

    def close(self) -> None:
        self.conn.close()
