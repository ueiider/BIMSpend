"""Local synthetic reporting. No raw window titles or network operations."""
from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from bimspend.db import Database
from bimspend.models import TimeEntryState

HEADERS = ("section", "project_id", "project_name", "user_id", "work_date",
           "state", "confirmed_hours", "approved_hours", "billed_hours",
           "labor_cost_aud", "billed_value_aud", "budget_aud")


def build_report(db: Database, start: str | None = None,
                 end: str | None = None) -> list[dict[str, Any]]:
    start_date = date.fromisoformat(start) if start else None
    end_date = date.fromisoformat(end) if end else None
    if start_date and end_date and start_date > end_date:
        raise ValueError("Start date must be on or before end date.")
    projects = {p.id: p for p in db.list_projects()}
    attributed = {a.id: a for a in db.list_attributed_time()}
    events = {e.id: e for e in db.list_events()}
    rows: list[dict[str, Any]] = []
    for entry in db.list_time_entries():
        link = attributed.get(entry.attributed_time_id)
        event = events.get(link.activity_event_id) if link else None
        if not event:
            continue
        work_date = date.fromisoformat(event.started_at[:10])
        if start_date and work_date < start_date or end_date and work_date > end_date:
            continue
        project = projects.get(entry.project_id)
        approved = entry.state in (TimeEntryState.APPROVED, TimeEntryState.BILLED)
        rows.append(dict(section="Timesheets", project_id=entry.project_id,
                         project_name=project.name if project else "Unknown",
                         user_id=entry.user_id, work_date=work_date.isoformat(),
                         state=entry.state.value,
                         confirmed_hours=round(entry.minutes / 60, 2),
                         approved_hours=round(entry.minutes / 60, 2) if approved else 0,
                         billed_hours=round(entry.billed_minutes / 60, 2),
                         labor_cost_aud=round(entry.labor_cost, 2) if approved else 0,
                         billed_value_aud=round(entry.billed_minutes / 60 * entry.standard_rate, 2),
                         budget_aud=project.budget_aud if project else None))
    return rows


def aggregate(rows: list[dict[str, Any]], section: str) -> list[dict[str, Any]]:
    if section not in ("Projects", "Team", "Costs"):
        raise ValueError("Unknown summary.")
    key = "user_id" if section == "Team" else "project_id"
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        k = str(row[key])
        if k not in grouped:
            grouped[k] = dict.fromkeys(HEADERS, "")
            grouped[k].update(section=section, project_id=row["project_id"]
                              if section != "Team" else "",
                              project_name=row["project_name"] if section != "Team" else "",
                              user_id=row["user_id"] if section == "Team" else "",
                              budget_aud=row["budget_aud"] if section != "Team" else "")
            for field in ("confirmed_hours", "approved_hours", "billed_hours",
                          "labor_cost_aud", "billed_value_aud"):
                grouped[k][field] = 0.0
        for field in ("confirmed_hours", "approved_hours", "billed_hours",
                      "labor_cost_aud", "billed_value_aud"):
            grouped[k][field] += row[field]
    for item in grouped.values():
        for field in ("confirmed_hours", "approved_hours", "billed_hours",
                      "labor_cost_aud", "billed_value_aud"):
            item[field] = round(item[field], 2)
    return list(grouped.values())


def export_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    """Export a local CSV, neutralizing spreadsheet formula prefixes."""
    def safe(value: Any) -> Any:
        if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
            return "'" + value
        return value
    with open(path, "w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=HEADERS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: safe(row.get(k, "")) for k in HEADERS})
