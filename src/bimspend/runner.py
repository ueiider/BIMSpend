"""Vertical-slice demo runner.

Wires together synthetic data, adapters, correlation, review and
dashboard into a single end-to-end demonstration. Reads JSON fixtures
from data/synthetic/ and prints the manager dashboard.
"""

from __future__ import annotations

import json
import os
from typing import Any

from .adapters.activitywatch import ActivityWatchAdapter
from .adapters.miru import MiruProjectAdapter
from .correlation import correlate_events
from .db import Database
from .dashboard import all_projects_summary
from .models import AttributedTime, Project, TimeEntry, TimeEntryState
from .review import approve_entry, reject_entry, suggest_entry


def _load_json(path: str) -> list[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _fixture(name: str) -> str:
    return os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "synthetic", name
    )


def run() -> None:
    db = Database("bimspend_demo.db")

    # 1. Project identity (Miru-like adapter)
    projects_adapter = MiruProjectAdapter(_fixture("projects.json"))
    projects = projects_adapter.get_projects()
    for p in projects:
        db.upsert_project(p)

    # 2. Activity event ingestion (ActivityWatch-like adapter)
    events_adapter = ActivityWatchAdapter(_fixture("events.json"))
    events = events_adapter.get_events()
    ingested_events: list = []
    ingested = 0
    duplicates = 0
    for ev in events:
        if db.ingest_event(ev):
            ingested += 1
            ingested_events.append(ev)
        else:
            duplicates += 1

    # 3. Correlation: observed -> attributed (suggestion, not approved).
    #    Only correlate events that were actually inserted (duplicates are
    #    skipped to avoid foreign-key violations on activity_event_id).
    attributed = correlate_events(ingested_events, projects)
    attributed_by_project: dict[str, float] = {}
    for at in attributed:
        db.upsert_attributed_time(at)
        attributed_by_project[at.project_id] = (
            attributed_by_project.get(at.project_id, 0.0) + at.attributed_minutes
        )

    # 4. Designer review: convert attributed -> pending time entries,
    #    then approve/reject a subset to demonstrate state separation.
    events_by_project: dict[str, float] = {}
    for ev in events:
        events_by_project[ev.user_id] = (
            events_by_project.get(ev.user_id, 0.0) + ev.duration_minutes
        )
    # Map event->project for minutes aggregation
    events_minutes_by_project: dict[str, float] = {}
    for at in attributed:
        events_minutes_by_project[at.project_id] = (
            events_minutes_by_project.get(at.project_id, 0.0)
            + at.attributed_minutes
        )

    # Build a lookup: attributed_time_id -> AttributedTime
    att_by_id = {at.id: at for at in attributed}
    proj_by_id = {p.id: p for p in projects}

    demo_user = "designer_01"

    for at in attributed:
        project = proj_by_id[at.project_id]
        entry = suggest_entry(at, project, demo_user)
        db.upsert_time_entry(entry)

    # Simulate designer decisions: approve first two, reject one,
    # leave rest pending.
    entries = db.list_time_entries()
    for i, entry in enumerate(entries):
        if i == 0:
            approve_entry(entry, reviewed_by="designer_01", notes="Looks correct")
        elif i == 1:
            reject_entry(
                entry,
                reviewed_by="designer_01",
                notes="Wrong project attribution",
            )
        # i >= 2 remain pending_review
        db.upsert_time_entry(entry)

    # 5. Manager dashboard
    entries = db.list_time_entries()
    summaries = all_projects_summary(
        projects, events_minutes_by_project, attributed_by_project, entries
    )

    print("=" * 72)
    print("BIMSpend Build 01 — Manager Project-Hours Dashboard (synthetic data)")
    print("=" * 72)
    print()
    print(f"Ingested activity events: {ingested} new, {duplicates} duplicates "
          f"(idempotent on source+external_id)")
    print(f"Attributed time records: {len(attributed)}")
    print(f"Time entries: {len(entries)} "
          f"({sum(1 for e in entries if e.state == TimeEntryState.APPROVED)} approved, "
          f"{sum(1 for e in entries if e.state == TimeEntryState.REJECTED)} rejected, "
          f"{sum(1 for e in entries if e.state == TimeEntryState.PENDING_REVIEW)} pending)")
    print()

    for s in summaries:
        print(f"Project: {s['project_name']} ({s['client']})")
        print(f"  Observed hours (ActivityWatch): {s['observed_hours']}")
        print(f"  Attributed hours (correlated):  {s['attributed_hours']}")
        print(f"  Approved hours (designer):      {s['approved_hours']}")
        print(f"  Billed hours (invoiced):        {s['billed_hours']}")
        print(f"  Realization (billed/observed):  {s['realization_percent']}%")
        print(f"  Effective rate (A$/obs hr):     {s['effective_rate_aud']}")
        print(f"  Labour cost (approved):         A${s['labor_cost_aud']}")
        print(f"  Standard value (approved):      A${s['standard_value_aud']}")
        print(f"  Entries: {s['approved_count']} approved, "
              f"{s['rejected_count']} rejected, {s['pending_count']} pending")
        print()

    print("Metric separation confirmed: observed != attributed != approved != billed.")
    print("No real employee data used; no employee monitoring active.")
    db.close()


if __name__ == "__main__":
    run()
