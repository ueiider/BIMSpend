"""Suggestion session domain service.

Manages the designer review and manager approval lifecycle for time entry
suggestions. All actions require an authenticated, session-validated actor
and enforce company-scoped authorization.

State machine:
  pending_review  -> submitted     (designer submits)
  submitted       -> approved      (manager approves)
  submitted       -> rejected      (manager rejects)
  pending_review  -> rejected      (designer self-rejects)
  rejected        -> pending_review (designer resets/corrects)
  submitted       -> returned_for_correction (manager returns for correction)
  returned_for_correction -> submitted (designer resubmits after correction)

Suggestions are never auto-billed or auto-approved.
"""

from __future__ import annotations

import datetime
import hashlib
import secrets
from typing import Any, Optional

from bimspend.db import Database
from bimspend.identity import Actor, Role, current_auth
from bimspend.models import TimeEntry, TimeEntrySuggestion, TimeEntryState


class SuggestionDomainError(Exception):
    """Raised when a suggestion domain operation fails."""


class SuggestionService:
    """Domain service for suggestion lifecycle management.

    All methods require an authenticated, session-validated actor and
    enforce company-scoped authorization.
    """

    def __init__(self, db: Database):
        self.db = db

    # ------------------------------------------------------------------
    # Submit: pending_review -> submitted
    # ------------------------------------------------------------------

    def submit_suggestion(
        self,
        suggestion: TimeEntrySuggestion,
        actor_id: str | None = None,
        notes: str | None = None,
    ) -> TimeEntrySuggestion:
        """Submit a pending_review suggestion for manager approval.

        Creates a linked TimeEntry in SUBMITTED state and marks the
        suggestion as submitted. Idempotent — submitting an already
        submitted suggestion is a no-op.

        Requires an authenticated designer actor who owns the suggestion.
        """
        actor = self._require_authenticated_actor(actor_id, Role.DESIGNER)

        if suggestion.state != TimeEntrySuggestion.PENDING_REVIEW:
            raise ValueError(
                f"Cannot submit suggestion in state {suggestion.state}; "
                "only pending_review suggestions can be submitted."
            )
        if suggestion.user_id != actor.id:
            raise PermissionError("Designers can submit only their own suggestions.")
        if suggestion.company_id != actor.company_id:
            raise PermissionError(
                f"Suggestion company {suggestion.company_id} does not match "
                f"actor company {actor.company_id}."
            )

        now = datetime.now(timezone.utc).isoformat()

        # Create linked TimeEntry
        entry = TimeEntry(
            id=f"entry-{suggestion.id}",
            attributed_time_id=suggestion.id,
            project_id=suggestion.edited_project_id or suggestion.project_id or "",
            user_id=suggestion.user_id,
            minutes=suggestion.edited_minutes or suggestion.suggested_minutes,
            state=TimeEntryState.SUBMITTED,
            standard_rate=0.0,
            loaded_cost_rate=0.0,
            billed_minutes=0.0,
            review_notes=suggestion.review_notes or notes,
            reviewed_by=None,
            reviewed_at=None,
            submitted_by=actor.id,
            submitted_at=now,
            created_at=now,
            company_id=suggestion.company_id,
        )

        self.db.upsert_time_entry(entry, actor_id=actor.id)

        # Update suggestion
        suggestion.state = TimeEntrySuggestionState.SUBMITTED
        suggestion.submitted_by = actor.id
        suggestion.submitted_at = now
        suggestion.time_entry_id = entry.id

        self.db.upsert_suggestion(suggestion)

        # Record audit
        self._record_decision(
            suggestion_id=suggestion.id,
            actor_id=actor.id,
            actor_company_id=actor.company_id,
            action="submit",
            previous_state="pending_review",
            new_state="submitted",
            previous_minutes=None,
            new_minutes=suggestion.suggested_minutes,
            notes=notes,
        )

        return suggestion

    # ------------------------------------------------------------------
    # Approve: submitted -> approved
    # ------------------------------------------------------------------

    def approve_suggestion(
        self,
        suggestion: TimeEntrySuggestion,
        actor_id: str | None = None,
        notes: str | None = None,
    ) -> TimeEntrySuggestion:
        """Approve a submitted suggestion.

        Manager-only action. Does NOT create billing — billing is a
        separate explicit action.

        Requires an authenticated manager actor in the same company.
        """
        actor = self._require_authenticated_actor(actor_id, Role.MANAGER)

        if suggestion.state != TimeEntrySuggestionState.SUBMITTED:
            raise SuggestionDomainError(
                f"Cannot approve suggestion in state {suggestion.state}; "
                "only submitted suggestions can be approved."
            )
        if suggestion.company_id != actor.company_id:
            raise PermissionError(
                f"Suggestion company {suggestion.company_id} does not match "
                f"actor company {actor.company_id}."
            )

        now = datetime.now(timezone.utc).isoformat()

        suggestion.state = TimeEntrySuggestionState.APPROVED
        suggestion.reviewed_by = actor.id
        suggestion.reviewed_at = now

        self.db.upsert_suggestion(suggestion)

        # Record audit
        self._record_decision(
            suggestion_id=suggestion.id,
            actor_id=actor.id,
            actor_company_id=actor.company_id,
            action="approve",
            previous_state="submitted",
            new_state="approved",
            previous_minutes=None,
            new_minutes=suggestion.suggested_minutes,
            notes=notes,
        )

        return suggestion

    # ------------------------------------------------------------------
    # Reject: submitted -> rejected (manager) or pending_review -> rejected (designer)
    # ------------------------------------------------------------------

    def reject_suggestion(
        self,
        suggestion: TimeEntrySuggestion,
        actor_id: str | None = None,
        notes: str | None = None,
    ) -> TimeEntrySuggestion:
        """Reject a suggestion.

        Designer rejects pending_review suggestions they own.
        Manager rejects submitted suggestions.

        Idempotent — rejecting an already rejected suggestion is a no-op.
        """
        actor = self._require_authenticated_actor(actor_id)

        if suggestion.state == TimeEntrySuggestionState.SUBMITTED:
            if actor.role != Role.MANAGER:
                raise PermissionError("Only managers can reject submitted suggestions.")
        elif suggestion.state == TimeEntrySuggestionState.PENDING_REVIEW:
            if actor.role != Role.DESIGNER:
                raise PermissionError("Only designers can reject pending suggestions.")
            if suggestion.user_id != actor.id:
                raise PermissionError("Designers can reject only their own suggestions.")
        else:
            raise SuggestionDomainError(
                f"Cannot reject suggestion in state {suggestion.state}; "
                "only pending_review or submitted suggestions can be rejected."
            )

        if suggestion.company_id != actor.company_id:
            raise PermissionError(
                f"Suggestion company {suggestion.company_id} does not match "
                f"actor company {actor.company_id}."
            )

        suggestion.state = TimeEntrySuggestionState.REJECTED

        self.db.upsert_suggestion(suggestion)

        self._record_decision(
            suggestion_id=suggestion.id,
            actor_id=actor.id,
            actor_company_id=actor.company_id,
            action="reject",
            previous_state=suggestion.state,
            new_state=TimeEntrySuggestionState.REJECTED,
            previous_minutes=None,
            new_minutes=suggestion.suggested_minutes,
            notes=notes,
        )

        return suggestion

    # ------------------------------------------------------------------
    # Return for correction: submitted -> returned_for_correction (manager)
    # ------------------------------------------------------------------

    def return_for_correction(
        self,
        suggestion: TimeEntrySuggestion,
        actor_id: str | None = None,
        notes: str | None = None,
    ) -> TimeEntrySuggestion:
        """Manager returns a submitted suggestion for correction.

        Requires an authenticated manager actor in the same company.
        """
        actor = self._require_authenticated_actor(actor_id, Role.MANAGER)

        if suggestion.state != TimeEntrySuggestionState.SUBMITTED:
            raise SuggestionDomainError(
                f"Cannot return suggestion in state {suggestion.state}; "
                "only submitted entries can be returned for correction."
            )
        if suggestion.company_id != actor.company_id:
            raise PermissionError(
                f"Suggestion company {suggestion.company_id} does not match "
                f"actor company {actor.company_id}."
            )

        now = datetime.now(timezone.utc).isoformat()

        suggestion.state = TimeEntrySuggestionState.REJECTED
        suggestion.reviewed_by = actor.id
        suggestion.reviewed_at = now
        suggestion.review_notes = notes

        self.db.upsert_suggestion(suggestion)

        self._record_decision(
            suggestion_id=suggestion.id,
            actor_id=actor.id,
            actor_company_id=actor.company_id,
            action="return_for_correction",
            previous_state="submitted",
            new_state="rejected",
            previous_minutes=None,
            new_minutes=suggestion.suggested_minutes,
            notes=notes,
        )

        return suggestion

    # ------------------------------------------------------------------
    # Split: split a pending suggestion into two at a given minute point
    # ------------------------------------------------------------------

    def split_suggestion(
        self,
        suggestion: TimeEntrySuggestion,
        split_minutes: float,
        actor_id: str | None = None,
    ) -> list[TimeEntrySuggestion]:
        """Split a pending suggestion into two suggestions at the given
        minute point from the start.

        Requires an authenticated designer actor who owns the suggestion.
        """
        actor = self._require_authenticated_actor(actor_id, Role.DESIGNER)

        if suggestion.state != TimeEntrySuggestionState.PENDING_REVIEW:
            raise SuggestionDomainError(
                f"Cannot split suggestion in state {suggestion.state}; "
                "only pending_review suggestions can be split."
            )
        if suggestion.user_id != actor.id:
            raise PermissionError("Designers can split only their own suggestions.")
        if suggestion.company_id != actor.company_id:
            raise PermissionError(
                f"Suggestion company {suggestion.company_id} does not match "
                f"actor company {actor.company_id}."
            )
        if suggestion.suggested_minutes <= 0:
            raise SuggestionDomainError(
                f"Cannot split suggestion with {suggestion.suggested_minutes} minutes."
            )
        if split_minutes <= 0 or split_minutes >= suggestion.suggested_minutes:
            raise SuggestionDomainError(
                f"Split minutes {split_minutes} must be between 0 and "
                f"{suggestion.suggested_minutes}."
            )

        now = datetime.now(timezone.utc).isoformat()

        # First suggestion gets split_minutes
        first = TimeEntrySuggestion(
            id=f"suggestion-{self._new_id()}",
            user_id=suggestion.user_id,
            company_id=suggestion.company_id,
            project_id=suggestion.project_id,
            start_time=suggestion.start_time,
            end_time=self._add_minutes(suggestion.start_time, split_minutes),
            suggested_minutes=split_minutes,
            confidence=suggestion.confidence,
            evidence_ids=list(suggestion.evidence_ids),
            state=TimeEntrySuggestionState.PENDING_REVIEW,
            created_at=now,
        )

        # Second suggestion gets remaining minutes
        second = TimeEntrySuggestion(
            id=f"suggestion-{self._new_id()}",
            user_id=suggestion.user_id,
            company_id=suggestion.company_id,
            project_id=suggestion.project_id,
            start_time=self._add_minutes(suggestion.start_time, split_minutes),
            end_time=suggestion.end_time,
            suggested_minutes=round(suggestion.suggested_minutes - split_minutes, 2),
            confidence=suggestion.confidence,
            evidence_ids=list(suggestion.evidence_ids),
            state=TimeEntrySuggestionState.PENDING_REVIEW,
            created_at=now,
        )

        # Mark original as merged
        suggestion.state = TimeEntrySuggestionState.MERGED

        self.db.upsert_suggestion(first)
        self.db.upsert_suggestion(second)
        self.db.upsert_suggestion(suggestion)

        # Record audit
        self._record_decision(
            suggestion_id=suggestion.id,
            actor_id=actor.id,
            actor_company_id=actor.company_id,
            action="split",
            previous_state=TimeEntrySuggestionState.PENDING_REVIEW,
            new_state=TimeEntrySuggestionState.MERGED,
            previous_minutes=suggestion.suggested_minutes,
            new_minutes=suggestion.suggested_minutes,
            notes=f"Split into {split_minutes}min and "
            f"{suggestion.suggested_minutes - split_minutes}min suggestions",
        )

        return [first, second]

    # ------------------------------------------------------------------
    # Merge: combine multiple pending suggestions into one
    # ------------------------------------------------------------------

    def merge_suggestions(
        self,
        suggestion_ids: list[str],
        actor_id: str | None = None,
    ) -> TimeEntrySuggestion:
        """Merge multiple pending suggestions into a single suggestion.

        All suggestions must be pending_review, owned by the same actor,
        in the same company. The resulting suggestion has the combined
        minutes and merged evidence IDs.
        """
        actor = self._require_authenticated_actor(actor_id, Role.DESIGNER)

        if len(suggestion_ids) < 2:
            raise SuggestionDomainError(
                "At least two suggestions are required for merging."
            )

        suggestions: list[TimeEntrySuggestion] = []
        for sid in suggestion_ids:
            s = self.db.get_suggestion(sid)
            if s is None:
                raise SuggestionDomainError(
                    f"Suggestion {sid} not found."
                )
            if s.state != TimeEntrySuggestionState.PENDING_REVIEW:
                raise SuggestionDomainError(
                    f"Suggestion {sid} is in state {s.state}; "
                    "only pending_review suggestions can be merged."
                )
            if s.user_id != actor.id:
                raise PermissionError(
                    "Designer can merge only their own suggestions."
                )
            if s.company_id != actor.company_id:
                raise PermissionError(
                    f"Suggestion {sid} company {s.company_id} does not match "
                    f"actor company {actor.company_id}."
                )
            suggestions.append(s)

        # Use the first suggestion's attributes as base
        first = suggestions[0]
        total_minutes = sum(s.suggested_minutes for s in suggestions)
        evidence_ids: list[str] = []
        for s in suggestions:
            evidence_ids.extend(s.evidence_ids)

        now = datetime.now(timezone.utc).isoformat()

        merged = TimeEntrySuggestion(
            id=f"suggestion-{self._new_id()}",
            user_id=first.user_id,
            company_id=first.company_id,
            project_id=first.project_id,
            start_time=min(s.start_time for s in suggestions),
            end_time=max(s.end_time for s in suggestions),
            suggested_minutes=round(total_minutes, 2),
            confidence=first.confidence,
            evidence_ids=evidence_ids,
            state=TimeEntrySuggestionState.PENDING_REVIEW,
            created_at=now,
        )

        # Mark all originals as merged
        for s in suggestions:
            s.state = TimeEntrySuggestionState.MERGED
            self.db.upsert_suggestion(s)

        self.db.upsert_suggestion(merged)

        # Record audit
        self._record_decision(
            suggestion_id=merged.id,
            actor_id=actor.id,
            actor_company_id=actor.company_id,
            action="merge",
            previous_state="multiple",
            new_state=TimeEntrySuggestionState.PENDING_REVIEW,
            previous_minutes=None,
            new_minutes=total_minutes,
            notes=f"Merged {len(suggestions)} suggestions",
        )

        return merged

    # ------------------------------------------------------------------
    # Audit trail
    # ------------------------------------------------------------------

    def get_suggestion_audit_trail(
        self,
        suggestion_id: str,
    ) -> list[dict[str, Any]]:
        """Return the audit trail for a suggestion."""
        rows = self.db.conn.execute(
            """
            SELECT actor_id, action, previous_state, new_state,
                   previous_minutes, new_minutes, notes, recorded_at
            FROM suggestion_decisions
            WHERE suggestion_id = ?
            ORDER BY recorded_at
            """,
            (suggestion_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_authenticated_actor(
        self,
        actor_id: str | None,
        required_role: Optional[Role] = None,
    ) -> Actor:
        """Validate an authenticated actor with optional role check."""
        actor = current_auth.actor
        if actor is None:
            raise PermissionError("No authenticated actor.")
        if actor_id is not None and actor.id != actor_id:
            raise PermissionError(
                f"Actor {actor.id} does not match requested actor_id {actor_id}."
            )
        if required_role is not None and actor.role != required_role:
            raise PermissionError(
                f"Actor {actor.id} cannot perform {required_role.value} action."
            )
        return actor

    def _record_decision(
        self,
        suggestion_id: str,
        actor_id: str,
        actor_company_id: str,
        action: str,
        previous_state: Optional[str],
        new_state: str,
        previous_minutes: Optional[float],
        new_minutes: float,
        notes: Optional[str],
    ) -> None:
        """Record a decision in the suggestion audit trail."""
        self.db.conn.execute(
            """
            INSERT INTO suggestion_decisions
                (id, suggestion_id, actor_id, actor_company_id, action,
                 previous_state, new_state, previous_minutes, new_minutes,
                 notes, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"dec-{self._new_id()}",
                suggestion_id,
                actor_id,
                actor_company_id,
                action,
                previous_state,
                new_state,
                previous_minutes,
                new_minutes,
                notes,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self.db._commit()

    def _new_id(self) -> str:
        return secrets.token_urlsafe(8)

    @staticmethod
    def _add_minutes(iso_timestamp: str, minutes: float) -> str:
        """Add minutes to an ISO-8601 timestamp string."""
        dt = datetime.fromisoformat(iso_timestamp)
        result = dt + datetime.timedelta(minutes=minutes)
        return result.isoformat()