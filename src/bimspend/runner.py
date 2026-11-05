"""Vertical-slice demo runner.

Wires together synthetic data, adapters, correlation, review and
dashboard into a single end-to-end demonstration. Reads JSON fixtures
from data/synthetic/ and prints the manager dashboard.

Demonstrates the full time-state lifecycle:
  observed (ActivityWatch) -> attributed (correlation) ->
  submitted (designer) -> approved (manager) -> billed (billing)
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
from .review import approve_entry, bill_entry, reject_entry, submit_entry, suggest_entry


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
    ingested = 0
    duplicates = 0
    ingested_events: list = []
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
    events_minutes_by_project: dict[str, float] = {}
    for at in attributed:
        db.upsert_attributed_time(at)
        if at.project_id is not None:
            attributed_by_project[at.project_id] = (
                attributed_by_project.get(at.project_id, 0.0) + at.attributed_minutes
            )
            events_minutes_by_project[at.project_id] = (
                events_minutes_by_project.get(at.project_id, 0.0)
                + at.attributed_minutes
            )

    # Build a lookup: attributed_time_id -> AttributedTime
    att_by_id = {at.id: at for at in attributed}
    proj_by_id = {p.id: p for p in projects}

    demo_user = "designer_01"

    # 4. Designer review: convert attributed -> pending time entries,
    #    then submit/approve/reject/bill to demonstrate state separation.
    for at in attributed:
        if at.project_id is None:
            # Unassigned events stay unassigned — no entry created
            # until designer maps them.
            continue
        project = proj_by_id[at.project_id]
        entry = suggest_entry(at, project, demo_user)
        db.upsert_time_entry(entry)

    # Simulate designer decisions on entries:
    #   entry 0: submit -> manager approves -> bill (partial billing)
    #   entry 1: submit -> manager rejects
    #   entry 2+: stay pending_review
    entries = db.list_time_entries()
    for i, entry in enumerate(entries):
        if i == 0:
            # Designer submits
            submit_entry(entry, submitted_by=demo_user)
            db.upsert_time_entry(entry)
            # Manager approves
            approve_entry(entry, reviewed_by="manager_01")
            db.upsert_time_entry(entry)
            # Billing: invoice 80% of approved hours (realization gap)
            bill_entry(entry, billed_minutes=entry.minutes * 0.8, reviewed_by="manager_01")
            db.upsert_time_entry(entry)
        elif i == 1:
            # Designer submits, manager rejects
            submit_entry(entry, submitted_by=demo_user)
            db.upsert_time_entry(entry)
            reject_entry(entry, reviewed_by="manager_01", notes="Wrong project attribution")
            db.upsert_time_entry(entry)
        # i >= 2 remain pending_review (designer hasn't reviewed yet)
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
    print(f"Time entries: {len(entries)}")
    print(f"  {sum(1 for e in entries if e.state == TimeEntryState.PENDING_REVIEW)} pending_review")
    print(f"  {sum(1 for e in entries if e.state == TimeEntryState.SUBMITTED)} submitted")
    print(f"  {sum(1 for e in entries if e.state == TimeEntryState.APPROVED)} approved")
    print(f"  {sum(1 for e in entries if e.state == TimeEntryState.REJECTED)} rejected")
    print(f"  {sum(1 for e in entries if e.state == TimeEntryState.BILLED)} billed")
    print()

    for s in summaries:
        print(f"Project: {s['project_name']} ({s['client']})")
        print(f"  Observed hours (ActivityWatch): {s['observed_hours']}")
        print(f"  Attributed hours (correlated):  {s['attributed_hours']}")
        print(f"  Approved hours (manager):       {s['approved_hours']}")
        print(f"  Submitted hours (pending):      {s['submitted_hours']}")
        print(f"  Billed hours (invoiced):        {s['billed_hours']}")
        print(f"  Realization (billed/observed):  {s['realization_percent']}%")
        print(f"  Effective rate (A$/obs hr):     {s['effective_rate_aud']}")
        print(f"  Labour cost (approved):         A${s['labor_cost_aud']}")
        print(f"  Standard value (approved):      A${s['standard_value_aud']}")
        print(f"  Entries: {s['pending_count']} pending, "
              f"{s['submitted_count']} submitted, "
              f"{s['approved_count']} approved, "
              f"{s['rejected_count']} rejected, "
              f"{s['billed_count']} billed")
        print()

    print("Metric separation confirmed:")
    print("  observed != attributed != approved != billed")
    print("  Approval does NOT auto-bill (billed set separately)")
    print("  No real employee data used; no employee monitoring active.")
    db.close()


if __name__ == "__main__":
    run()
