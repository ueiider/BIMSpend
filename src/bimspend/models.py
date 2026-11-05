"""Core domain models for the BIMSpend vertical slice.

Metric separation principle: observed activity, attributed time, approved
time, billed hours and loaded internal cost are stored as separate records.
No automatic inference that window focus equals productive or billable work.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class TimeEntryState(Enum):
    """Review and billing states for a time entry.

    State machine (each transition has its own actor and audit record):

    pending_review  -> designer has not yet reviewed suggested hours
    submitted       -> designer has reviewed and submitted for manager approval
    approved        -> manager has approved (NOT billed)
    rejected        -> manager returned for correction, or designer rejected
    billed          -> time has been invoiced (separate explicit action)

    Designer owns: pending_review -> submitted
    Manager owns:  submitted -> approved/rejected
    Billing owns:  approved -> billed (never automatic)
    """

    PENDING_REVIEW = "pending_review"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    BILLED = "billed"


@dataclass
class Project:
    """A commercial project (identity layer, Miru-like)."""

    id: str
    name: str
    client: str
    standard_rate: float  # client charge-out rate (A$/hour)
    loaded_cost_rate: float  # internal loaded labour cost (A$/hour)
    is_billable: bool = True
    created_at: Optional[str] = None
    is_archived: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "client": self.client,
            "standard_rate": self.standard_rate,
            "loaded_cost_rate": self.loaded_cost_rate,
            "is_billable": self.is_billable,
            "created_at": self.created_at,
            "is_archived": self.is_archived,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Project":
        return cls(
            id=data["id"],
            name=data["name"],
            client=data["client"],
            standard_rate=float(data["standard_rate"]),
            loaded_cost_rate=float(data["loaded_cost_rate"]),
            is_billable=bool(data.get("is_billable", True)),
            created_at=data.get("created_at"),
            is_archived=bool(data.get("is_archived", False)),
        )


@dataclass
class ActivityEvent:
    """Raw observed activity event (ActivityWatch-like source).

    This is *observed attention*, not productive effort. It is treated as
    untrusted input until correlated and reviewed.

    Privacy: window_title may be redacted/hashed per privacy policy. The
    raw title must never be stored in plain text for employee data.
    """

    id: str
    source: str  # e.g. "activitywatch", "miru", "revit"
    external_id: str  # idempotency key from the source system
    user_id: str
    app_name: str
    window_title: str  # may be privacy-redacted (see privacy_filter)
    started_at: str  # ISO-8601
    ended_at: str  # ISO-8601
    duration_minutes: float
    is_afk: bool = False
    event_type: str = "active_window"
    raw_payload: Optional[dict[str, Any]] = None
    title_redacted: bool = False  # True if window_title was privacy-redacted

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "external_id": self.external_id,
            "user_id": self.user_id,
            "app_name": self.app_name,
            "window_title": self.window_title,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_minutes": self.duration_minutes,
            "is_afk": self.is_afk,
            "event_type": self.event_type,
            "raw_payload": self.raw_payload,
            "title_redacted": self.title_redacted,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActivityEvent":
        return cls(
            id=data["id"],
            source=data["source"],
            external_id=data["external_id"],
            user_id=data["user_id"],
            app_name=data["app_name"],
            window_title=data["window_title"],
            started_at=data["started_at"],
            ended_at=data["ended_at"],
            duration_minutes=float(data["duration_minutes"]),
            is_afk=bool(data.get("is_afk", False)),
            event_type=data.get("event_type", "active_window"),
            raw_payload=data.get("raw_payload"),
            title_redacted=bool(data.get("title_redacted", False)),
        )


@dataclass
class AttributedTime:
    """Activity correlated to a commercial project.

    The correlation layer assigns an observed activity event to a project
    with a confidence score. This is a *suggestion* pending designer review.
    Uncorrelated/ambiguous events remain unassigned (no project_id match).
    """

    id: str
    activity_event_id: str
    project_id: str | None  # None = unassigned/ambiguous
    attributed_minutes: float
    confidence: float  # 0.0 to 1.0
    correlation_method: str  # e.g. "window_title_match", "user_assignment", "unassigned"
    created_at: Optional[str] = None
    is_archived: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "activity_event_id": self.activity_event_id,
            "project_id": self.project_id,
            "attributed_minutes": self.attributed_minutes,
            "confidence": self.confidence,
            "correlation_method": self.correlation_method,
            "created_at": self.created_at,
        }


@dataclass
class TimeEntry:
    """Designer-reviewed / manager-approved time entry.

    The source of truth for billing/cost decisions. Distinct from observed
    activity and attributed time.

    States:
      pending_review  -> designer has not yet reviewed suggested hours
      submitted       -> designer submitted for manager approval
      approved        -> manager approved (NOT automatically billed)
      rejected        -> returned for correction
      billed          -> invoiced to client (separate explicit action)
    """

    id: str
    attributed_time_id: str
    project_id: str
    user_id: str
    minutes: float
    state: TimeEntryState = TimeEntryState.PENDING_REVIEW
    standard_rate: float = 0.0  # snapshot of project rate at review
    loaded_cost_rate: float = 0.0  # snapshot of loaded cost at review
    billed_minutes: float = 0.0  # hours invoiced to client (may differ from minutes)
    review_notes: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None  # ISO-8601
    submitted_by: Optional[str] = None  # designer who submitted
    submitted_at: Optional[str] = None  # when designer submitted
    created_at: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "attributed_time_id": self.attributed_time_id,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "minutes": self.minutes,
            "state": self.state.value,
            "standard_rate": self.standard_rate,
            "loaded_cost_rate": self.loaded_cost_rate,
            "billed_minutes": self.billed_minutes,
            "review_notes": self.review_notes,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at,
            "submitted_by": self.submitted_by,
            "submitted_at": self.submitted_at,
            "created_at": self.created_at,
            "is_archived": self.is_archived,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TimeEntry":
        return cls(
            id=data["id"],
            attributed_time_id=data["attributed_time_id"],
            project_id=data["project_id"],
            user_id=data["user_id"],
            minutes=float(data["minutes"]),
            state=TimeEntryState(data.get("state", "pending_review")),
            standard_rate=float(data.get("standard_rate", 0.0)),
            loaded_cost_rate=float(data.get("loaded_cost_rate", 0.0)),
            billed_minutes=float(data.get("billed_minutes", 0.0)),
            review_notes=data.get("review_notes"),
            reviewed_by=data.get("reviewed_by"),
            reviewed_at=data.get("reviewed_at"),
            submitted_by=data.get("submitted_by"),
            submitted_at=data.get("submitted_at"),
            created_at=data.get("created_at"),
            is_archived=bool(data.get("is_archived", False)),
        )

    @property
    def labor_cost(self) -> float:
        """Internal loaded labour cost for this entry (not revenue)."""
        return self.minutes / 60.0 * self.loaded_cost_rate

    @property
    def standard_value(self) -> float:
        """Standard charge-out value of reviewed minutes (not revenue)."""
        return self.minutes / 60.0 * self.standard_rate

    @property
    def is_approved(self) -> bool:
        return self.state == TimeEntryState.APPROVED

    @property
    def is_billed(self) -> bool:
        return self.billed_minutes > 0

    @property
    def is_submitted(self) -> bool:
        return self.state == TimeEntryState.SUBMITTED

    @property
    def is_pending_review(self) -> bool:
        return self.state == TimeEntryState.PENDING_REVIEW

    @property
    def is_rejected(self) -> bool:
        return self.state == TimeEntryState.REJECTED
