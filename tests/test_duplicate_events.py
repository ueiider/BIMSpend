"""Test idempotent activity-event ingestion.

Duplicate events (same source + external_id) must not create duplicate
records. This mirrors the idempotency gap identified in Miru's agent
ingestion endpoint (no uniqueness constraint on external_run_id /
external_session_id) — BIMSpend's adapter layer enforces it at the
database level.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bimspend.db import Database  # noqa: E402
from bimspend.models import ActivityEvent  # noqa: E402


_SCRATCH_DB = "test_bimspend_scratch.db"


def _fresh_db():
    if os.path.exists(_SCRATCH_DB):
        os.remove(_SCRATCH_DB)
    return Database(_SCRATCH_DB)


def test_duplicate_event_is_ignored():
    db = _fresh_db()
    try:
        event = ActivityEvent(
            id="evt_1",
            source="activitywatch",
            external_id="aw_dup_1",
            user_id="designer_01",
            app_name="Revit",
            window_title="Project - Autodesk Revit",
            started_at="2026-10-05T09:00:00Z",
            ended_at="2026-10-05T10:00:00Z",
            duration_minutes=60.0,
            is_afk=False,
        )

        # First insert succeeds.
        assert db.ingest_event(event) is True
        assert len(db.list_events()) == 1

        # Same source + external_id = duplicate, ignored (idempotent).
        assert db.ingest_event(event) is False
        assert len(db.list_events()) == 1

        # Different external_id with same source = NOT a duplicate.
        event2 = ActivityEvent(
            id="evt_2",
            source="activitywatch",
            external_id="aw_dup_2",
            user_id="designer_01",
            app_name="Revit",
            window_title="Project - Autodesk Revit",
            started_at="2026-10-05T10:00:00Z",
            ended_at="2026-10-05T11:00:00Z",
            duration_minutes=60.0,
            is_afk=False,
        )
        assert db.ingest_event(event2) is True
        assert len(db.list_events()) == 2

        # Same external_id with different source = NOT a duplicate.
        event3 = ActivityEvent(
            id="evt_3",
            source="miru",
            external_id="aw_dup_1",
            user_id="designer_01",
            app_name="Revit",
            window_title="Project - Autodesk Revit",
            started_at="2026-10-05T09:00:00Z",
            ended_at="2026-10-05T10:00:00Z",
            duration_minutes=60.0,
            is_afk=False,
        )
        assert db.ingest_event(event3) is True
        assert len(db.list_events()) == 3
    finally:
        db.close()
        if os.path.exists(_SCRATCH_DB):
            os.remove(_SCRATCH_DB)


def test_duplicate_different_duration_still_ignored():
    """Even if the duplicate carries a different duration, the original
    record wins (idempotent key is source+external_id, not full event)."""
    db = _fresh_db()
    try:
        event = ActivityEvent(
            id="evt_1",
            source="activitywatch",
            external_id="aw_dup_1",
            user_id="designer_01",
            app_name="Revit",
            window_title="Project - Autodesk Revit",
            started_at="2026-10-05T09:00:00Z",
            ended_at="2026-10-05T10:00:00Z",
            duration_minutes=60.0,
            is_afk=False,
        )
        assert db.ingest_event(event) is True

        duplicate_with_diff_duration = ActivityEvent(
            id="evt_99",
            source="activitywatch",
            external_id="aw_dup_1",
            user_id="designer_01",
            app_name="Revit",
            window_title="Project - Autodesk Revit",
            started_at="2026-10-05T09:00:00Z",
            ended_at="2026-10-05T12:00:00Z",
            duration_minutes=180.0,
            is_afk=False,
        )
        assert db.ingest_event(duplicate_with_diff_duration) is False
        assert len(db.list_events()) == 1
        assert db.list_events()[0].duration_minutes == 60.0
    finally:
        db.close()
        if os.path.exists(_SCRATCH_DB):
            os.remove(_SCRATCH_DB)
