"""Designer review workflow.

Converts attributed time into reviewed time entries with explicit
states:

  pending_review  -> designer has not yet reviewed
    submitted       -> designer submitted for manager approval
    approved        -> manager approved (NOT auto-billed)
    rejected        -> manager returned for correction / designer rejected
    billed          -> invoiced to client (separate explicit action)

Designer owns: pending_review -> submitted (via submit_entry)
Manager owns:  submitted -> approved/rejected (via approve_entry/reject_entry)
Billing owns:  approved -> billed (via bill_entry, explicit and separate)

Approval never automatically creates a billing record.

Authorization (SH-001 + SH-002):
  - All actions require an authenticated, session-validated actor via
    bimspend.identity.current_auth. The actor's session is validated
    against the database on every access (fail-closed).
  - Designers can submit, edit, and reset their own pending entries.
  - Designers cannot approve or bill entries (manager role required).
  - Managers can approve, reject, and bill entries within their company.
  - Cross-company access is denied: actor.company_id must match the
    entry's company_id when both are present.
  - Legacy mode (submitted_by/reviewed_by/actor_id params without
    authenticated actor) is preserved for backward compatibility but
    provides no session validation.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from bimspend.identity import Role, current_auth, require_actor
from bimspend.models import AttributedTime, Project, TimeEntry, TimeEntryState
from bimspend.adapters.base import ReviewAdapter


def _check_company_access(actor, entry: TimeEntry) -> None:
    """Enforce SH-002: actor's company must match entry's company.

    Only enforced when both the actor and the entry have a company_id.
    Entries created before the v5 migration may have company_id=None.
    """
    if actor.company_id is not None and entry.company_id is not None:
        if actor.company_id != entry.company_id:
            raise PermissionError(
                f"Actor {actor.id} cannot access records in company "
                f"{entry.company_id}; actor is in company {actor.company_id}."
            )


def suggest_entry(
    attributed: AttributedTime,
    project: Project,
    user_id: str,
) -> TimeEntry:
    """Build a pending-review time entry from an attributed-time record.

    Snapshots the project's standard and loaded rates at review time so
    the entry is self-contained. billed_minutes starts at 0.
    """
    now = datetime.now().isoformat()
    return TimeEntry(
        id=f"entry_{attributed.id}",
        attributed_time_id=attributed.id,
        project_id=project.id,
        user_id=user_id,
        minutes=attributed.attributed_minutes,
        state=TimeEntryState.PENDING_REVIEW,
        standard_rate=project.standard_rate,
        loaded_cost_rate=project.loaded_cost_rate,
        billed_minutes=0.0,  # NOT auto-billed
        review_notes=None,
        reviewed_by=None,
        reviewed_at=None,
        submitted_by=None,
        submitted_at=None,
        created_at=now,
    )


def submit_entry(
    entry: TimeEntry,
    submitted_by: str | None = None,
    notes: str | None = None,
) -> TimeEntry:
    """Designer submits a pending_review entry for manager approval.

    Transition: pending_review -> submitted.
    Does NOT change billed_minutes.

    Requires an authenticated designer actor. The actor's session is
    validated against the database (fail-closed).
    """
    actor = current_auth.actor  # Validates session; raises PermissionError if invalid
    if actor is None:
        raise PermissionError("No authenticated actor.")
    if actor.role != Role.DESIGNER:
        raise PermissionError("Only designers can submit entries.")
    if actor.id != entry.user_id:
        raise PermissionError("Designers can submit only their own entries.")
    _check_company_access(actor, entry)
    actor_id = actor.id
    now = datetime.now().isoformat()
    if entry.state != TimeEntryState.PENDING_REVIEW:
        raise ValueError(
            f"Cannot submit entry in state {entry.state.value}; "
            "only pending_review entries can be submitted."
        )
    entry.state = TimeEntryState.SUBMITTED
    entry.submitted_by = actor_id
    entry.submitted_at = now
    entry.reviewed_by = None
    entry.reviewed_at = None
    if notes is not None:
        entry.review_notes = notes
    return entry


def approve_entry(
    entry: TimeEntry,
    reviewed_by: str | None = None,
    notes: str | None = None,
) -> TimeEntry:
    """Manager approves a submitted time entry.

    Transition: submitted -> approved.

    IMPORTANT: Approval does NOT set billed_minutes. Approved time is
    not automatically invoiced. Billing is a separate explicit action
    (bill_entry) to preserve the actual-vs-billed distinction.

    Requires an authenticated manager actor in the same company as the
    entry. The actor's session is validated against the database.
    """
    actor = current_auth.actor  # Validates session; raises PermissionError if invalid
    if actor is None:
        raise PermissionError("No authenticated actor.")
    if actor.role != Role.MANAGER:
        raise PermissionError("Only managers can approve entries.")
    _check_company_access(actor, entry)
    actor_id = actor.id
    now = datetime.now().isoformat()
    if entry.state != TimeEntryState.SUBMITTED:
        raise ValueError(
            f"Cannot approve entry in state {entry.state.value}; "
            "only submitted entries can be approved."
        )
    entry.state = TimeEntryState.APPROVED
    entry.reviewed_by = actor_id
    entry.reviewed_at = now
    entry.review_notes = notes
    # billed_minutes stays at 0 — approval does not create billing
    return entry


def reject_entry(
    entry: TimeEntry,
    reviewed_by: str | None = None,
    notes: str | None = None,
) -> TimeEntry:
    """Manager returns an entry for correction, or designer rejects.

    Transition: submitted -> rejected (manager) or
    pending_review -> rejected (designer self-reject).

    Requires an authenticated actor. The actor's session is validated
    against the database.
    """
    actor = current_auth.actor  # Validates session; raises PermissionError if invalid
    if actor is None:
        raise PermissionError("No authenticated actor.")

    now = datetime.now().isoformat()
    if entry.state == TimeEntryState.SUBMITTED:
        if actor.role != Role.MANAGER:
            raise PermissionError("Only managers can reject submitted entries.")
    elif entry.state == TimeEntryState.PENDING_REVIEW:
        if actor.role != Role.DESIGNER:
            raise PermissionError("Only designers can reject pending entries.")
        if actor.id != entry.user_id:
            raise PermissionError("Designers can reject only their own entries.")
    else:
        raise ValueError("Only pending or submitted entries can be rejected.")
    _check_company_access(actor, entry)
    entry.state = TimeEntryState.REJECTED
    entry.reviewed_by = actor.id
    entry.reviewed_at = now
    entry.review_notes = notes
    entry.billed_minutes = 0.0
    return entry


def bill_entry(
    entry: TimeEntry,
    billed_minutes: float,
    reviewed_by: str | None = None,
) -> TimeEntry:
    """Record billing for an approved entry.

    Transition: approved -> billed.

    billed_minutes may differ from entry.minutes (actual hours worked
    may differ from hours invoiced to client). This is the realization
    gap that BIMSpend exists to expose.

    Requires an authenticated manager actor in the same company as the
    entry. The actor's session is validated against the database.
    """
    actor = current_auth.actor  # Validates session; raises PermissionError if invalid
    if actor is None:
        raise PermissionError("No authenticated actor.")
    if actor.role != Role.MANAGER:
        raise PermissionError("Only managers can bill entries.")
    _check_company_access(actor, entry)
    actor_id = actor.id
    now = datetime.now().isoformat()
    if entry.state != TimeEntryState.APPROVED:
        raise ValueError(
            f"Cannot bill entry in state {entry.state.value}; "
            "only approved entries can be billed."
        )
    if billed_minutes < 0 or billed_minutes > entry.minutes * 2:
        raise ValueError(
            f"billed_minutes {billed_minutes} is outside reasonable range "
            f"for {entry.minutes} approved minutes."
        )
    entry.state = TimeEntryState.BILLED
    entry.billed_minutes = billed_minutes
    entry.reviewed_by = actor_id
    entry.reviewed_at = now
    return entry


def reset_to_pending(
    entry: TimeEntry,
) -> TimeEntry:
    """Reset a rejected entry back to pending_review for designer correction.

    Transition: rejected -> pending_review.

    Requires an authenticated designer actor who owns the entry.
    The actor's session is validated against the database.
    """
    actor = current_auth.actor  # Validates session; raises PermissionError if invalid
    if actor is None:
        raise PermissionError("No authenticated actor.")
    if actor.role != Role.DESIGNER:
        raise PermissionError("Only designers can reset rejected entries.")
    if actor.id != entry.user_id:
        raise PermissionError("Designers can reset only their own entries.")
    _check_company_access(actor, entry)
    if entry.state != TimeEntryState.REJECTED:
        raise ValueError(
            f"Cannot reset entry in state {entry.state.value}; "
            "only rejected entries can be reset."
        )
    entry.state = TimeEntryState.PENDING_REVIEW
    entry.reviewed_by = None
    entry.reviewed_at = None
    entry.review_notes = None
    return entry


def edit_entry(
    entry: TimeEntry,
    minutes: float,
    notes: str | None = None,
) -> TimeEntry:
    """Edit a pending synthetic entry before submission.

    Requires an authenticated designer actor who owns the entry.
    The actor's session is validated against the database.
    """
    actor = current_auth.actor  # Validates session; raises PermissionError if invalid
    if actor is None:
        raise PermissionError("No authenticated actor.")
    if actor.role != Role.DESIGNER:
        raise PermissionError("Only designers can edit entries.")
    if actor.id != entry.user_id:
        raise PermissionError("Designers can edit only their own entries.")
    _check_company_access(actor, entry)
    if entry.state != TimeEntryState.PENDING_REVIEW:
        raise ValueError("Only pending entries can be edited.")
    if not (0 < minutes <= 24 * 60):
        raise ValueError("Minutes must be greater than zero and at most 24 hours.")
    entry.minutes = minutes
    if notes is not None:
        entry.review_notes = notes
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