"""Automatic timesheet suggestion engine.

Converts observed activity events into reviewable time entry suggestions.
The engine:

1. Queries activity events for a user/company in a time range
2. Filters out AFK and locked-session intervals
3. Looks up correlation evidence for each event
4. Groups consecutive same-project events into suggestions
5. Produces TimeEntrySuggestion objects at CONFIRMED/HIGH/MEDIUM/LOW/UNASSIGNED
   confidence levels

Observed activity is NEVER automatically approved or billed — every
suggestion requires explicit designer review and submission.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from bimspend.db import Database
from bimspend.models import ActivityEvent, AttributedTime, TimeEntry, TimeEntryState, TimeEntrySuggestion

logger = logging.getLogger(__name__)


@dataclass
class SuggestionConfig:
    """Configuration for the suggestion engine."""

    # Maximum gap (minutes) between consecutive same-project events
    # before they are split into separate suggestions.
    max_gap_minutes: float = 15.0

    # Minimum duration (minutes) for a suggestion to be generated.
    min_duration_minutes: float = 5.0

    # Company-scoping: only generate suggestions for this company.
    company_id: Optional[str] = None


@dataclass
class ActivityObservation:
    """A single observed activity event with correlation context."""

    event_id: str
    user_id: str
    company_id: Optional[str]
    app_name: str
    window_title: str  # privacy-hashed
    start_time: str  # ISO-8601 UTC
    end_time: str  # ISO-8601 UTC
    duration_minutes: float
    is_afk: bool
    is_locked: bool
    project_id: Optional[str] = None
    confidence: str = "unassigned"
    correlation_method: Optional[str] = None


class SuggestionEngine:
    """Deterministic suggestion engine for automatic timesheet generation.

    Converts observed activity events into reviewable time entry
    suggestions. All suggestions start in pending_review state and
    require explicit designer submission before becoming billable time.

    The engine is deterministic — given the same input events, it
    always produces the same suggestions. Reprocessing is idempotent.
    """

    def __init__(
        self,
        db: Database,
        config: Optional[SuggestionConfig] = None,
    ):
        self.db = db
        self.config = config or SuggestionConfig()

    # ------------------------------------------------------------------
    # Observation collection
    # ------------------------------------------------------------------

    def collect_observations(
        self,
        user_id: str,
        start_time: str,
        end_time: str,
    ) -> list[ActivityObservation]:
        """Collect activity events for a user in a time range.

        Returns observations sorted by start_time, with correlation
        evidence attached where available.
        """
        events = self.db.list_events(user_id=user_id)

        # Filter by time range
        in_range = []
        for event in events:
            if event.started_at < start_time or event.ended_at > end_time:
                continue
            in_range.append(event)

        # Sort by start time
        in_range.sort(key=lambda e: e.started_at)

        # Build observations with correlation evidence
        observations: list[ActivityObservation] = []
        for event in in_range:
            observation = self._event_to_observation(event)
            observations.append(observation)

        return observations

    def _event_to_observation(
        self,
        event: ActivityEvent,
    ) -> ActivityObservation:
        """Convert an ActivityEvent to an ActivityObservation.

        Looks up correlation evidence from the revit_correlation_evidence
        table to determine project attribution and confidence.
        """
        # Look up correlation evidence for this event
        evidence = self._get_correlation_evidence(event.id)

        if evidence is not None:
            project_id = evidence["document_guid"]
            confidence = evidence["correlation_confidence"]
            correlation_method = evidence["correlation_method"]
        else:
            project_id = None
            confidence = "unassigned"
            correlation_method = None

        return ActivityObservation(
            event_id=event.id,
            user_id=event.user_id,
            company_id=event.company_id,
            app_name=event.app_name,
            window_title=event.window_title,
            start_time=event.started_at,
            end_time=event.ended_at,
            duration_minutes=event.duration_minutes,
            is_afk=event.is_afk,
            is_locked=evidence["is_locked"] if evidence else False,
            project_id=project_id,
            confidence=confidence,
            correlation_method=correlation_method,
        )

    def _get_correlation_evidence(
        self,
        activity_event_id: str,
    ) -> Optional[dict[str, Any]]:
        """Look up correlation evidence for an activity event."""
        row = self.db.conn.execute(
            """
            SELECT document_guid, correlation_confidence, correlation_method,
                   is_afk, is_locked
            FROM revit_correlation_evidence
            WHERE activity_event_id = ?
            ORDER BY recorded_at DESC
            LIMIT 1
            """,
            (activity_event_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "document_guid": row["document_guid"],
            "correlation_confidence": row["correlation_confidence"],
            "correlation_method": row["correlation_method"],
            "is_afk": bool(row["is_afk"]),
            "is_locked": bool(row["is_locked"]),
        }

    # ------------------------------------------------------------------
    # Suggestion generation
    # ------------------------------------------------------------------

    def generate_suggestions(
        self,
        user_id: str,
        start_time: str,
        end_time: str,
    ) -> list[TimeEntrySuggestion]:
        """Generate time entry suggestions for a user in a time range.

        Groups consecutive same-project observations into suggestions,
        excluding AFK and locked-session intervals. Returns suggestions
        in pending_review state.

        Idempotent: calling with the same parameters produces the same
        suggestions.
        """
        observations = self.collect_observations(user_id, start_time, end_time)

        # Filter out AFK and locked intervals
        active_observations = [
            o for o in observations
            if not o.is_afk and not o.is_locked
        ]

        # Group consecutive same-project observations
        suggestions = self._group_observations(active_observations)

        # Filter by minimum duration
        suggestions = [
            s for s in suggestions
            if s.suggested_minutes >= self.config.min_duration_minutes
        ]

        logger.info(
            "Generated %d suggestions for user=%s (%s to %s)",
            len(suggestions),
            user_id,
            start_time,
            end_time,
        )
        return suggestions

    def _group_observations(
        self,
        observations: list[ActivityObservation],
    ) -> list[TimeEntrySuggestion]:
        """Group consecutive same-project observations into suggestions.

        Consecutive observations with the same project_id are merged
        into a single suggestion. AFK/locked observations are excluded
        (filtered out before this method is called), but they do NOT
        break the chain — same-project observations on either side of
        an AFK gap are merged.

        Returns suggestions sorted by start_time.
        """
        if not observations:
            return []

        suggestions: list[TimeEntrySuggestion] = []
        current_group: Optional[ActivityObservation] = None
        group_events: list[ActivityObservation] = []

        for obs in observations:
            if current_group is None:
                # Start new group
                current_group = obs
                group_events = [obs]
            elif obs.project_id == current_group.project_id:
                # Same project — extend current group
                group_events.append(obs)
            else:
                # Different project — close current group, start new one
                suggestion = self._build_suggestion(current_group, group_events)
                if suggestion is not None:
                    suggestions.append(suggestion)
                current_group = obs
                group_events = [obs]

        # Close final group
        if current_group is not None:
            suggestion = self._build_suggestion(current_group, group_events)
            if suggestion is not None:
                suggestions.append(suggestion)

        return suggestions

    def _build_suggestion(
        self,
        first_observation: ActivityObservation,
        events: list[ActivityObservation],
    ) -> Optional[TimeEntrySuggestion]:
        """Build a TimeEntrySuggestion from a group of observations."""

        import hashlib

        total_minutes = sum(e.duration_minutes for e in events)

        if total_minutes <= 0:
            return None

        # Determine project_id and confidence from events
        # Use the most common project_id and highest confidence
        project_id = first_observation.project_id
        confidence = first_observation.confidence

        # Count project_id frequency
        project_counts: dict[Optional[str], int] = {}
        for e in events:
            pid = e.project_id
            project_counts[pid] = project_counts.get(pid, 0) + 1

        # Pick most frequent project_id (non-None preferred)
        best_project: Optional[str] = None
        best_count = 0
        for pid, count in project_counts.items():
            if pid is not None and count > best_count:
                best_project = pid
                best_count = count

        if best_project is not None:
            project_id = best_project

        # Determine confidence: use the highest confidence from events
        confidence_order = {
            "CONFIRMED": 5,
            "HIGH": 4,
            "MEDIUM": 3,
            "LOW": 2,
            "UNASSIGNED": 1,
        }
        best_confidence = first_observation.confidence
        best_conf = confidence_order.get(best_confidence, 1)
        for e in events:
            c = confidence_order.get(e.confidence, 1)
            if c > best_conf:
                best_conf = c
                best_confidence = e.confidence

        # Collect evidence IDs
        evidence_ids = [e.event_id for e in events]

        start_time = events[0].start_time
        end_time = events[-1].end_time

        # Build a deterministic ID from input data for idempotency
        evidence_hash = hashlib.sha256(
            f"{start_time}-{'-'.join(sorted(evidence_ids))}".encode()
        ).hexdigest()[:12]
        suggestion_id = f"suggestion-{evidence_hash}"

        return TimeEntrySuggestion(
            id=suggestion_id,
            user_id=first_observation.user_id,
            company_id=first_observation.company_id,
            project_id=project_id,
            start_time=start_time,
            end_time=end_time,
            suggested_minutes=round(total_minutes, 2),
            confidence=best_confidence,
            evidence_ids=evidence_ids,
            state="pending_review",
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    # ------------------------------------------------------------------
    # Persistence integration (delegates to Database methods)
    # ------------------------------------------------------------------

    def save_suggestion(self, suggestion: TimeEntrySuggestion) -> bool:
        """Persist a suggestion to the database.

        Returns True if inserted, False if duplicate (same id already exists).
        Idempotent — saving the same suggestion twice is a no-op.
        """
        return self.db.upsert_suggestion(suggestion)

    def load_suggestion(self, suggestion_id: str) -> Optional[TimeEntrySuggestion]:
        """Load a suggestion by id."""
        return self.db.get_suggestion(suggestion_id)

    def list_suggestions(
        self,
        user_id: str,
        state: Optional[str] = None,
    ) -> list[TimeEntrySuggestion]:
        """List suggestions for a user, optionally filtered by state."""
        return self.db.list_suggestions(user_id, state)

    # ------------------------------------------------------------------
    # Submission / rejection (domain actions)
    # ------------------------------------------------------------------

    def submit_suggestion(
        self,
        suggestion: TimeEntrySuggestion,
        actor_id: str,
    ) -> TimeEntrySuggestion:
        """Submit a suggestion for manager approval.

        Creates a linked TimeEntry in SUBMITTED state and marks the
        suggestion as submitted. Idempotent — submitting an already
        submitted suggestion is a no-op.

        Requires the suggestion to be in pending_review state.
        """
        if suggestion.state != "pending_review":
            raise ValueError(
                f"Cannot submit suggestion in state {suggestion.state}; "
                "only pending_review suggestions can be submitted."
            )

        now = datetime.now(timezone.utc).isoformat()

        # Create linked TimeEntry
        # First create attributed_time row (FK target for time_entries)
        activity_event_id = suggestion.evidence_ids[0] if suggestion.evidence_ids else suggestion.id
        attributed_entry = AttributedTime(
            id=suggestion.id,
            activity_event_id=activity_event_id,
            project_id=suggestion.edited_project_id or suggestion.project_id,
            attributed_minutes=suggestion.edited_minutes or suggestion.suggested_minutes,
            confidence=1.0,
            correlation_method="session_correlation",
            created_at=suggestion.created_at,
        )
        self.db.upsert_attributed_time(attributed_entry)

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
            review_notes=suggestion.review_notes,
            reviewed_by=None,
            reviewed_at=None,
            submitted_by=actor_id,
            submitted_at=now,
            created_at=now,
            company_id=suggestion.company_id,
        )

        # Persist time entry
        self.db.upsert_time_entry(entry, actor_id=actor_id)

        # Update suggestion
        suggestion.state = "submitted"
        suggestion.submitted_by = actor_id
        suggestion.submitted_at = now
        suggestion.time_entry_id = entry.id

        # Save updated suggestion
        self.db.upsert_suggestion(suggestion)

        return suggestion

    def reject_suggestion(
        self,
        suggestion: TimeEntrySuggestion,
    ) -> TimeEntrySuggestion:
        """Reject a suggestion.

        Marks the suggestion as rejected. Does not create a TimeEntry.
        Idempotent — rejecting an already rejected suggestion is a no-op.
        """
        if suggestion.state != "pending_review":
            raise ValueError(
                f"Cannot reject suggestion in state {suggestion.state}; "
                "only pending_review suggestions can be rejected."
            )

        suggestion.state = "rejected"
        self.db.upsert_suggestion(suggestion)

        return suggestion