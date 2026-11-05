"""Correlation layer: observed activity -> attributed project time.

Matches activity events to commercial projects using window-title
matching against project/client names, with user assignment as a
fallback. Returns attributed-time *suggestions* pending designer
review. Confidence reflects mapping certainty; low-confidence matches
are flagged for review.
"""

from __future__ import annotations

from typing import Any

from bimspend.models import ActivityEvent, AttributedTime, Project


def correlate_events(
    events: list[ActivityEvent],
    projects: list[Project],
    user_id: str | None = None,
) -> list[AttributedTime]:
    """Correlate activity events to projects.

    Strategy:
      1. If an event's window title contains the project name or client,
         attribute the event to that project (high confidence).
      2. Otherwise, if user_id is set, attribute to the user's default
         project (medium confidence).
      3. Otherwise, leave uncorrelated (no AttributedTime produced).

    Returns a list of AttributedTime domain objects (not yet persisted).
    """
    attributed: list[AttributedTime] = []
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()

    # Index projects by name/client for fast matching.
    by_name: dict[str, Project] = {}
    by_client: dict[str, Project] = {}
    for p in projects:
        by_name[p.name.lower()] = p
        by_client[p.client.lower()] = p

    user_projects = [p for p in projects]  # in a real system, filter by membership

    for event in events:
        if event.is_afk:
            continue  # skip idle/away time

        title = event.window_title.lower()
        matched_project: Project | None = None
        method = ""
        confidence = 0.0

        # 1. Exact/substring match on project name in window title.
        for name, proj in by_name.items():
            if name and name in title:
                matched_project = proj
                method = "window_title_match"
                confidence = 0.85
                break

        # 2. Fallback: match client name in window title.
        if matched_project is None:
            for client, proj in by_client.items():
                if client and client in title:
                    matched_project = proj
                    method = "client_title_match"
                    confidence = 0.6
                    break

        # 3. Fallback: assign to user's default project (medium-low conf).
        if matched_project is None and user_id and user_projects:
            matched_project = user_projects[0]
            method = "user_assignment"
            confidence = 0.35

        if matched_project is None:
            continue  # uncorrelated — no attributed time created

        # Attribute only the non-afk portion (already filtered above).
        attributed.append(
            AttributedTime(
                id=f"att_{event.id}",
                activity_event_id=event.id,
                project_id=matched_project.id,
                attributed_minutes=event.duration_minutes,
                confidence=confidence,
                correlation_method=method,
                created_at=now,
            )
        )

    return attributed
