"""Test project attribution.

Verifies that activity events are correlated to commercial projects with
correct confidence scores, and that uncorrelated/afk events do not
produce attributed time.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bimspend.adapters.activitywatch import ActivityWatchAdapter  # noqa: E402
from bimspend.adapters.miru import MiruProjectAdapter  # noqa: E402
from bimspend.correlation import correlate_events  # noqa: E402


def _fixture(name):
    return os.path.join(
        os.path.dirname(__file__), "..", "data", "synthetic", name
    )


def test_window_title_matches_project_name():
    projects_adapter = MiruProjectAdapter(_fixture("projects.json"))
    events_adapter = ActivityWatchAdapter(_fixture("events.json"))
    projects = projects_adapter.get_projects()
    events = events_adapter.get_events(user_id="designer_01")

    attributed = correlate_events(events, projects, user_id="designer_01")

    # At least one event should match "Sprinkler Design" project by title.
    sprinkler = next(p for p in projects if p.name == "Sprinkler Design - Stage 1")
    sprinkler_attr = [
        a for a in attributed if a.project_id == sprinkler.id
    ]
    assert len(sprinkler_attr) > 0, "Expected Sprinkler Design attribution"

    # All attributed records should reference a known project.
    project_ids = {p.id for p in projects}
    for a in attributed:
        assert a.project_id in project_ids
        assert 0.0 < a.confidence <= 1.0
        assert a.attributed_minutes > 0


def test_afk_events_are_not_attributed():
    projects_adapter = MiruProjectAdapter(_fixture("projects.json"))
    events_adapter = ActivityWatchAdapter(_fixture("events.json"))
    projects = projects_adapter.get_projects()
    events = events_adapter.get_events(user_id="designer_02")

    attributed = correlate_events(events, projects, user_id="designer_02")

    # evt_008 is AFK (10 min) — should not produce attributed time.
    afk_events = [e for e in events if e.is_afk]
    assert len(afk_events) == 1  # sanity: fixture has one AFK event
    afk_event_ids = {e.id for e in afk_events}
    attributed_event_ids = {a.activity_event_id for a in attributed}
    assert afk_event_ids.isdisjoint(attributed_event_ids)

    # All attributed minutes should be positive.
    for a in attributed:
        assert a.attributed_minutes > 0
