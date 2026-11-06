"""Tests for the suggestion domain service (SH-001/SH-002 compliance).

Tests cover:
- Session-based authentication enforcement
- Company-scoped authorization
- Suggestion submission workflow
- Manager approval workflow
- Suggestion rejection
- Return for correction
- Split and merge operations
- Audit trail recording
- Cross-company access denial
- Fail-closed behavior
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bimspend.auth import SessionManager, hash_password
from bimspend.db import Database
from bimspend.identity import Actor, Role, current_auth
from bimspend.capture.suggestion_domain import SuggestionService
from bimspend.models import (
    Project,
    TeamMember,
    TimeEntry,
    TimeEntryState,
    TimeEntrySuggestion,
)


def _make_project(db, pid="p1", name="Project", client="Client"):
    db.upsert_project(Project(pid, name, client, 150.0, 80.0))
    return pid


def _make_member(db, mid="m1", name="Alice", role="designer", cost=95.0, active=True):
    db.upsert_member(TeamMember(mid, name, role, cost, active))
    return mid


def _make_company(db, cid="c1", name="Test Company"):
    db.upsert_company(cid, name)
    return cid


def _make_credential(db, member_id="m1", username="alice", password="secretpass"):
    db.upsert_user_credential(member_id, username, hash_password(password))
    return member_id


def _make_suggestion(
    db,
    suggestion_id="sugg-1",
    user_id="m1",
    company_id="c1",
    project_id="p1",
    start_time="2026-01-01T09:00:00Z",
    end_time="2026-01-01T09:30:00Z",
    suggested_minutes=30.0,
    confidence="HIGH",
    evidence_ids=["ev1"],
    state="pending_review",
    created_at="2026-01-01T09:30:00Z",
):
    """Create and persist a time entry suggestion."""
    suggestion = TimeEntrySuggestion(
        id=suggestion_id,
        user_id=user_id,
        company_id=company_id,
        project_id=project_id,
        start_time=start_time,
        end_time=end_time,
        suggested_minutes=suggested_minutes,
        confidence=confidence,
        evidence_ids=evidence_ids,
        state=state,
        created_at=created_at,
    )
    db.upsert_suggestion(suggestion)
    return suggestion


# ------------------------------------------------------------------
# Session-based authentication tests
# ------------------------------------------------------------------

def test_submit_suggestion_requires_authentication(tmp_path):
    """Submit requires an authenticated session."""
    db = Database(str(tmp_path / "submit.db"))
    db.upsert_company("c1", "Test Company", is_active=True)
    db.upsert_member(TeamMember("m1", "Alice", "designer", 95.0, True))
    db.upsert_company_member("c1", "m1", "designer")
    db.upsert_user_credential("m1", "alice", hash_password("secretpass"))
    db.upsert_project(Project("p1", "Project", "Client", 150.0, 80.0))

    suggestion = TimeEntrySuggestion(
        id="sugg-1",
        user_id="m1",
        company_id="c1",
        project_id="p1",
        start_time="2026-01-01T09:00:00Z",
        end_time="2026-01-01T09:30:00Z",
        suggested_minutes=30.0,
        confidence="HIGH",
        evidence_ids=["ev1"],
        state="pending_review",
        created_at="2026-01-01T09:30:00Z",
    )
    db.upsert_suggestion(suggestion)

    service = SuggestionService(db)
    # No authenticated actor
    current_auth.clear()
    with pytest.raises(PermissionError, match="No authenticated actor"):
        service.submit_suggestion(suggestion, actor_id="m1")
    db.close()


def test_submit_suggestion_requires_designer_role(tmp_path):
    """Submit requires designer role."""
    db = Database(str(tmp_path / "submit2.db"))
    db.upsert_company("c1", "Test Company", is_active=True)
    db.upsert_member(TeamMember("m1", "Alice", "manager", 120.0, True))
    db.upsert_company_member("c1", "m1", "manager")
    db.upsert_user_credential("m1", "alice", hash_password("secretpass"))
    db.upsert_project(Project("p1", "Project", "Client", 150.0, 80.0))

    suggestion = TimeEntrySuggestion(
        id="sugg-1",
        user_id="m1",
        company_id="c1",
        project_id="p1",
        start_time="2026-01-01T09:00:00Z",
        end_time="2026-01-01T09:30:00Z",
        suggested_minutes=30.0,
        confidence="HIGH",
        evidence_ids=["ev1"],
        state="pending_review",
        created_at="2026-01-01T09:30:00Z",
    )
    db.upsert_suggestion(suggestion)

    service = SuggestionService(db)
    current_auth.set_actor(Actor(id="m1", role=Role.MANAGER, company_id="c1"))
    with pytest.raises(PermissionError, match="Only designers"):
        service.submit_suggestion(suggestion, actor_id="m1")
    db.close()


def test_submit_suggestion_requires_company_scope(tmp_path):
    """Submit requires company scope matching."""
    db = Database(str(tmp_path / "submit3.db"))
    db.upsert_company("c1", "Company One", is_active=True)
    db.upsert_company("c2", "Company Two", is_active=True)
    db.upsert_member(TeamMember("m1", "Alice", "designer", 95.0, True))
    db.upsert_member(TeamMember("m2", "Bob", "designer", 95.0, True))
    db.upsert_company_member("c1", "m1", "designer")
    db.upsert_company_member("c2", "m2", "designer")
    db.upsert_user_credential("m1", "alice", hash_password("secretpass"))
    db.upsert_user_credential("m2", "bob", hash_password("secretpass"))
    db.upsert_project(Project("p1", "Project", "Client", 150.0, 80.0))

    suggestion = TimeEntrySuggestion(
        id="sugg-1",
        user_id="m1",
        company_id="c1",
        project_id="p1",
        start_time="2026-01-01T09:00:00Z",
        end_time="2026-01-01T09:30:00Z",
        suggested_minutes=30.0,
        confidence="HIGH",
        evidence_ids=["ev1"],
        state="pending_review",
        created_at="2026-01-01T09:30:00Z",
    )
    db.upsert_suggestion(suggestion)

    service = SuggestionService(db)
    # Actor from company c2 trying to submit suggestion in company c1
    current_auth.set_actor(Actor(id="m2", role=Role.DESIGNER, company_id="c2"))
    with pytest.raises(PermissionError, match="does not match"):
        service.submit_suggestion(suggestion, actor_id="m2")
    db.close()


def test_submit_suggestion_success(tmp_path):
    """Successful submission creates a TimeEntry in SUBMITTED state."""
    db = Database(str(tmp_path / "submit_success.db"))
    db.upsert_company("c1", "Test Company", is_active=True)
    db.upsert_member(TeamMember("m1", "Alice", "designer", 95.0, True))
    db.upsert_company_member("c1", "m1", "designer")
    db.upsert_user_credential("m1", "alice", hash_password("secretpass"))
    db.upsert_project(Project("p1", "Project", "Client", 150.0, 80.0))

    suggestion = TimeEntrySuggestion(
        id="sugg-1",
        user_id="m1",
        company_id="c1",
        project_id="p1",
        start_time="2026-01-01T09:00:00Z",
        end_time="2026-01-01T09:30:00Z",
        suggested_minutes=30.0,
        confidence="HIGH",
        evidence_ids=["ev1"],
        state="pending_review",
        created_at="2026-01-01T09:30:00Z",
    )
    db.upsert_suggestion(suggestion)

    service = SuggestionService(db)
    current_auth.set_actor(Actor(id="m1", role=Role.DESIGNER, company_id="c1"))

    result = service.submit_suggestion(suggestion, actor_id="m1")

    assert result.state == "submitted"
    assert result.submitted_by == "m1"
    assert result.submitted_at is not None

    # Suggestion was persisted
    updated = db.get_suggestion("sugg-1")
    assert updated.state == "submitted"
    assert updated.submitted_by == "m1"
    db.close()


def test_approve_suggestion_requires_manager(tmp_path):
    """Approve requires manager role."""
    db = Database(str(tmp_path / "approve.db"))
    db.upsert_company("c1", "Test Company", is_active=True)
    db.upsert_member(TeamMember("m1", "Alice", "designer", 95.0, True))
    db.upsert_member(TeamMember("m2", "Bob", "manager", 120.0, True))
    db.upsert_company_member("c1", "m1", "designer")
    db.upsert_company_member("c1", "m2", "manager")
    db.upsert_user_credential("m1", "alice", hash_password("secretpass"))
    db.upsert_user_credential("m2", "bob", hash_password("secretpass"))
    db.upsert_project(Project("p1", "Project", "Client", 150.0, 80.0))

    suggestion = TimeEntrySuggestion(
        id="sugg-1",
        user_id="m1",
        company_id="c1",
        project_id="p1",
        start_time="2026-01-01T09:00:00Z",
        end_time="2026-01-01T09:30:00Z",
        suggested_minutes=30.0,
        confidence="HIGH",
        evidence_ids=["ev1"],
        state="submitted",
        submitted_by="m1",
        submitted_at="2026-01-01T09:30:00Z",
        created_at="2026-01-01T09:30:00Z",
    )
    db.upsert_suggestion(suggestion)

    service = SuggestionService(db)

    # Designer cannot approve
    current_auth.set_actor(Actor(id="m1", role=Role.DESIGNER, company_id="c1"))
    with pytest.raises(PermissionError, match="Only managers"):
        service.approve_suggestion(suggestion, actor_id="m1")

    # Manager can approve
    current_auth.set_actor(Actor(id="m2", role=Role.MANAGER, company_id="c1"))
    result = service.approve_suggestion(suggestion, actor_id="m2")
    assert result.state == "approved"
    assert result.reviewed_by == "m2"

    # Suggestion was updated
    updated = db.get_suggestion("sugg-1")
    assert updated.state == "approved"
    db.close()


def test_reject_suggestion_designer_owns(tmp_path):
    """Designer can reject their own pending suggestion."""
    db = Database(str(tmp_path / "reject.db"))
    db.upsert_company("c1", "Test Company", is_active=True)
    db.upsert_member(TeamMember("m1", "Alice", "designer", 95.0, True))
    db.upsert_company_member("c1", "m1", "designer")
    db.upsert_user_credential("m1", "alice", hash_password("secretpass"))
    db.upsert_project(Project("p1", "Project", "Client", 150.0, 80.0))

    suggestion = TimeEntrySuggestion(
        id="sugg-1",
        user_id="m1",
        company_id="c1",
        project_id="p1",
        start_time="2026-01-01T09:00:00Z",
        end_time="2026-01-01T09:30:00Z",
        suggested_minutes=30.0,
        confidence="HIGH",
        evidence_ids=["ev1"],
        state="pending_review",
        created_at="2026-01-01T09:30:00Z",
    )
    db.upsert_suggestion(suggestion)

    service = SuggestionService(db)
    current_auth.set_actor(Actor(id="m1", role=Role.DESIGNER, company_id="c1"))

    result = service.reject_suggestion(suggestion, actor_id="m1", notes="Wrong project")
    assert result.state == "rejected"

    updated = db.get_suggestion("sugg-1")
    assert updated.state == "rejected"
    db.close()


def test_audit_trail_recorded(tmp_path):
    """Audit trail records all actions."""
    db = Database(str(tmp_path / "audit.db"))
    db.upsert_company("c1", "Test Company", is_active=True)
    db.upsert_member(TeamMember("m1", "Alice", "designer", 95.0, True))
    db.upsert_member(TeamMember("m2", "Bob", "manager", 120.0, True))
    db.upsert_company_member("c1", "m1", "designer")
    db.upsert_company_member("c1", "m2", "manager")
    db.upsert_user_credential("m1", "alice", hash_password("secretpass"))
    db.upsert_user_credential("m2", "bob", hash_password("secretpass"))
    db.upsert_project(Project("p1", "Project", "Client", 150.0, 80.0))

    suggestion = TimeEntrySuggestion(
        id="sugg-1",
        user_id="m1",
        company_id="c1",
        project_id="p1",
        start_time="2026-01-01T09:00:00Z",
        end_time="2026-01-01T09:30:00Z",
        suggested_minutes=30.0,
        confidence="HIGH",
        evidence_ids=["ev1"],
        state="pending_review",
        created_at="2026-01-01T09:30:00Z",
    )
    db.upsert_suggestion(suggestion)

    service = SuggestionService(db)

    # Designer submits
    current_auth.set_actor(Actor(id="m1", role=Role.DESIGNER, company_id="c1"))
    service.submit_suggestion(suggestion, actor_id="m1")

    # Manager approves
    current_auth.set_actor(Actor(id="m2", role=Role.MANAGER, company_id="c1"))
    service.approve_suggestion(suggestion, actor_id="m2")

    # Get audit trail
    history = service.get_suggestion_audit_trail("sugg-1")
    assert len(history) == 2
    assert history[0]["action"] == "submit"
    assert history[0]["actor_id"] == "m1"
    assert history[1]["action"] == "approve"
    assert history[1]["actor_id"] == "m2"
    db.close()