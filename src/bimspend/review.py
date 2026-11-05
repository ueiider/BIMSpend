"""Designer review workflow.

Converts attributed time into reviewed time entries with explicit
pending_review / approved / rejected states. The designer (user) reviews
suggested hours before they become billable/cost-relevant.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bimspend.models import Project, TimeEntry, TimeEntryState
from bimspend.adapters.base import ReviewAdapter


def suggest_entry(
    attributed: AttributedTime,
    project: Project,
    user_id: str,
) -> TimeEntry:
    """Build a pending-review time entry from an attributed-time record.

    Snapshots the project's standard and loaded rates at review time so
    the entry is self-contained.
    """
    from datetime import datetime as _dt

    now = _dt.now().isoformat()
    return TimeEntry(
        id=f"entry_{attributed.id}",
        attributed_time_id=attributed.id,
        project_id=project.id,
        user_id=user_id,
        minutes=attributed.attributed_minutes,
        state=TimeEntryState.PENDING_REVIEW,
        standard_rate=project.standard_rate,
        loaded_cost_rate=project.loaded_cost_rate,
        billed_minutes=0.0,  # not invoiced until approved/billed separately
        review_notes=None,
        reviewed_by=None,
        reviewed_at=None,
        created_at=now,
    )


def approve_entry(
    entry: TimeEntry,
    reviewed_by: str,
    notes: str | None = None,
    billed_minutes: float | None = None,
) -> TimeEntry:
    """Approve a time entry. Billed minutes default to reviewed minutes
    unless overridden (actual hours != invoiced hours is allowed)."""
    from datetime import datetime as _dt

    now = _dt.now().isoformat()
    entry.state = TimeEntryState.APPROVED
    entry.reviewed_by = reviewed_by
    entry.reviewed_at = now
    entry.review_notes = notes
    if billed_minutes is not None:
        entry.billed_minutes = billed_minutes
    else:
        entry.billed_minutes = entry.minutes
    return entry


def reject_entry(
    entry: TimeEntry,
    reviewed_by: str,
    notes: str | None = None,
) -> TimeEntry:
    """Reject a time entry (designer disputes the suggested hours)."""
    from datetime import datetime as _dt

    now = _dt.now().isoformat()
    entry.state = TimeEntryState.REJECTED
    entry.reviewed_by = reviewed_by
    entry.reviewed_at = now
    entry.review_notes = notes
    entry.billed_minutes = 0.0
    return entry


class InMemoryReviewAdapter:
    """In-memory implementation of ReviewAdapter (for the vertical slice)."""

    def __init__(self) -> None:
        self._decisions: list[dict[str, Any]] = []

    def decide(
        self,
        entry_id: str,
        state: str,
        reviewed_by: str,
        notes: str | None = None,
    ) -> None:
        self._decisions.append(
            {
                "entry_id": entry_id,
                "state": state,
                "reviewed_by": reviewed_by,
                "notes": notes,
                "at": datetime.now().isoformat(),
            }
        )
