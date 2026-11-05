"""Synthetic ActivityWatch-like adapter.

Reads activity events from a JSON fixture (simulating the ActivityWatch
local REST API /api/0 buckets/events). Real integrations replace this
with HTTP calls to a loopback aw-server instance.

Events are treated as *untrusted input* — observed attention, not
productive effort — pending correlation and designer review.
"""

from __future__ import annotations

import json
import os
from typing import Any

from bimspend.models import ActivityEvent
from .base import ActivityAdapter


class ActivityWatchAdapter(ActivityAdapter):
    """Synthetic ActivityWatch adapter backed by a JSON fixture."""

    def __init__(self, fixture_path: str | None = None):
        if fixture_path is None:
            fixture_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "data",
                "synthetic",
                "events.json",
            )
        self.fixture_path = fixture_path
        self._events: list[ActivityEvent] | None = None

    def _load(self) -> list[ActivityEvent]:
        if self._events is not None:
            return self._events
        with open(self.fixture_path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        self._events = [ActivityEvent.from_dict(item) for item in raw]
        return self._events

    def get_events(
        self, user_id: str | None = None, from_time: str | None = None
    ) -> list[ActivityEvent]:
        events = self._load()
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        if from_time:
            events = [e for e in events if e.ended_at >= from_time]
        return events
