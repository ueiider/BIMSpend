"""Core domain models for the BIMSpend vertical slice.

Metric separation principle: observed activity, attributed time, approved
time, billed hours and loaded internal cost are stored as separate records.
No automatic inference that window focus equals productive or billable work.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
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


class SuggestionState(Enum):
    """Review state for a suggested time entry.

    Suggestions are auto-generated from observed activity and must be
    explicitly reviewed and submitted by a designer before becoming
    billable time.

    States:
      pending_review  -> suggestion has not been reviewed by designer
      submitted       -> designer submitted for manager approval
      rejected        -> designer rejected the suggestion
      merged          -> suggestion was merged into another suggestion
    """

    PENDING_REVIEW = "pending_review"
    SUBMITTED = "submitted"
    REJECTED = "rejected"
    MERGED = "merged"


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
    budget_aud: float | None = None

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
            "budget_aud": self.budget_aud,
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
            budget_aud=float(data["budget_aud"]) if data.get("budget_aud") is not None else None,
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
    company_id: Optional[str] = None  # company scope for tenant isolation
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
            "company_id": self.company_id,
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
            company_id=data.get("company_id"),
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
            "is_archived": self.is_archived,
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
    is_archived: bool = False
    company_id: Optional[str] = None

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
            "company_id": self.company_id,
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
        return self.state in (TimeEntryState.APPROVED, TimeEntryState.BILLED)

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



@dataclass
class TeamMember:
    """Local synthetic roster, separate from authenticated identity."""
    id: str
    name: str
    role: str
    loaded_cost_rate: float
    is_active: bool = True


class SuggestionState(Enum):
    """Review state for a suggested time entry.

    Suggestions are auto-generated from observed activity and must be
    explicitly reviewed and submitted by a designer before becoming
    billable time.

    States:
      pending_review  -> suggestion has not been reviewed by designer
      submitted       -> designer submitted for manager approval
      rejected        -> designer rejected the suggestion
      merged          -> suggestion was merged into another suggestion
    """

    PENDING_REVIEW = "pending_review"
    SUBMITTED = "submitted"
    REJECTED = "rejected"
    MERGED = "merged"


@dataclass
class TimeEntrySuggestion:
    """Auto-generated time entry suggestion from observed activity.

    Created by the suggestion engine from correlation evidence and
    activity events. A suggestion is NOT a time entry — it must be
    explicitly reviewed and submitted by a designer before it becomes
    billable time.

    Designer may edit project, duration, and notes before submitting.
    Submitted entries enter the existing review workflow
    (pending_review -> submitted -> approved/rejected -> billed).
    """

    id: str
    user_id: str
    start_time: str  # ISO-8601 UTC
    end_time: str  # ISO-8601 UTC
    suggested_minutes: float  # observed active duration (excludes AFK/locked)
    confidence: str  # CONFIRMED, HIGH, MEDIUM, LOW, UNASSIGNED
    evidence_ids: list[str]  # activity_event ids that contributed
    company_id: Optional[str] = None
    project_id: Optional[str] = None  # None if UNASSIGNED
    state: str = "pending_review"  # pending_review, submitted, rejected, merged
    edited_minutes: Optional[float] = None  # designer override
    edited_project_id: Optional[str] = None  # designer project override
    review_notes: Optional[str] = None
    submitted_by: Optional[str] = None
    submitted_at: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    time_entry_id: Optional[str] = None  # linked TimeEntry if submitted
    created_at: str = ""  # ISO-8601 UTC

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "company_id": self.company_id,
            "project_id": self.project_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "suggested_minutes": self.suggested_minutes,
            "confidence": self.confidence,
            "evidence_ids": self.evidence_ids,
            "state": self.state,
            "edited_minutes": self.edited_minutes,
            "edited_project_id": self.edited_project_id,
            "review_notes": self.review_notes,
            "submitted_by": self.submitted_by,
            "submitted_at": self.submitted_at,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at,
            "time_entry_id": self.time_entry_id,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TimeEntrySuggestion":
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            company_id=data.get("company_id"),
            project_id=data.get("project_id"),
            start_time=data["start_time"],
            end_time=data["end_time"],
            suggested_minutes=float(data["suggested_minutes"]),
            confidence=data.get("confidence", "unassigned"),
            evidence_ids=data.get("evidence_ids", []),
            state=data.get("state", "pending_review"),
            edited_minutes=data.get("edited_minutes"),
            edited_project_id=data.get("edited_project_id"),
            review_notes=data.get("review_notes"),
            submitted_by=data.get("submitted_by"),
            submitted_at=data.get("submitted_at"),
            reviewed_by=data.get("reviewed_by"),
            reviewed_at=data.get("reviewed_at"),
            time_entry_id=data.get("time_entry_id"),
            created_at=data.get("created_at", ""),
        )


@dataclass
class UserIdentityMap:
    """Maps historical user_id values from time_entries to team_members.

    Preserves original user IDs while allowing authorized, auditable
    mapping to authenticated team member accounts. Unmapped identities
    are tracked separately so historical records are never orphaned
    or silently reassigned.
    """

    id: str
    historical_user_id: str
    mapped_member_id: str | None  # None = unresolved
    mapping_status: str  # "unresolved" or "mapped"
    mapped_by: str | None
    mapped_at: str | None
    reason: str | None
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "historical_user_id": self.historical_user_id,
            "mapped_member_id": self.mapped_member_id,
            "mapping_status": self.mapping_status,
            "mapped_by": self.mapped_by,
            "mapped_at": self.mapped_at,
            "reason": self.reason,
            "created_at": self.created_at,
        }


# ------------------------------------------------------------------
# Financial management models (R1-07)
# ------------------------------------------------------------------


class AdjustmentType(str, Enum):
    """Types of financial adjustments."""
    COST = "cost"
    CREDIT = "credit"
    WRITEOFF = "writeoff"
    ACCRUAL = "accrual"


@dataclass
class EmployeeCostRate:
    """Employee internal labour cost rate with effective date range.

    Historical rate preservation: rates are never silently rewritten.
    New rates create new records with effective_from dates. The rate
    effective at a given time is selected by effective_from <= target
    and (effective_to IS NULL OR effective_to > target).
    """

    id: str
    member_id: str  # team_members.id
    company_id: str  # company scope for tenant isolation
    hourly_cost_aud: Decimal  # internal cost per hour in AUD
    effective_from: str  # ISO-8601 UTC
    effective_to: Optional[str] = None  # NULL = current rate
    created_by: str = ""  # actor who created this rate
    created_at: str = ""
    notes: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "member_id": self.member_id,
            "company_id": self.company_id,
            "hourly_cost_aud": str(self.hourly_cost_aud),
            "effective_from": self.effective_from,
            "effective_to": self.effective_to,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EmployeeCostRate":
        return cls(
            id=data["id"],
            member_id=data["member_id"],
            company_id=data["company_id"],
            hourly_cost_aud=Decimal(str(data["hourly_cost_aud"])),
            effective_from=data["effective_from"],
            effective_to=data.get("effective_to"),
            created_by=data.get("created_by", ""),
            created_at=data.get("created_at", ""),
            notes=data.get("notes"),
        )


@dataclass
class EmployeeBillingRate:
    """Employee client billing rate with effective date range.

    Historical rate preservation: same pattern as EmployeeCostRate.
    """

    id: str
    member_id: str  # team_members.id
    company_id: str  # company scope for tenant isolation
    hourly_billing_aud: Decimal  # billing rate per hour in AUD
    effective_from: str  # ISO-8601 UTC
    effective_to: Optional[str] = None  # NULL = current rate
    created_by: str = ""
    created_at: str = ""
    notes: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "member_id": self.member_id,
            "company_id": self.company_id,
            "hourly_billing_aud": str(self.hourly_billing_aud),
            "effective_from": self.effective_from,
            "effective_to": self.effective_to,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EmployeeBillingRate":
        return cls(
            id=data["id"],
            member_id=data["member_id"],
            company_id=data["company_id"],
            hourly_billing_aud=Decimal(str(data["hourly_billing_aud"])),
            effective_from=data["effective_from"],
            effective_to=data.get("effective_to"),
            created_by=data.get("created_by", ""),
            created_at=data.get("created_at", ""),
            notes=data.get("notes"),
        )


@dataclass
class ProjectBudget:
    """Project financial configuration with budget tracking.

    Original budget is preserved; current budget reflects revisions.
    Labour budget tracked independently from total project budget.
    """

    id: str
    project_id: str  # projects.id
    company_id: str  # company scope for tenant isolation
    original_budget_aud: Decimal
    current_budget_aud: Decimal
    budget_currency: str = "AUD"
    project_status: str = "active"  # active, on_hold, completed, cancelled
    budget_owner_id: Optional[str] = None  # team_members.id
    effective_from: str = ""
    effective_to: Optional[str] = None
    created_by: str = ""
    created_at: str = ""
    notes: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "company_id": self.company_id,
            "original_budget_aud": str(self.original_budget_aud),
            "current_budget_aud": str(self.current_budget_aud),
            "budget_currency": self.budget_currency,
            "project_status": self.project_status,
            "budget_owner_id": self.budget_owner_id,
            "effective_from": self.effective_from,
            "effective_to": self.effective_to,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectBudget":
        return cls(
            id=data["id"],
            project_id=data["project_id"],
            company_id=data["company_id"],
            original_budget_aud=Decimal(str(data["original_budget_aud"])),
            current_budget_aud=Decimal(str(data["current_budget_aud"])),
            budget_currency=data.get("budget_currency", "AUD"),
            project_status=data.get("project_status", "active"),
            budget_owner_id=data.get("budget_owner_id"),
            effective_from=data.get("effective_from", ""),
            effective_to=data.get("effective_to"),
            created_by=data.get("created_by", ""),
            created_at=data.get("created_at", ""),
            notes=data.get("notes"),
        )


@dataclass
class BudgetRevision:
    """Auditable budget revision history."""

    id: str
    project_budget_id: str  # project_budgets.id
    revision_number: int
    previous_budget_aud: Decimal
    new_budget_aud: Decimal
    revision_reason: str
    created_by: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project_budget_id": self.project_budget_id,
            "revision_number": self.revision_number,
            "previous_budget_aud": str(self.previous_budget_aud),
            "new_budget_aud": str(self.new_budget_aud),
            "revision_reason": self.revision_reason,
            "created_by": self.created_by,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BudgetRevision":
        return cls(
            id=data["id"],
            project_budget_id=data["project_budget_id"],
            revision_number=int(data["revision_number"]),
            previous_budget_aud=Decimal(str(data["previous_budget_aud"])),
            new_budget_aud=Decimal(str(data["new_budget_aud"])),
            revision_reason=data["revision_reason"],
            created_by=data["created_by"],
            created_at=data["created_at"],
        )


@dataclass
class FinancialAdjustment:
    """Manual financial adjustment/correction.

    Adjustments are traceable to an authorized actor and company.
    Never creates duplicate records for the same entry.
    """

    id: str
    entry_id: Optional[str]  # time_entries.id (NULL for project-level adjustments)
    project_id: str  # projects.id
    company_id: str  # company scope
    adjustment_type: AdjustmentType
    amount_aud: Decimal
    adjustment_date: str  # ISO-8601 UTC
    created_by: str
    created_at: str
    notes: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "entry_id": self.entry_id,
            "project_id": self.project_id,
            "company_id": self.company_id,
            "adjustment_type": self.adjustment_type.value,
            "amount_aud": str(self.amount_aud),
            "adjustment_date": self.adjustment_date,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FinancialAdjustment":
        return cls(
            id=data["id"],
            entry_id=data.get("entry_id"),
            project_id=data["project_id"],
            company_id=data["company_id"],
            adjustment_type=AdjustmentType(data["adjustment_type"]),
            amount_aud=Decimal(str(data["amount_aud"])),
            adjustment_date=data["adjustment_date"],
            created_by=data["created_by"],
            created_at=data["created_at"],
            notes=data.get("notes"),
        )


@dataclass
class FinancialSummary:
    """Computed financial summary for a project.

    All amounts in AUD. Derived from approved time entries only.
    """

    project_id: str
    project_name: str
    company_id: str
    original_budget_aud: Decimal
    current_budget_aud: Decimal
    approved_labour_cost_aud: Decimal
    remaining_budget_aud: Decimal
    budget_utilization_percent: float
    budget_variance_aud: Decimal  # positive = over budget
    is_over_budget: bool
    approved_hours: float
    billing_value_aud: Decimal  # approved hours * billing rates
    gross_margin_aud: Decimal  # billing value - labour cost
    last_updated: str  # ISO-8601 UTC

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "company_id": self.company_id,
            "original_budget_aud": str(self.original_budget_aud),
            "current_budget_aud": str(self.current_budget_aud),
            "approved_labour_cost_aud": str(self.approved_labour_cost_aud),
            "remaining_budget_aud": str(self.remaining_budget_aud),
            "budget_utilization_percent": self.budget_utilization_percent,
            "budget_variance_aud": str(self.budget_variance_aud),
            "is_over_budget": self.is_over_budget,
            "approved_hours": self.approved_hours,
            "billing_value_aud": str(self.billing_value_aud),
            "gross_margin_aud": str(self.gross_margin_aud),
            "last_updated": self.last_updated,
        }
