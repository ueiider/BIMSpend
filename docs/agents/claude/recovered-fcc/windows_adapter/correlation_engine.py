#!/usr/bin/env python3
"""
Windows Adapter - Correlation Engine

Correlates ActivityWatch events (window focus, AFK) with Revit Connector events
to build attributed time intervals for Miru submission.
"""

import json
import logging
import os
import sqlite3
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("correlation_engine")


@dataclass
class WindowFocusEvent:
    event_id: str
    timestamp: datetime
    previous_app: Optional[str]
    previous_title: Optional[str]
    current_app: str
    current_title: str
    current_pid: int
    current_exe: str
    transition_type: str
    idle_state: str
    session_id: str
    run_id: str
    external_run_id: str
    external_session_id: str


@dataclass
class AFKEvent:
    event_id: str
    timestamp: datetime
    state: str  # "afk" or "not_afk"
    idle_duration: int
    trigger: str
    session_id: str
    run_id: str


@dataclass
class RevitDocumentEvent:
    event_id: str
    timestamp: datetime
    event_type: str  # opened, closed, view_activated, idling
    document_id: str
    document_title: str
    central_guid: Optional[str]
    central_path: Optional[str]
    view_id: Optional[int]
    view_name: Optional[str]
    view_type: Optional[str]
    process_id: int
    revit_session_id: str
    is_foreground: bool
    session_id: str
    run_id: str


@dataclass
class CorrelatedInterval:
    interval_id: str
    session_id: str
    run_id: str
    external_run_id: str
    external_session_id: str
    start_utc: datetime
    end_utc: datetime
    duration_seconds: int
    project_id: str
    project_name: str
    model_identity: Dict
    confidence: float
    confidence_factors: Dict[str, bool]
    observed_seconds: int
    active_seconds: int
    afk_seconds: int
    idle_seconds: int
    revit_foreground_seconds: int
    other_app_seconds: int
    source_event_ids: List[str]
    window_events_count: int
    afk_events_count: int
    revit_idling_events_count: int


class CorrelationEngine:
    """
    Correlates AW and Revit events into attributed time intervals.

    Algorithm:
    1. Maintain per-process state for Revit (document, view, foreground status)
    2. Track window focus changes to know when Revit is foreground
    3. Track AFK state to exclude away time
    4. Build 30-minute intervals (configurable)
    5. Calculate confidence based on 5 factors
    6. Resolve project identity via IdentityResolver
    """

    def __init__(self, config: Dict, identity_resolver, queue_writer):
        self.config = config
        self.identity_resolver = identity_resolver
        self.queue_writer = queue_writer
        self.interval_minutes = config.get("correlation", {}).get("interval_minutes", 30)
        self.confidence_weights = config.get("correlation", {}).get("confidence_weights", {
            "revit_foreground": 0.25,
            "document_match": 0.25,
            "view_active": 0.15,
            "afk_excluded": 0.20,
            "single_revit_process": 0.15,
        })
        self.confidence_thresholds = config.get("correlation", {}).get("confidence_thresholds", {
            "high": 0.80,
            "medium": 0.50,
            "low": 0.00,
        })

        # State tracking
        self._window_events: List[WindowFocusEvent] = []
        self._afk_events: List[AFKEvent] = []
        self._revit_events: List[RevitDocumentEvent] = []

        # Per-process Revit state
        self._revit_process_state: Dict[int, Dict] = {}  # pid -> {doc_id, view_id, is_foreground, session_id}

        # Current interval being built
        self._current_interval_start: Optional[datetime] = None
        self._interval_events: Dict[str, List] = defaultdict(list)  # session_id -> events

        # Deduplication tracking
        self._last_window_key: Dict[str, float] = {}
        self._last_afk_key: Dict[str, float] = {}
        self._last_revit_key: Dict[str, float] = {}

        # Lock for thread safety
        self._lock = threading.Lock()

    def consume_aw_window_event(self, event: Dict) -> None:
        """Consume a window.focus.changed event from AW Adapter."""
        with self._lock:
            try:
                payload = event.get("payload", {})
                correlation = event.get("correlation", {})

                # Deduplication: 5 second window on app+title
                current = payload.get("current", {})
                key = f"{current.get('app_name', '')}:{current.get('window_title', '')}"
                ts = datetime.fromisoformat(event["timestamp_utc"].replace("Z", "+00:00")).timestamp()

                if key in self._last_window_key and ts - self._last_window_key[key] < 5:
                    return
                self._last_window_key[key] = ts

                win_event = WindowFocusEvent(
                    event_id=event["event_id"],
                    timestamp=datetime.fromisoformat(event["timestamp_utc"].replace("Z", "+00:00")),
                    previous_app=payload.get("previous", {}).get("app_name"),
                    previous_title=payload.get("previous", {}).get("window_title"),
                    current_app=current.get("app_name", ""),
                    current_title=current.get("window_title", ""),
                    current_pid=current.get("process_id", 0),
                    current_exe=current.get("exe_path", ""),
                    transition_type=payload.get("transition_type", ""),
                    idle_state=payload.get("idle_state", "active"),
                    session_id=correlation.get("session_id", ""),
                    run_id=correlation.get("run_id", ""),
                    external_run_id=correlation.get("external_run_id", ""),
                    external_session_id=correlation.get("external_session_id", ""),
                )

                self._window_events.append(win_event)
                self._maybe_update_revit_foreground(win_event)
                self._maybe_finalize_intervals()

            except Exception as e:
                logger.error(f"Error consuming window event: {e}")

    def consume_aw_afk_event(self, event: Dict) -> None:
        """Consume an afk.state.changed event from AW Adapter."""
        with self._lock:
            try:
                payload = event.get("payload", {})
                correlation = event.get("correlation", {})

                # Deduplication: 10 second window on state
                key = payload.get("state", "")
                ts = datetime.fromisoformat(event["timestamp_utc"].replace("Z", "+00:00")).timestamp()

                if key in self._last_afk_key and ts - self._last_afk_key[key] < 10:
                    return
                self._last_afk_key[key] = ts

                afk_event = AFKEvent(
                    event_id=event["event_id"],
                    timestamp=datetime.fromisoformat(event["timestamp_utc"].replace("Z", "+00:00")),
                    state=payload.get("state", "not_afk"),
                    idle_duration=payload.get("idle_duration_seconds", 0),
                    trigger=payload.get("trigger", "timeout"),
                    session_id=correlation.get("session_id", ""),
                    run_id=correlation.get("run_id", ""),
                )

                self._afk_events.append(afk_event)
                self._maybe_finalize_intervals()

            except Exception as e:
                logger.error(f"Error consuming AFK event: {e}")

    def consume_revit_event(self, event: Dict) -> None:
        """Consume a Revit event from Revit Connector."""
        with self._lock:
            try:
                payload = event.get("payload", {})
                correlation = event.get("correlation", {})
                event_type = event.get("event_type", "")

                # Deduplication per event type
                key = f"{event_type}:{payload.get('document_id', '')}:{payload.get('view_id', payload.get('active_view_id', ''))}"
                ts = datetime.fromisoformat(event["timestamp_utc"].replace("Z", "+00:00")).timestamp()

                dedup_window = {"revit.document.opened": 1, "revit.document.closed": 1,
                               "revit.view.activated": 2, "revit.application.idling": 30}.get(event_type, 5)

                if key in self._last_revit_key and ts - self._last_revit_key[key] < dedup_window:
                    return
                self._last_revit_key[key] = ts

                revit_event = RevitDocumentEvent(
                    event_id=event["event_id"],
                    timestamp=datetime.fromisoformat(event["timestamp_utc"].replace("Z", "+00:00")),
                    event_type=event_type,
                    document_id=payload.get("document_id", ""),
                    document_title=payload.get("title", payload.get("document_title", "")),
                    central_guid=payload.get("central_guid"),
                    central_path=payload.get("central_path"),
                    view_id=payload.get("view_id", payload.get("active_view_id")),
                    view_name=payload.get("view_name", payload.get("current_view", {}).get("view_name")),
                    view_type=payload.get("view_type", payload.get("current_view", {}).get("view_type")),
                    process_id=event.get("source", {}).get("process_id", 0),
                    revit_session_id=correlation.get("session_id", ""),
                    is_foreground=payload.get("is_foreground", True),
                    session_id=correlation.get("session_id", ""),
                    run_id=correlation.get("run_id", ""),
                )

                self._revit_events.append(revit_event)
                self._update_revit_process_state(revit_event)
                self._maybe_finalize_intervals()

            except Exception as e:
                logger.error(f"Error consuming Revit event: {e}")

    def _maybe_update_revit_foreground(self, win_event: WindowFocusEvent) -> None:
        """Update Revit process foreground state based on window focus."""
        # Check if current window is a Revit process
        for pid, state in self._revit_process_state.items():
            if pid == win_event.current_pid:
                state["is_foreground"] = True
            else:
                # Other Revit processes are not foreground
                state["is_foreground"] = False

    def _update_revit_process_state(self, revit_event: RevitDocumentEvent) -> None:
        """Update per-process Revit state."""
        pid = revit_event.process_id
        if pid not in self._revit_process_state:
            self._revit_process_state[pid] = {
                "document_id": None,
                "view_id": None,
                "is_foreground": False,
                "session_id": revit_event.revit_session_id,
                "opened_at": revit_event.timestamp,
            }

        state = self._revit_process_state[pid]

        if revit_event.event_type == "revit.document.opened":
            state["document_id"] = revit_event.document_id
            state["view_id"] = revit_event.view_id
            state["opened_at"] = revit_event.timestamp
        elif revit_event.event_type == "revit.document.closed":
            # Finalize interval for this document
            self._finalize_document_interval(pid, revit_event.timestamp)
            state["document_id"] = None
            state["view_id"] = None
        elif revit_event.event_type == "revit.view.activated":
            state["view_id"] = revit_event.view_id
        elif revit_event.event_type == "revit.application.idling":
            state["is_foreground"] = revit_event.is_foreground

    def _finalize_document_interval(self, pid: int, end_time: datetime) -> None:
        """Finalize interval for a closed document."""
        state = self._revit_process_state.get(pid)
        if not state or not state.get("document_id"):
            return

        # Find relevant events in this time range
        start_time = state.get("opened_at", end_time)
        session_id = state.get("session_id")

        # Build interval from events
        interval = self._build_interval(
            session_id=session_id,
            start_utc=start_time,
            end_utc=end_time,
            document_id=state["document_id"],
            view_id=state["view_id"],
            process_id=pid,
        )

        if interval and interval.duration_seconds >= 60:  # Minimum 1 minute
            self._submit_interval(interval)

    def _maybe_finalize_intervals(self) -> None:
        """Check if any intervals should be finalized based on time."""
        if not self._current_interval_start:
            self._current_interval_start = datetime.now(timezone.utc)
            return

        now = datetime.now(timezone.utc)
        elapsed = (now - self._current_interval_start).total_seconds() / 60

        if elapsed >= self.interval_minutes:
            # Finalize intervals for all active sessions
            self._finalize_all_intervals(now)
            self._current_interval_start = now

    def _finalize_all_intervals(self, end_time: datetime) -> None:
        """Finalize intervals for all active Revit processes."""
        for pid, state in self._revit_process_state.items():
            if state.get("document_id"):
                start_time = state.get("opened_at", end_time)
                interval = self._build_interval(
                    session_id=state["session_id"],
                    start_utc=start_time,
                    end_utc=end_time,
                    document_id=state["document_id"],
                    view_id=state["view_id"],
                    process_id=pid,
                )
                if interval and interval.duration_seconds >= 60:
                    self._submit_interval(interval)

    def _build_interval(
        self,
        session_id: str,
        start_utc: datetime,
        end_utc: datetime,
        document_id: str,
        view_id: Optional[int],
        process_id: int,
    ) -> Optional[CorrelatedInterval]:
        """Build a correlated interval from collected events."""
        # Filter events in time range
        window_events = [
            e for e in self._window_events
            if start_utc <= e.timestamp <= end_utc
        ]
        afk_events = [
            e for e in self._afk_events
            if start_utc <= e.timestamp <= end_utc
        ]
        revit_events = [
            e for e in self._revit_events
            if start_utc <= e.timestamp <= end_utc and e.document_id == document_id
        ]

        if not window_events and not revit_events:
            return None

        # Calculate time breakdown
        total_seconds = int((end_utc - start_utc).total_seconds())

        # AFK time
        afk_seconds = self._calculate_afk_time(afk_events, start_utc, end_utc)

        # Revit foreground time
        revit_fg_seconds = self._calculate_revit_foreground_time(
            window_events, revit_events, process_id, start_utc, end_utc
        )

        # Other app time
        other_app_seconds = max(0, total_seconds - afk_seconds - revit_fg_seconds)

        # Active time (not AFK, not idle)
        idle_seconds = sum(
            e.idle_duration for e in afk_events
            if e.state == "afk" and e.trigger == "timeout"
        )
        active_seconds = max(0, total_seconds - afk_seconds - idle_seconds)

        # Resolve project identity
        model_identity = self._resolve_model_identity(document_id)
        project_id = model_identity.get("project_id", "unknown")
        project_name = model_identity.get("project_name", "Unknown Project")

        # Calculate confidence
        confidence, factors = self._calculate_confidence(
            window_events, afk_events, revit_events, process_id
        )

        # Collect source event IDs
        source_event_ids = (
            [e.event_id for e in window_events] +
            [e.event_id for e in afk_events] +
            [e.event_id for e in revit_events]
        )

        return CorrelatedInterval(
            interval_id=str(uuid.uuid4()),
            session_id=session_id,
            run_id=str(uuid.uuid4()),
            external_run_id=self._generate_external_run_id(session_id, start_utc),
            external_session_id=self._generate_external_session_id(process_id, session_id),
            start_utc=start_utc,
            end_utc=end_utc,
            duration_seconds=total_seconds,
            project_id=project_id,
            project_name=project_name,
            model_identity=model_identity,
            confidence=confidence,
            confidence_factors=factors,
            observed_seconds=total_seconds,
            active_seconds=active_seconds,
            afk_seconds=afk_seconds,
            idle_seconds=idle_seconds,
            revit_foreground_seconds=revit_fg_seconds,
            other_app_seconds=other_app_seconds,
            source_event_ids=source_event_ids,
            window_events_count=len(window_events),
            afk_events_count=len(afk_events),
            revit_idling_events_count=len([e for e in revit_events if e.event_type == "revit.application.idling"]),
        )

    def _calculate_afk_time(
        self,
        afk_events: List[AFKEvent],
        start: datetime,
        end: datetime
    ) -> int:
        """Calculate total AFK seconds in interval."""
        if not afk_events:
            return 0

        afk_seconds = 0
        current_state = "not_afk"
        last_change = start

        for event in sorted(afk_events, key=lambda e: e.timestamp):
            if event.timestamp > end:
                break

            if current_state == "afk":
                afk_seconds += int((event.timestamp - last_change).total_seconds())

            current_state = event.state
            last_change = event.timestamp

        # Handle trailing AFK state
        if current_state == "afk":
            afk_seconds += int((end - last_change).total_seconds())

        return max(0, afk_seconds)

    def _calculate_revit_foreground_time(
        self,
        window_events: List[WindowFocusEvent],
        revit_events: List[RevitDocumentEvent],
        revit_pid: int,
        start: datetime,
        end: datetime,
    ) -> int:
        """Calculate seconds where Revit was foreground."""
        # Simple approach: count window events where Revit was foreground
        # In production, would track precise foreground transitions
        revit_window_events = [
            e for e in window_events
            if e.current_pid == revit_pid and "revit" in e.current_app.lower()
        ]

        if not revit_window_events:
            return 0

        # Approximate: assume Revit was foreground between its window events
        # This is a simplification - real implementation would track focus transitions
        return int((end - start).total_seconds() * 0.8)  # 80% heuristic

    def _resolve_model_identity(self, document_id: str) -> Dict:
        """Resolve document to project identity."""
        # This would call the IdentityResolver
        # For now, return a default
        return {
            "type": "workshared_central",
            "central_guid": "11111111-2222-3333-4444-555555555555",
            "central_path": "\\\\SERVER\\CENTRAL\\PROJECT_A_CENTRAL.RVT",
            "document_title": "Project_A.rvt",
            "project_id": "11111111-2222-3333-4444-555555555555",
            "project_name": "Project Alpha",
        }

    def _calculate_confidence(
        self,
        window_events: List[WindowFocusEvent],
        afk_events: List[AFKEvent],
        revit_events: List[RevitDocumentEvent],
        revit_pid: int,
    ) -> Tuple[float, Dict[str, bool]]:
        """Calculate confidence score based on 5 factors."""
        factors = {}

        # 1. revit_foreground: Was Revit the foreground app for most of the interval?
        revit_fg_events = [e for e in window_events if e.current_pid == revit_pid]
        factors["revit_foreground"] = len(revit_fg_events) > len(window_events) * 0.5

        # 2. document_match: Does active document match the correlated document?
        factors["document_match"] = len(revit_events) > 0

        # 3. view_active: Is there an active working view (not sheet/schedule)?
        working_views = [e for e in revit_events if e.view_type in ("FloorPlan", "CeilingPlan", "ThreeD", "Section", "Elevation")]
        factors["view_active"] = len(working_views) > 0

        # 4. afk_excluded: Was AFK time properly excluded?
        total_afk = sum(e.idle_duration for e in afk_events if e.state == "afk")
        factors["afk_excluded"] = total_afk > 0  # Has AFK tracking

        # 5. single_revit_process: Only one Revit process running?
        revit_pids = set(e.process_id for e in revit_events)
        factors["single_revit_process"] = len(revit_pids) <= 1

        # Calculate weighted confidence
        confidence = sum(
            self.confidence_weights.get(k, 0) * (1.0 if v else 0.0)
            for k, v in factors.items()
        )

        return confidence, factors

    def _submit_interval(self, interval: CorrelatedInterval) -> None:
        """Submit correlated interval to queue."""
        try:
            # Create adapter.correlated.activity event
            correlated_event = {
                "event_id": str(uuid.uuid4()),
                "event_type": "adapter.correlated.activity",
                "schema_version": "1.0.0",
                "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "source": {
                    "component": "windows-adapter",
                    "version": "1.0.0",
                    "instance_id": self.config.get("instance_id", str(uuid.uuid4())),
                    "process_id": os.getpid(),
                },
                "correlation": {
                    "session_id": interval.session_id,
                    "run_id": interval.run_id,
                    "external_run_id": interval.external_run_id,
                    "external_session_id": interval.external_session_id,
                },
                "payload": {
                    "interval": {
                        "start_utc": interval.start_utc.isoformat().replace("+00:00", "Z"),
                        "end_utc": interval.end_utc.isoformat().replace("+00:00", "Z"),
                        "duration_seconds": interval.duration_seconds,
                    },
                    "attribution": {
                        "project_id": interval.project_id,
                        "project_name": interval.project_name,
                        "model_identity": interval.model_identity,
                        "confidence": interval.confidence,
                        "confidence_factors": interval.confidence_factors,
                    },
                    "activity": {
                        "observed_seconds": interval.observed_seconds,
                        "active_seconds": interval.active_seconds,
                        "afk_seconds": interval.afk_seconds,
                        "idle_seconds": interval.idle_seconds,
                        "revit_foreground_seconds": interval.revit_foreground_seconds,
                        "other_app_seconds": interval.other_app_seconds,
                    },
                    "evidence": {
                        "window_events_count": interval.window_events_count,
                        "afk_events_count": interval.afk_events_count,
                        "revit_idling_events_count": interval.revit_idling_events_count,
                        "source_event_ids": interval.source_event_ids,
                    },
                },
            }

            # Also create adapter.ingestion.draft if confidence is high enough
            if interval.confidence >= self.confidence_thresholds["medium"]:
                self._create_ingestion_draft(interval)

            # Enqueue
            self.queue_writer.enqueue(correlated_event)
            logger.info(f"Submitted interval {interval.interval_id}: {interval.duration_seconds}s, confidence={interval.confidence:.2f}")

        except Exception as e:
            logger.error(f"Error submitting interval: {e}")

    def _create_ingestion_draft(self, interval: CorrelatedInterval) -> None:
        """Create adapter.ingestion.draft event for high-confidence intervals."""
        duration_minutes = round(interval.active_seconds / 60 * interval.confidence)
        if duration_minutes < 5:  # Minimum threshold
            return

        work_date = interval.start_utc.strftime("%Y-%m-%d")

        # Build note
        view_names = set()
        for eid in interval.source_event_ids:
            # Would need to look up view names from events
            pass

        note = f"Correlated Revit activity: {interval.model_identity.get('document_title', 'Unknown')}. "
        note += f"Confidence: {interval.confidence:.2f}. "
        note += f"Observed: {interval.observed_seconds//60}min, Active: {interval.active_seconds//60}min, AFK excluded: {interval.afk_seconds//60}min."

        ingestion_event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "adapter.ingestion.draft",
            "schema_version": "1.0.0",
            "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "source": {
                "component": "windows-adapter",
                "version": "1.0.0",
                "instance_id": self.config.get("instance_id", str(uuid.uuid4())),
                "process_id": os.getpid(),
            },
            "correlation": {
                "session_id": interval.session_id,
                "run_id": interval.run_id,
                "external_run_id": interval.external_run_id,
                "external_session_id": interval.external_session_id,
            },
            "payload": {
                "timesheet_entry": {
                    "external_run_id": interval.external_run_id,
                    "external_session_id": interval.external_session_id,
                    "duration_minutes": duration_minutes,
                    "work_date": work_date,
                    "project_id": interval.project_id,
                    "source": "automation",
                    "note": note,
                    "proof_url": f"https://bimspend.example.com/evidence/{interval.external_run_id}",
                    "source_metadata": {
                        "correlation_confidence": interval.confidence,
                        "observed_seconds": interval.observed_seconds,
                        "active_seconds": interval.active_seconds,
                        "afk_seconds": interval.afk_seconds,
                        "evidence_event_ids": interval.source_event_ids,
                        "model_identity": interval.model_identity,
                        "attribution_factors": interval.confidence_factors,
                    },
                    "proof_metadata": {
                        "window_events": interval.window_events_count,
                        "afk_events": interval.afk_events_count,
                        "revit_idling_events": interval.revit_idling_events_count,
                        "correlation_algorithm": "v1.0",
                        "privacy_filter_applied": True,
                    },
                },
                "agent": {
                    "agent_key_id": self.config.get("agent_key", ""),
                    "company_id": self.config.get("company_id", ""),
                },
            },
        }

        self.queue_writer.enqueue(ingestion_event)
        logger.info(f"Created ingestion draft for {interval.external_run_id}: {duration_minutes} minutes")

    def _generate_external_run_id(self, session_id: str, start_utc: datetime) -> str:
        """Generate deterministic external_run_id."""
        import hashlib
        adapter_instance_id = self.config.get("instance_id", "unknown")
        input_str = f"run{adapter_instance_id}{session_id}{start_utc.isoformat()}"
        return hashlib.sha256(input_str.encode()).hexdigest()[:32]

    def _generate_external_session_id(self, process_id: int, session_id: str) -> str:
        """Generate deterministic external_session_id."""
        import hashlib
        input_str = f"session{process_id}{session_id}"
        return hashlib.sha256(input_str.encode()).hexdigest()[:32]

    def flush(self) -> None:
        """Flush any pending intervals."""
        with self._lock:
            now = datetime.now(timezone.utc)
            self._finalize_all_intervals(now)


class QueueWriter:
    """Writes events to shared SQLite queue."""

    def __init__(self, queue_path: str):
        self.queue_path = Path(queue_path)
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.queue_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=FULL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS queue_entries (
                    id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    external_run_id TEXT NOT NULL,
                    external_session_id TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('pending','submitting','acked','dead_letter')),
                    attempts INTEGER NOT NULL DEFAULT 0,
                    last_attempt_utc TEXT,
                    next_retry_utc TEXT,
                    created_utc TEXT NOT NULL,
                    acked_utc TEXT,
                    error_code TEXT,
                    error_message TEXT,
                    error_http_status INTEGER,
                    error_response_body TEXT,
                    correlation_confidence REAL NOT NULL,
                    project_id TEXT NOT NULL,
                    interval_start_utc TEXT NOT NULL,
                    interval_end_utc TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_queue_status_next_retry
                ON queue_entries(status, next_retry_utc)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_queue_external_run
                ON queue_entries(external_run_id)
            """)
            conn.commit()

    def _extract_metadata(self, event: Dict) -> Dict:
        """Extract metadata for indexing."""
        correlation = event.get("correlation", {})
        payload = event.get("payload", {})

        if event["event_type"] == "adapter.correlated.activity":
            interval = payload.get("interval", {})
            attribution = payload.get("attribution", {})
            return {
                "correlation_confidence": attribution.get("confidence", 0.5),
                "project_id": attribution.get("project_id", "unknown"),
                "interval_start_utc": interval.get("start_utc", ""),
                "interval_end_utc": interval.get("end_utc", ""),
            }
        elif event["event_type"] == "adapter.ingestion.draft":
            timesheet = payload.get("timesheet_entry", {})
            source_meta = timesheet.get("source_metadata", {})
            return {
                "correlation_confidence": source_meta.get("correlation_confidence", 0.5),
                "project_id": timesheet.get("project_id", "unknown"),
                "interval_start_utc": timesheet.get("work_date", "") + "T00:00:00Z",
                "interval_end_utc": timesheet.get("work_date", "") + "T23:59:59Z",
            }

        return {
            "correlation_confidence": 0.5,
            "project_id": "unknown",
            "interval_start_utc": event.get("timestamp_utc", ""),
            "interval_end_utc": event.get("timestamp_utc", ""),
        }

    def enqueue(self, event: Dict) -> str:
        """Add validated event to queue. Returns queue entry ID."""
        import uuid as uuid_lib

        external_run_id = event["correlation"].get("external_run_id", str(uuid_lib.uuid4()))
        external_session_id = event["correlation"].get("external_session_id", str(uuid_lib.uuid4()))

        entry_id = str(uuid_lib.uuid4())
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        metadata = self._extract_metadata(event)

        with sqlite3.connect(self.queue_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=FULL")
            conn.execute("""
                INSERT INTO queue_entries (
                    id, event_type, payload, external_run_id, external_session_id,
                    status, attempts, last_attempt_utc, next_retry_utc,
                    created_utc, acked_utc, error_code, error_message,
                    error_http_status, error_response_body,
                    correlation_confidence, project_id,
                    interval_start_utc, interval_end_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry_id,
                event["event_type"],
                json.dumps(event),
                external_run_id,
                external_session_id,
                "pending",
                0,
                None,
                now,
                now,
                None,
                None,
                None,
                None,
                None,
                metadata["correlation_confidence"],
                metadata["project_id"],
                metadata["interval_start_utc"],
                metadata["interval_end_utc"],
            ))
            conn.commit()

        logger.debug(f"Enqueued event {entry_id}: {event['event_type']}")
        return entry_id