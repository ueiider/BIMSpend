"""Correlation layer: observed activity -> attributed project time.

Matches activity events to commercial projects using window-title
matching against project/client names. Returns attributed-time
*suggestions* pending designer review.

Key rules:
- Ambiguous/unmatched events remain UNASSIGNED (project_id = None).
- No automatic attribution to the "first" project.
- AFK events are excluded from attribution.
- Confidence reflects mapping certainty; low-confidence matches are
  flagged for designer review.
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
         attribute the event to that project (medium-high confidence).
      2. If no title match, leave UNASSIGNED (project_id = None).
         No automatic fallback to the first project — ambiguous events
         stay unassigned until the designer explicitly maps them.
      3. AFK events are never attributed.

    Returns a list of AttributedTime domain objects (not yet persisted).
    """
    attributed: list[AttributedTime] = []
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()

    # Index projects by name/client for fast matching.
    by_name: dict[str, Project] = {}
    by_client: dict[str, Project] = {}
    for p in projects:
        if p.name:
            by_name[p.name.lower()] = p
        if p.client:
            by_client[p.client.lower()] = p

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

        # 2. Fallback: match client name in window title (lower confidence).
        if matched_project is None:
            for client, proj in by_client.items():
                if client and client in title:
                    matched_project = proj
                    method = "client_title_match"
                    confidence = 0.60
                    break

        # 3. NO automatic fallback to first project.
        #    Unmatched events remain unassigned (project_id = None).
        if matched_project is None:
            attributed.append(
                AttributedTime(
                    id=f"att_{event.id}",
                    activity_event_id=event.id,
                    project_id=None,  # unassigned — designer must map
                    attributed_minutes=event.duration_minutes,
                    confidence=0.0,
                    correlation_method="unassigned",
                    created_at=now,
                )
            )
            continue

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
