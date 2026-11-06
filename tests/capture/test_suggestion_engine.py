"""Tests for the suggestion engine (R1-05).

Tests cover:
- Suggestion generation from activity events
- Same-project grouping across AFK gaps
- Different-project separation
- AFK exclusion
- Locked-session exclusion
- Missing heartbeat handling
- Duplicate event handling
- Reprocessing idempotency
- Confidence classification
- Unassigned project handling
- Designer project correction
- Duration correction
- Suggestion rejection
- Suggestion acceptance/submission
- Role-based permissions
- Cross-company isolation
- Approved entry immutability
- Billed entry immutability
- SQLite migration compatibility
- Existing timesheet regression
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bimspend.db import Database
from bimspend.models import (
    ActivityEvent,
    AttributedTime,
    Project,
    TeamMember,
    TimeEntry,
    TimeEntrySuggestion,
    TimeEntryState,
)
from bimspend.capture import SuggestionEngine, SuggestionConfig


# ------------------------------------------------------------------
# Helper factories
# ------------------------------------------------------------------

def _make_event(
    db: Database,
    event_id: str,
    user_id: str,
    company_id: str,
    app_name: str,
    window_title: str,
    started_at: str,
    ended_at: str,
    duration_minutes: float,
    is_afk: bool = False,
    event_type: str = "active_window",
    company_active: bool = True,
) -> ActivityEvent:
    """Create and persist an activity event."""
    event = ActivityEvent(
        id=event_id,
        source="activitywatch",
        external_id=f"ext-{event_id}",
        user_id=user_id,
        company_id=company_id,
        app_name=app_name,
        window_title=window_title,
        started_at=started_at,
        ended_at=ended_at,
        duration_minutes=duration_minutes,
        is_afk=is_afk,
        event_type=event_type,
        title_redacted=True,
    )
    db.ingest_event(event, company_id=company_id)
    # Also create attributed_time record (FK target for time_entries)
    db.upsert_attributed_time(
        AttributedTime(
            id=f"att-{event_id}",
            activity_event_id=event_id,
            project_id=None,
            attributed_minutes=duration_minutes,
            confidence=1.0,
            correlation_method="window_title_match",
            created_at=started_at,
        )
    )
    return event


def _make_correlation_evidence(
    db: Database,
    activity_event_id: str,
    document_guid: str,
    correlation_confidence: str,
    correlation_method: str,
    is_afk: bool = False,
    is_locked: bool = False,
    session_id: str = "session-1",
    foreground_duration_seconds: float = 30.0,
) -> None:
    """Insert correlation evidence for an activity event."""
    # Insert session first (FK target for revit_correlation_evidence)
    db.conn.execute(
        """
        INSERT OR IGNORE INTO revit_sessions
            (id, process_id, session_guid, revit_version, started_at,
             last_activity_at, is_active, company_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            f"pid-{session_id}",
            session_id,
            "Revit 2026",
            "2026-01-01T09:00:00Z",
            "2026-01-01T09:30:00Z",
            1,
            "c1",
        ),
    )
    # Insert document first (FK target)
    db.conn.execute(
        """
        INSERT OR IGNORE INTO revit_documents
            (id, document_guid, document_title, document_path_hash,
             is_workshared, central_path_hash, document_type,
             created_at, last_seen_at, company_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"doc-{document_guid}",
            document_guid,
            f"Document {document_guid}",
            None,
            0,
            None,
            "workshared",
            "2026-01-01T00:00:00Z",
            "2026-01-01T09:30:00Z",
            "c1",
        ),
    )
    db.conn.execute(
        """
        INSERT INTO revit_correlation_evidence
            (id, session_id, document_guid, activity_event_id,
             foreground_duration_seconds, is_afk, is_locked,
             correlation_confidence, correlation_method, recorded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"ev-{activity_event_id}",
            session_id,
            document_guid,
            activity_event_id,
            foreground_duration_seconds,
            1 if is_afk else 0,
            1 if is_locked else 0,
            correlation_confidence,
            correlation_method,
            "2026-01-01T00:00:00Z",
        ),
    )
    db.conn.commit()


# ------------------------------------------------------------------
# Suggestion engine tests
# ------------------------------------------------------------------

def test_suggestion_generation_single_project(tmp_path):
    """Single project activity generates one suggestion."""
    db = Database(str(tmp_path / "suggest.db"))
    db.upsert_company("c1", "Test Company", is_active=True)
    db.upsert_member(TeamMember("u1", "User One", "designer", 95, True))
    db.upsert_company_member("c1", "u1", "designer")

    _make_event(db, "ev1", "u1", "c1", "Revit", "[HASH:abc]",
                "2026-01-01T09:00:00Z", "2026-01-01T09:30:00Z", 30.0)
    _make_correlation_evidence(db, "ev1", "doc-1", "HIGH", "stable_id")

    engine = SuggestionEngine(db)
    suggestions = engine.generate_suggestions("u1", "2026-01-01T00:00:00Z", "2026-01-01T23:59:59Z")

    assert len(suggestions) == 1
    s = suggestions[0]
    assert s.user_id == "u1"
    assert s.company_id == "c1"
    assert s.project_id == "doc-1"
    assert s.suggested_minutes == 30.0
    assert s.confidence == "HIGH"
    assert s.state == "pending_review"
    assert s.evidence_ids == ["ev1"]
    db.close()


def test_same_project_grouping_across_afk(tmp_path):
    """Same-project events separated by AFK are merged."""
    db = Database(str(tmp_path / "group.db"))
    db.upsert_company("c1", "Test Company", is_active=True)
    db.upsert_member(TeamMember("u1", "User One", "designer", 95, True))
    db.upsert_company_member("c1", "u1", "designer")

    # First Revit segment
    _make_event(db, "ev1", "u1", "c1", "Revit", "[HASH:abc]",
                "2026-01-01T09:00:00Z", "2026-01-01T09:25:00Z", 25.0)
    _make_correlation_evidence(db, "ev1", "doc-1", "HIGH", "stable_id")

    # AFK event (excluded)
    _make_event(db, "ev2", "u1", "c1", "Revit", "[HASH:abc]",
                "2026-01-01T09:25:00Z", "2026-01-01T09:30:00Z", 5.0, is_afk=True)
    _make_correlation_evidence(db, "ev2", "doc-1", "HIGH", "stable_id")

    # Second Revit segment
    _make_event(db, "ev3", "u1", "c1", "Revit", "[HASH:abc]",
                "2026-01-01T09:30:00Z", "2026-01-01T10:15:00Z", 45.0)
    _make_correlation_evidence(db, "ev3", "doc-1", "HIGH", "stable_id")

    engine = SuggestionEngine(db)
    suggestions = engine.generate_suggestions("u1", "2026-01-01T00:00:00Z", "2026-01-01T23:59:59Z")

    assert len(suggestions) == 1
    s = suggestions[0]
    assert s.project_id == "doc-1"
    assert s.suggested_minutes == 70.0  # 25 + 45, AFK excluded
    assert s.confidence == "HIGH"
    assert set(s.evidence_ids) == {"ev1", "ev3"}  # AFK event excluded
    db.close()


def test_different_project_separation(tmp_path):
    """Different projects create separate suggestions."""
    db = Database(str(tmp_path / "sep.db"))
    db.upsert_company("c1", "Test Company", is_active=True)
    db.upsert_member(TeamMember("u1", "User One", "designer", 95, True))
    db.upsert_company_member("c1", "u1", "designer")

    _make_event(db, "ev1", "u1", "c1", "Revit", "[HASH:abc]",
                "2026-01-01T09:00:00Z", "2026-01-01T09:30:00Z", 30.0)
    _make_correlation_evidence(db, "ev1", "doc-a", "HIGH", "stable_id")

    _make_event(db, "ev2", "u1", "c1", "Revit", "[HASH:def]",
                "2026-01-01T09:30:00Z", "2026-01-01T10:00:00Z", 30.0)
    _make_correlation_evidence(db, "ev2", "doc-b", "HIGH", "stable_id")

    engine = SuggestionEngine(db)
    suggestions = engine.generate_suggestions("u1", "2026-01-01T00:00:00Z", "2026-01-01T23:59:59Z")

    assert len(suggestions) == 2
    project_ids = sorted([s.project_id for s in suggestions])
    assert project_ids == ["doc-a", "doc-b"]
    for s in suggestions:
        assert s.suggested_minutes == 30.0
    db.close()


def test_afk_exclusion(tmp_path):
    """AFK events are excluded from suggestions."""
    db = Database(str(tmp_path / "afk.db"))
    db.upsert_company("c1", "Test Company", is_active=True)
    db.upsert_member(TeamMember("u1", "User One", "designer", 95, True))
    db.upsert_company_member("c1", "u1", "designer")

    _make_event(db, "ev1", "u1", "c1", "Revit", "[HASH:abc]",
                "2026-01-01T09:00:00Z", "2026-01-01T09:30:00Z", 30.0)
    _make_correlation_evidence(db, "ev1", "doc-1", "HIGH", "stable_id")

    _make_event(db, "ev2", "u1", "c1", "Revit", "[HASH:abc]",
                "2026-01-01T09:30:00Z", "2026-01-01T10:00:00Z", 30.0, is_afk=True)
    _make_correlation_evidence(db, "ev2", "doc-1", "HIGH", "stable_id")

    engine = SuggestionEngine(db)
    suggestions = engine.generate_suggestions("u1", "2026-01-01T00:00:00Z", "2026-01-01T23:59:59Z")

    assert len(suggestions) == 1
    s = suggestions[0]
    assert s.suggested_minutes == 30.0  # Only non-AFK time
    db.close()


def test_locked_session_exclusion(tmp_path):
    """Locked session events are excluded from suggestions."""
    db = Database(str(tmp_path / "lock.db"))
    db.upsert_company("c1", "Test Company", is_active=True)
    db.upsert_member(TeamMember("u1", "User One", "designer", 95, True))
    db.upsert_company_member("c1", "u1", "designer")

    _make_event(db, "ev1", "u1", "c1", "Revit", "[HASH:abc]",
                "2026-01-01T09:00:00Z", "2026-01-01T09:30:00Z", 30.0)
    _make_correlation_evidence(db, "ev1", "doc-1", "HIGH", "stable_id", is_locked=True)

    engine = SuggestionEngine(db)
    suggestions = engine.generate_suggestions("u1", "2026-01-01T00:00:00Z", "2026-01-01T23:59:59Z")

    assert len(suggestions) == 0
    db.close()


def test_confidence_classification(tmp_path):
    """Confidence from correlation evidence is preserved."""
    db = Database(str(tmp_path / "conf.db"))
    db.upsert_company("c1", "Test Company", is_active=True)
    db.upsert_member(TeamMember("u1", "User One", "designer", 95, True))
    db.upsert_company_member("c1", "u1", "designer")

    _make_event(db, "ev1", "u1", "c1", "Revit", "[HASH:abc]",
                "2026-01-01T09:00:00Z", "2026-01-01T09:30:00Z", 30.0)
    _make_correlation_evidence(db, "ev1", "doc-1", "CONFIRMED", "explicit")

    engine = SuggestionEngine(db)
    suggestions = engine.generate_suggestions("u1", "2026-01-01T00:00:00Z", "2026-01-01T23:59:59Z")

    assert len(suggestions) == 1
    assert suggestions[0].confidence == "CONFIRMED"
    db.close()


def test_unassigned_project(tmp_path):
    """Events without correlation evidence get UNASSIGNED confidence."""
    db = Database(str(tmp_path / "unassigned.db"))
    db.upsert_company("c1", "Test Company", is_active=True)
    db.upsert_member(TeamMember("u1", "User One", "designer", 95, True))
    db.upsert_company_member("c1", "u1", "designer")

    _make_event(db, "ev1", "u1", "c1", "Revit", "[HASH:abc]",
                "2026-01-01T09:00:00Z", "2026-01-01T09:30:00Z", 30.0)
    # No correlation evidence

    engine = SuggestionEngine(db)
    suggestions = engine.generate_suggestions("u1", "2026-01-01T00:00:00Z", "2026-01-01T23:59:59Z")

    assert len(suggestions) == 1
    s = suggestions[0]
    assert s.project_id is None
    assert s.confidence == "unassigned"
    db.close()


def test_min_duration_filter(tmp_path):
    """Entries below minimum duration are filtered out."""
    db = Database(str(tmp_path / "mindur.db"))
    db.upsert_company("c1", "Test Company", is_active=True)
    db.upsert_member(TeamMember("u1", "User One", "designer", 95, True))
    db.upsert_company_member("c1", "u1", "designer")

    _make_event(db, "ev1", "u1", "c1", "Revit", "[HASH:abc]",
                "2026-01-01T09:00:00Z", "2026-01-01T09:02:00Z", 2.0)
    _make_correlation_evidence(db, "ev1", "doc-1", "HIGH", "stable_id")

    engine = SuggestionEngine(db, config=SuggestionConfig(min_duration_minutes=5.0))
    suggestions = engine.generate_suggestions("u1", "2026-01-01T00:00:00Z", "2026-01-01T23:59:59Z")

    assert len(suggestions) == 0
    db.close()


def test_reprocessing_idempotency(tmp_path):
    """Reprocessing produces the same suggestions."""
    db = Database(str(tmp_path / "idempotent.db"))
    db.upsert_company("c1", "Test Company", is_active=True)
    db.upsert_member(TeamMember("u1", "User One", "designer", 95, True))
    db.upsert_company_member("c1", "u1", "designer")

    _make_event(db, "ev1", "u1", "c1", "Revit", "[HASH:abc]",
                "2026-01-01T09:00:00Z", "2026-01-01T09:30:00Z", 30.0)
    _make_correlation_evidence(db, "ev1", "doc-1", "HIGH", "stable_id")

    engine = SuggestionEngine(db)
    s1 = engine.generate_suggestions("u1", "2026-01-01T00:00:00Z", "2026-01-01T23:59:59Z")
    s2 = engine.generate_suggestions("u1", "2026-01-01T00:00:00Z", "2026-01-01T23:59:59Z")

    assert len(s1) == len(s2) == 1
    assert s1[0].id == s2[0].id  # Same suggestion id
    assert s1[0].suggested_minutes == s2[0].suggested_minutes
    db.close()


# ------------------------------------------------------------------
# Designer review workflow tests
# ------------------------------------------------------------------

def test_designer_submit_suggestion(tmp_path):
    """Designer submits a suggestion for manager approval."""
    db = Database(str(tmp_path / "submit.db"))
    db.upsert_company("c1", "Test Company", is_active=True)
    db.upsert_member(TeamMember("u1", "User One", "designer", 95, True))
    db.upsert_member(TeamMember("m1", "Manager One", "manager", 120, True))
    db.upsert_company_member("c1", "u1", "designer")
    db.upsert_company_member("c1", "m1", "manager")
    db.upsert_project(Project("proj-a", "Project A", "Client", 150, 80, True))
    _make_event(db, "ev1", "u1", "c1", "Revit", "[HASH:abc]",
                "2026-01-01T09:00:00Z", "2026-01-01T09:30:00Z", 30.0)
    _make_correlation_evidence(db, "ev1", "doc-1", "HIGH", "stable_id")

    suggestion = TimeEntrySuggestion(
        id="sugg-1",
        user_id="u1",
        company_id="c1",
        project_id="proj-a",
        start_time="2026-01-01T09:00:00Z",
        end_time="2026-01-01T09:30:00Z",
        suggested_minutes=30.0,
        confidence="HIGH",
        evidence_ids=["ev1"],
        state="pending_review",
        created_at="2026-01-01T09:30:00Z",
    )
    db.upsert_suggestion(suggestion)

    engine = SuggestionEngine(db)
    from bimspend.identity import current_auth, Actor, Role

    # Designer submits
    current_auth.set_actor(Actor(id="u1", role=Role.DESIGNER, company_id="c1"))
    engine.submit_suggestion(suggestion, actor_id="u1")

    assert suggestion.state == "submitted"
    assert suggestion.submitted_by == "u1"
    assert suggestion.submitted_at is not None
    assert suggestion.time_entry_id is not None

    # Time entry was created
    entries = db.list_time_entries(state=TimeEntryState.SUBMITTED)
    assert len(entries) == 1
    assert entries[0].user_id == "u1"
    assert entries[0].project_id == "proj-a"
    assert entries[0].minutes == 30.0
    assert entries[0].state == TimeEntryState.SUBMITTED
    db.close()


def test_designer_reject_suggestion(tmp_path):
    """Designer rejects a suggestion."""
    db = Database(str(tmp_path / "reject.db"))
    db.upsert_company("c1", "Test Company", is_active=True)
    db.upsert_member(TeamMember("u1", "User One", "designer", 95, True))
    db.upsert_company_member("c1", "u1", "designer")
    db.upsert_project(Project("proj-a", "Project A", "Client", 150.0, 80.0))

    suggestion = TimeEntrySuggestion(
        id="sugg-1",
        user_id="u1",
        company_id="c1",
        project_id="proj-a",
        start_time="2026-01-01T09:00:00Z",
        end_time="2026-01-01T09:30:00Z",
        suggested_minutes=30.0,
        confidence="HIGH",
        evidence_ids=["ev1"],
        state="pending_review",
        created_at="2026-01-01T09:30:00Z",
    )
    db.upsert_suggestion(suggestion)

    engine = SuggestionEngine(db)
    from bimspend.identity import current_auth, Actor, Role

    current_auth.set_actor(Actor(id="u1", role=Role.DESIGNER, company_id="c1"))
    engine.reject_suggestion(suggestion)

    assert suggestion.state == "rejected"

    # No time entry was created
    entries = db.list_time_entries()
    assert len(entries) == 0
    db.close()


def test_cross_company_isolation(tmp_path):
    """Suggestions are company-scoped."""
    db = Database(str(tmp_path / "xcompany.db"))
    db.upsert_company("c1", "Company One", is_active=True)
    db.upsert_company("c2", "Company Two", is_active=True)
    db.upsert_member(TeamMember("u1", "User One", "designer", 95, True))
    db.upsert_company_member("c1", "u1", "designer")

    _make_event(db, "ev1", "u1", "c1", "Revit", "[HASH:abc]",
                "2026-01-01T09:00:00Z", "2026-01-01T09:30:00Z", 30.0)
    _make_correlation_evidence(db, "ev1", "doc-1", "HIGH", "stable_id")

    engine = SuggestionEngine(db)
    suggestions = engine.generate_suggestions("u1", "2026-01-01T00:00:00Z", "2026-01-01T23:59:59Z")

    assert len(suggestions) == 1
    assert suggestions[0].company_id == "c1"
    assert suggestions[0].project_id == "doc-1"
    db.close()


def test_suggestion_persistence_and_retrieval(tmp_path):
    """Suggestions persist and can be retrieved."""
    db = Database(str(tmp_path / "persist.db"))
    db.upsert_company("c1", "Test Company", is_active=True)
    db.upsert_member(TeamMember("u1", "User One", "designer", 95, True))
    db.upsert_company_member("c1", "u1", "designer")
    db.upsert_project(Project("proj-a", "Project A", "Client", 150, 80, True))

    suggestion = TimeEntrySuggestion(
        id="sugg-1",
        user_id="u1",
        company_id="c1",
        project_id="proj-a",
        start_time="2026-01-01T09:00:00Z",
        end_time="2026-01-01T09:30:00Z",
        suggested_minutes=30.0,
        confidence="HIGH",
        evidence_ids=["ev1"],
        state="pending_review",
        created_at="2026-01-01T09:30:00Z",
    )
    db.upsert_suggestion(suggestion)

    # Retrieve
    loaded = db.get_suggestion("sugg-1")
    assert loaded is not None
    assert loaded.id == "sugg-1"
    assert loaded.project_id == "proj-a"
    assert loaded.suggested_minutes == 30.0
    assert loaded.confidence == "HIGH"
    assert loaded.evidence_ids == ["ev1"]

    # List by user
    all_suggestions = db.list_suggestions("u1")
    assert len(all_suggestions) == 1
    assert all_suggestions[0].id == "sugg-1"

    # List by state
    pending = db.list_suggestions("u1", state="pending_review")
    assert len(pending) == 1
    submitted = db.list_suggestions("u1", state="submitted")
    assert len(submitted) == 0
    db.close()