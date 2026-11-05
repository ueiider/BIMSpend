"""Abstract adapter interfaces.

Real ActivityWatch, Miru and Revit integrations implement these
interfaces. The vertical slice ships synthetic/mock implementations that
read from JSON fixtures.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from bimspend.models import ActivityEvent, Project


class ProjectAdapter(ABC):
    """Reads project/identity data from an external system (Miru-like)."""

    @abstractmethod
    def get_projects(self) -> list[Project]:
        """Return all projects visible to the caller."""

    @abstractmethod
    def get_project(self, project_id: str) -> Project | None:
        """Return a single project by id."""


class ActivityAdapter(ABC):
    """Reads observed activity events from an external system
    (ActivityWatch-like). Events are treated as untrusted input."""

    @abstractmethod
    def get_events(
        self, user_id: str | None = None, from_time: str | None = None
    ) -> list[ActivityEvent]:
        """Return activity events, optionally filtered by user and time."""


class CorrelationAdapter(ABC):
    """Correlates observed activity events to commercial projects."""

    @abstractmethod
    def correlate(
        self, events: list[ActivityEvent], projects: list[Project]
    ) -> list[dict[str, Any]]:
        """Return attributed-time suggestions: one dict per event with
        keys: activity_event_id, project_id, attributed_minutes,
        confidence, correlation_method."""


class ReviewAdapter(ABC):
    """Persists designer review decisions (approve/reject)."""

    @abstractmethod
    def decide(
        self, entry_id: str, state: str, reviewed_by: str, notes: str | None
    ) -> None:
        """Record a designer's approve/reject decision on a time entry."""


class DashboardAdapter(ABC):
    """Reads aggregated project-hours data for managers."""

    @abstractmethod
    def project_summary(self, project_id: str) -> dict[str, Any]:
        """Return observed/attributed/approved/billed hours for a project."""

    @abstractmethod
    def all_projects_summary(self) -> list[dict[str, Any]]:
        """Return summaries for all projects."""
