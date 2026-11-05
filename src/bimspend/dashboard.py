"""Manager-facing project-hours dashboard.

Aggregates observed, attributed, approved and billed hours per project,
preserving the distinction between them. Loaded internal labour cost is
computed separately from charge-out revenue.
"""

from __future__ import annotations

from typing import Any

from bimspend.models import Project, TimeEntry, TimeEntryState


def project_summary(
    project: Project,
    events_minutes: float,
    attributed_minutes: float,
    entries: list[TimeEntry],
) -> dict[str, Any]:
    """Build a per-project summary.

    Args:
        project: the project domain model.
        events_minutes: total observed activity minutes (ActivityWatch).
        attributed_minutes: total attributed minutes (correlation output).
        entries: all time entries for the project.
    """
    approved = [e for e in entries if e.state == TimeEntryState.APPROVED]
    rejected = [e for e in entries if e.state == TimeEntryState.REJECTED]
    pending = [e for e in entries if e.state == TimeEntryState.PENDING_REVIEW]

    approved_minutes = sum(e.minutes for e in approved)
    rejected_minutes = sum(e.minutes for e in rejected)
    pending_minutes = sum(e.minutes for e in pending)
    billed_minutes = sum(e.billed_minutes for e in entries)

    approved_hours = approved_minutes / 60.0
    billed_hours = billed_minutes / 60.0
    observed_hours = events_minutes / 60.0
    attributed_hours = attributed_minutes / 60.0

    labor_cost = sum(e.labor_cost for e in approved)
    standard_value = sum(e.standard_value for e in approved)

    return {
        "project_id": project.id,
        "project_name": project.name,
        "client": project.client,
        "standard_rate": project.standard_rate,
        "loaded_cost_rate": project.loaded_cost_rate,
        # Observed (ActivityWatch) attention — not productive effort.
        "observed_hours": round(observed_hours, 2),
        # Attributed (correlated) project time — pending review.
        "attributed_hours": round(attributed_hours, 2),
        # Designer-approved time.
        "approved_hours": round(approved_hours, 2),
        # Invoiced/billed hours (may differ from approved — realization gap).
        "billed_hours": round(billed_hours, 2),
        # Counts by state.
        "approved_count": len(approved),
        "rejected_count": len(rejected),
        "pending_count": len(pending),
        "rejected_minutes": round(rejected_minutes, 2),
        "pending_minutes": round(pending_minutes, 2),
        # Financial views (approved entries only).
        "labor_cost_aud": round(labor_cost, 2),        # internal loaded cost
        "standard_value_aud": round(standard_value, 2), # client charge value
        "realization_percent": round(
            (billed_hours / observed_hours * 100) if observed_hours > 0 else 0.0, 2
        ),
        "effective_rate_aud": round(
            (project.standard_rate * billed_hours / observed_hours)
            if observed_hours > 0
            else 0.0,
            2,
        ),
    }


def all_projects_summary(
    projects: list[Project],
    events_by_project: dict[str, float],
    attributed_by_project: dict[str, float],
    entries: list[TimeEntry],
) -> list[dict[str, Any]]:
    """Return summaries for all projects."""
    summaries: list[dict[str, Any]] = []
    for p in projects:
        summaries.append(
            project_summary(
                p,
                events_by_project.get(p.id, 0.0),
                attributed_by_project.get(p.id, 0.0),
                [e for e in entries if e.project_id == p.id],
            )
        )
    return summaries
