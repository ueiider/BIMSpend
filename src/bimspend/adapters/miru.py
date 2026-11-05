"""Synthetic Miru-like project adapter.

Reads project/identity data from a JSON fixture (simulating the Miru
API). Real integrations replace this with HTTP calls to a Miru
deployment using the existing agent API
(`POST /api/v1/agent/timesheet_entries`, etc.) as the integration
boundary.
"""

from __future__ import annotations

import json
import os
from typing import Any

from bimspend.models import Project
from .base import ProjectAdapter


class MiruProjectAdapter(ProjectAdapter):
    """Synthetic Miru project adapter backed by a JSON fixture."""

    def __init__(self, fixture_path: str | None = None):
        if fixture_path is None:
            fixture_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "data",
                "synthetic",
                "projects.json",
            )
        self.fixture_path = fixture_path
        self._projects: list[Project] | None = None

    def _load(self) -> list[Project]:
        if self._projects is not None:
            return self._projects
        with open(self.fixture_path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        self._projects = [Project.from_dict(item) for item in raw]
        return self._projects

    def get_projects(self) -> list[Project]:
        return self._load()

    def get_project(self, project_id: str) -> Project | None:
        for p in self._load():
            if p.id == project_id:
                return p
        return None
