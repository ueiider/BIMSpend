"""Historical estimating from confirmed manager-approved local synthetic time."""
from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from bimspend.db import Database
from bimspend.models import TimeEntryState


@dataclass(frozen=True)
class Estimate:
    reference_projects: int
    median_hours: float
    low_hours: float
    high_hours: float
    estimated_cost_aud: float
    assumptions: str


def estimate_from_history(db: Database, target_project_id: str) -> Estimate | None:
    target = db.get_project(target_project_id)
    if target is None:
        raise ValueError("Unknown project.")
    hours: dict[str, float] = {}
    for entry in db.list_time_entries():
        if entry.project_id == target_project_id or entry.state not in (
                TimeEntryState.APPROVED, TimeEntryState.BILLED):
            continue
        hours[entry.project_id] = hours.get(entry.project_id, 0) + entry.minutes / 60
    if not hours:
        return None
    samples = list(hours.values())
    basis = median(samples)
    return Estimate(
        reference_projects=len(samples), median_hours=round(basis, 1),
        low_hours=round(min(samples), 1), high_hours=round(max(samples), 1),
        estimated_cost_aud=round(basis * target.loaded_cost_rate, 2),
        assumptions=("Uses the median of approved hours on other projects with "
                     "any approved entries. They may be incomplete and unrelated. "
                     "Rates use the target project's current loaded cost; "
                     "this is a preliminary reference, not a quote."),
    )
