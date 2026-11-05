"""BIMSpend Build 01 vertical slice.

Project time-and-cost intelligence prototype with adapter interfaces.
Real ActivityWatch, Miru and Revit integrations connect through these
interfaces later; this slice uses synthetic data only.
"""

__version__ = "0.1.0"

from .models import Project, ActivityEvent, AttributedTime, TimeEntry, TimeEntryState
from .db import Database

__all__ = [
    "Project",
    "ActivityEvent",
    "AttributedTime",
    "TimeEntry",
    "TimeEntryState",
    "Database",
]
