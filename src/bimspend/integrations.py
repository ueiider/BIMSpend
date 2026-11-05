"""Opt-in, synthetic-first integration boundary. Importing this module never connects."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import ipaddress
import json
from urllib.parse import quote, urlsplit
from urllib.request import urlopen

from bimspend.models import ActivityEvent, AttributedTime, Project, TimeEntry


def _utc(value: str) -> datetime:
    instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if instant.tzinfo is None:
        raise ValueError("Timezone offset is required")
    return instant.astimezone(timezone.utc)


def _event(source: str, key: str, user: str, app: str, title: str,
           start: datetime, end: datetime, kind: str = "active_window") -> ActivityEvent:
    if end <= start:
        raise ValueError("Event interval must be positive")
    external = str(key)
    return ActivityEvent(id="int_" + sha256(f"{source}:{external}".encode()).hexdigest()[:28],
                         source=source, external_id=external, user_id=user, app_name=app,
                         window_title=title, started_at=start.isoformat(), ended_at=end.isoformat(),
                         duration_minutes=(end - start).total_seconds() / 60,
                         is_afk=kind == "afk", event_type=kind)


def parse_activitywatch(bucket_id: str, bucket_type: str, rows: list[dict], user: str) -> list[ActivityEvent]:
    """Parse ActivityWatch window/AFK buckets; no network or watcher side effects."""
    if bucket_type not in ("currentwindow", "afkstatus"):
        return []
    out = []
    for row in rows:
        start = _utc(row["timestamp"])
        seconds = float(row["duration"])
        if seconds <= 0 or seconds > 86400:
            raise ValueError("Invalid ActivityWatch duration")
        data = row.get("data", {})
        kind = "afk" if bucket_type == "afkstatus" else "active_window"
        title = str(data.get("title", "")) if kind != "afk" else ""
        app = str(data.get("app", "")) if kind != "afk" else "ActivityWatch"
        if kind == "afk" and data.get("status") != "afk":
            continue
        key = f"{bucket_id}:{row['id']}" if "id" in row else f"{bucket_id}:{start.isoformat()}:{seconds}:{sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()}"
        out.append(_event("activitywatch", key, user, app, title, start,
                          start + timedelta(seconds=seconds), kind))
    return out


def parse_revit(rows: list[dict], user: str) -> list[ActivityEvent]:
    """Read-only versioned Revit companion events, never Revit API calls."""
    result = []
    for row in rows:
        if row.get("schema_version") != 1 or row.get("kind") not in ("active", "idle"):
            raise ValueError("Unsupported Revit event contract")
        if not row.get("document_id") or not row.get("event_id"):
            raise ValueError("Revit event identity is required")
        result.append(_event("revit", str(row["event_id"]), user, "Revit",
                             str(row["document_id"]), _utc(row["started_at"]),
                             _utc(row["ended_at"]), "afk" if row["kind"] == "idle" else "revit_active"))
    return result


class ActivityWatchLocalClient:
    """Explicitly invoked local API reader; default configuration forbids connections."""

    def __init__(self, endpoint: str = "http://127.0.0.1:5600", *, enabled: bool = False):
        parsed = urlsplit(endpoint)
        try:
            host = ipaddress.ip_address(parsed.hostname or "")
        except ValueError as exc:
            raise ValueError("Only literal IPv4 loopback endpoints are permitted") from exc
        if parsed.scheme != "http" or not host.is_loopback or host.version != 4 or parsed.username or parsed.password or parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            raise ValueError("Only plain HTTP IPv4 loopback endpoints are permitted")
        self.endpoint = endpoint.rstrip("/")
        self.enabled = enabled

    def _get(self, path: str):
        if not self.enabled:
            raise PermissionError("ActivityWatch connection disabled by default")
        with urlopen(self.endpoint + path, timeout=3) as response:
            return json.load(response)

    def buckets(self) -> dict:
        return self._get("/api/0/buckets/")

    def events(self, bucket_id: str, *, start: str, end: str) -> list[dict]:
        _utc(start)
        _utc(end)
        return self._get(f"/api/0/buckets/{quote(bucket_id, safe='')}/events?start={quote(start, safe='')}&end={quote(end, safe='')}")


@dataclass(frozen=True)
class AttributionRules:
    revit_documents: dict[str, str]
    applications: dict[str, str]


def suggest(events: list[ActivityEvent], projects: list[Project], rules: AttributionRules) -> list[AttributedTime]:
    """Compute disjoint suggestions, prioritizing Revit over overlapping window focus.

    Recalculation is deterministic. AFK intervals cut time from both sources;
    conflicts and unknown identity stay unassigned. No timesheet is approved.
    """
    unique = {(e.source, e.external_id): e for e in events}
    ordered = sorted(unique.values(), key=lambda e: (e.source, e.external_id))
    valid = {p.id for p in projects if not p.is_archived}
    result = []
    for event in ordered:
        if event.is_afk:
            continue
        start, end = _utc(event.started_at), _utc(event.ended_at)
        cuts = {start, end}
        for other in ordered:
            if other.user_id != event.user_id or other.id == event.id:
                continue
            a, b = _utc(other.started_at), _utc(other.ended_at)
            if a < end and b > start:
                cuts.update((max(start, a), min(end, b)))
        points = sorted(cuts)
        for index, (a, b) in enumerate(zip(points, points[1:])):
            if b <= a or any(e.is_afk and e.user_id == event.user_id and _utc(e.started_at) < b and _utc(e.ended_at) > a for e in ordered):
                continue
            competing = [e for e in ordered if not e.is_afk and e.user_id == event.user_id and _utc(e.started_at) < b and _utc(e.ended_at) > a]
            if event is not min(competing, key=lambda e: (0 if e.source == "revit" else 1, e.source, e.external_id)):
                continue
            mapped = rules.revit_documents.get(event.window_title) if event.source == "revit" else rules.applications.get(event.app_name)
            if mapped not in valid:
                mapped = None
            result.append(AttributedTime(id=f"seg_{event.id}_{index}", activity_event_id=event.id,
                                         project_id=mapped, attributed_minutes=(b - a).total_seconds() / 60,
                                         confidence=0.95 if mapped and event.source == "revit" else 0.7 if mapped else 0,
                                         correlation_method="revit_mapping" if mapped and event.source == "revit" else "app_rule" if mapped else "unassigned"))
    return result


class MiruMockExport:
    """Explicit, in-memory export ledger. No network endpoint is assumed."""

    def __init__(self):
        self.exported: dict[str, dict] = {}

    def export(self, entry_id: str, project_id: str, minutes: float, *, approved: bool, explicitly_requested: bool) -> dict:
        if not approved or not explicitly_requested:
            raise PermissionError("Approved time and explicit export action are required")
        return self.exported.setdefault(entry_id, {"entry_id": entry_id, "project_id": project_id, "minutes": minutes})


def _ingest_synthetic_batch(db, events: list[ActivityEvent], rules: AttributionRules) -> dict[str, int]:
    """Explicit synthetic batch import; never updates an existing suggestion/review.

    Preserves manual corrections and approved records on repeated imports.
    The caller must provide synthetic events; the routine never calls adapters.
    """
    if any(not e.external_id or e.source not in ("activitywatch", "revit") for e in events):
        raise ValueError("Only identified synthetic ActivityWatch/Revit events are accepted")
    inserted = [e for e in events if db.ingest_event(e)]
    existing = {s.id for s in db.list_attributed_time()}
    suggestions = suggest(inserted, db.list_projects(), rules)
    created = 0
    for suggestion in suggestions:
        if suggestion.id in existing:
            continue
        db.upsert_attributed_time(suggestion)
        existing.add(suggestion.id)
        if suggestion.project_id is None:
            continue
        source = next(e for e in inserted if e.id == suggestion.activity_event_id)
        project = db.get_project(suggestion.project_id)
        db.upsert_time_entry(TimeEntry(id="entry_" + suggestion.id,
                                       attributed_time_id=suggestion.id,
                                       project_id=project.id, user_id=source.user_id,
                                       minutes=suggestion.attributed_minutes,
                                       standard_rate=project.standard_rate,
                                       loaded_cost_rate=project.loaded_cost_rate),
                             actor_id="synthetic_import")
        created += 1
    return {"events": len(inserted), "suggestions": len(suggestions), "pending_entries": created}


def ingest_synthetic_batch(db, events: list[ActivityEvent], rules: AttributionRules) -> dict[str, int]:
    """Import all synthetic events and suggestions as one SQLite transaction."""
    with db.transaction():
        return _ingest_synthetic_batch(db, events, rules)
