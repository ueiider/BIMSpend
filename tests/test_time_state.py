"""Test time-state separation.

Verifies that observed activity, attributed time, approved time and
billed hours are stored as separate records and that designer review
moves entries through pending_review -> approved/rejected without
auto-invoicing.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bimspend.db import Database  # noqa: E402
from bimspend.identity import Actor, Role, current_auth
from bimspend.models import (  # noqa: E402
    ActivityEvent,
    AttributedTime,
    Project,
    TimeEntry,
    TimeEntryState,
)
from bimspend.review import (  # noqa: E402
    approve_entry,
    bill_entry,
    reject_entry,
    submit_entry,
    suggest_entry,
)


def _set_actor(user_id: str, role: Role, company_id: str | None = None):
    current_auth.clear()
    current_auth.set_actor(Actor(id=user_id, role=role, company_id=company_id or "c1"))


_SCRATCH_DB = "test_bimspend_scratch.db"


def _fresh_db():
    if os.path.exists(_SCRATCH_DB):
        os.remove(_SCRATCH_DB)
    return Database(_SCRATCH_DB)


def test_observed_vs_attributed_vs_approved_are_separate():
    db = _fresh_db()
    try:
        project = Project(
            id="proj_1",
            name="Sprinkler Design",
            client="Northshore",
            standard_rate=150.0,
            loaded_cost_rate=85.0,
        )
        db.upsert_project(project)

        # Observed activity event (120 minutes).
        event = ActivityEvent(
            id="evt_1",
            source="activitywatch",
            external_id="aw_1",
            user_id="designer_01",
            app_name="Revit",
            window_title="Sprinkler Design - Autodesk Revit",
            started_at="2026-10-05T09:00:00Z",
            ended_at="2026-10-05T11:00:00Z",
            duration_minutes=120.0,
            is_afk=False,
        )
        assert db.ingest_event(event) is True
        observed = db.list_events()[0]
        assert observed.duration_minutes == 120.0

        # Attributed time (correlated suggestion, 110 minutes).
        attributed = AttributedTime(
            id="att_1",
            activity_event_id="evt_1",
            project_id="proj_1",
            attributed_minutes=110.0,
            confidence=0.85,
            correlation_method="window_title_match",
        )
        db.upsert_attributed_time(attributed)
        stored_att = db.list_attributed_time()[0]
        assert stored_att.attributed_minutes == 110.0

        # Approved time entry: designer reviews suggested 110 minutes and
        # adjusts down to 100 (designer modifies, not auto-accepted).
        # Workflow: pending_review -> submitted (designer) -> approved (manager)
        db.upsert_attributed_time(attributed)  # persist before FK reference
        entry = suggest_entry(attributed, project, "designer_01")
        entry.minutes = 100.0  # designer modifies suggested hours
        _set_actor("designer_01", Role.DESIGNER)
        submit_entry(entry)
        db.upsert_time_entry(entry)
        _set_actor("manager_01", Role.MANAGER)
        approve_entry(entry)
        db.upsert_time_entry(entry)
        # Billing is a SEPARATE explicit action — NOT automatic
        bill_entry(entry, billed_minutes=80.0)
        db.upsert_time_entry(entry)
        stored_entry = db.get_time_entry(entry.id)
        assert stored_entry.state == TimeEntryState.BILLED
        assert stored_entry.minutes == 100.0
        assert stored_entry.billed_minutes == 80.0

        # Separation: observed (120) != attributed (110) != approved (100)
        # != billed (80).
        assert observed.duration_minutes != stored_att.attributed_minutes
        assert stored_att.attributed_minutes != stored_entry.minutes
        assert stored_entry.minutes != stored_entry.billed_minutes

        # Rejected entries don't contribute to approved/billed.
        entry2 = suggest_entry(attributed, project, "designer_01")
        _set_actor("designer_01", Role.DESIGNER)
        reject_entry(entry2)
        db.upsert_time_entry(entry2)
        assert db.get_time_entry(entry2.id).state == TimeEntryState.REJECTED
        assert db.get_time_entry(entry2.id).billed_minutes == 0.0
    finally:
        db.close()
        if os.path.exists(_SCRATCH_DB):
            os.remove(_SCRATCH_DB)


def test_pending_entries_are_not_auto_invoiced():
    db = _fresh_db()
    try:
        project = Project(
            id="proj_1",
            name="Project",
            client="Client",
            standard_rate=100.0,
            loaded_cost_rate=60.0,
        )
        db.upsert_project(project)

        # Insert the observed activity event first (attributed_time.event_id
        # references activity_events.id).
        event = ActivityEvent(
            id="evt_1",
            source="activitywatch",
            external_id="aw_1",
            user_id="designer_01",
            app_name="Revit",
            window_title="Project - Autodesk Revit",
            started_at="2026-10-05T09:00:00Z",
            ended_at="2026-10-05T10:00:00Z",
            duration_minutes=60.0,
            is_afk=False,
        )
        db.ingest_event(event)
        attributed = AttributedTime(
            id="att_1",
            activity_event_id="evt_1",
            project_id="proj_1",
            attributed_minutes=60.0,
            confidence=0.9,
            correlation_method="window_title_match",
        )
        db.upsert_attributed_time(attributed)  # persist before FK reference
        entry = suggest_entry(attributed, project, "designer_01")
        db.upsert_time_entry(entry)

        stored = db.get_time_entry(entry.id)
        assert stored.state == TimeEntryState.PENDING_REVIEW
        assert stored.billed_minutes == 0.0  # not billed until approved
    finally:
        db.close()
        if os.path.exists(_SCRATCH_DB):
            os.remove(_SCRATCH_DB)


def test_labor_cost_and_standard_value_are_separate():
    db = _fresh_db()
    try:
        project = Project(
            id="proj_1",
            name="Project",
            client="Client",
            standard_rate=150.0,
            loaded_cost_rate=85.0,
        )
        db.upsert_project(project)

        # Insert the observed activity event first (attributed_time.event_id
        # references activity_events.id).
        event = ActivityEvent(
            id="evt_1",
            source="activitywatch",
            external_id="aw_1",
            user_id="designer_01",
            app_name="Revit",
            window_title="Project - Autodesk Revit",
            started_at="2026-10-05T09:00:00Z",
            ended_at="2026-10-05T11:00:00Z",
            duration_minutes=120.0,
            is_afk=False,
        )
        db.ingest_event(event)
        attributed = AttributedTime(
            id="att_1",
            activity_event_id="evt_1",
            project_id="proj_1",
            attributed_minutes=120.0,
            confidence=0.9,
            correlation_method="window_title_match",
        )
        db.upsert_attributed_time(attributed)  # persist before FK reference
        entry = suggest_entry(attributed, project, "designer_01")
        _set_actor("designer_01", Role.DESIGNER)
        submit_entry(entry)
        db.upsert_time_entry(entry)
        _set_actor("manager_01", Role.MANAGER)
        approve_entry(entry)
        db.upsert_time_entry(entry)

        stored = db.get_time_entry(entry.id)
        # 120 minutes = 2 hours.
        # labor_cost = 2 * 85 = 170; standard_value = 2 * 150 = 300.
        assert abs(stored.labor_cost - 170.0) < 0.01
        assert abs(stored.standard_value - 300.0) < 0.01
        assert stored.labor_cost != stored.standard_value  # not the same metric
    finally:
        db.close()
        if os.path.exists(_SCRATCH_DB):
            os.remove(_SCRATCH_DB)