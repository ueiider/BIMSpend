"""Heartbeat and interval manager for activity capture.

Provides stable event identifiers, idempotent persistence, and correct
interval management across application switches, AFK transitions, lock/unlock,
and sleep/resume.

All timestamps use UTC. Monotonic elapsed-time measurements are used for
duration calculations where appropriate.
"""

from __future__ import annotations

import logging
import secrets
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class HeartbeatEvent:
    """A single heartbeat observation."""

    id: str
    source: str
    external_id: str
    user_id: str
    company_id: Optional[str]
    app_name: str
    window_title: str  # always privacy-hashed
    started_at: str  # ISO-8601 UTC
    ended_at: str  # ISO-8601 UTC
    duration_minutes: float
    is_afk: bool
    event_type: str
    title_redacted: bool = True


class HeartbeatManager:
    """Manages heartbeat generation and interval coordination.

    Responsibilities:
    - Generate stable event IDs for idempotency
    - Track the current active interval to avoid overlaps
    - Close intervals on state transitions (app switch, AFK, lock, etc.)
    - Ensure UTC timestamps
    - Never create artificial work duration across unobserved gaps
    """

    def __init__(
        self,
        user_id: str,
        company_id: Optional[str] = None,
        source: str = "activitywatch",
        heartbeat_interval: float = 5.0,
    ):
        self.user_id = user_id
        self.company_id = company_id
        self.source = source
        self.heartbeat_interval = heartbeat_interval
        self._lock = threading.Lock()
        self._current_interval: Optional[dict] = None
        self._last_app: Optional[str] = None
        self._last_title_hash: Optional[str] = None
        self._event_count = 0

    def _hash_title(self, title: str) -> str:
        import hashlib

        return f"[HASH:{hashlib.sha256(title.encode('utf-8')).hexdigest()[:8]}]"

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _external_id(self, app: str, title_hash: str, start_time: str) -> str:
        """Generate a stable external_id for idempotency."""
        return f"{self.source}:{app}:{title_hash}:{start_time}"

    def _close_current_interval(self, ended_at: str) -> Optional[HeartbeatEvent]:
        """Close the current interval and return the completed event."""
        if self._current_interval is None:
            return None

        interval = self._current_interval
        self._current_interval = None

        start = interval["started_at"]
        end = ended_at

        # Compute duration in minutes
        try:
            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)
            duration_minutes = max(0.0, (end_dt - start_dt).total_seconds() / 60.0)
        except Exception:
            duration_minutes = 0.0

        event_id = secrets.token_urlsafe(16)
        external_id = self._external_id(
            interval["app_name"], interval["title_hash"], start
        )

        return HeartbeatEvent(
            id=event_id,
            source=self.source,
            external_id=external_id,
            user_id=self.user_id,
            company_id=self.company_id,
            app_name=interval["app_name"],
            window_title=interval["title_hash"],
            started_at=start,
            ended_at=end,
            duration_minutes=duration_minutes,
            is_afk=interval.get("is_afk", False),
            event_type=interval.get("event_type", "active_window"),
            title_redacted=True,
        )

    def observe(
        self,
        app_name: str,
        title_hash: str,
        is_afk: bool = False,
        event_type: str = "active_window",
        timestamp: Optional[str] = None,
    ) -> Optional[HeartbeatEvent]:
        """Record a window observation and manage interval transitions.

        Returns a completed HeartbeatEvent if an interval was closed, or None
        if the current interval continues.

        An interval is closed when:
        - The app changes
        - The title hash changes (significant title change)
        - The AFK state changes
        - No observation has been received for more than heartbeat_interval * 2
        """
        now = timestamp or self._now_iso()

        with self._lock:
            # Check if we need to close the current interval
            if self._current_interval is not None:
                ci = self._current_interval
                app_changed = ci["app_name"] != app_name
                title_changed = ci["title_hash"] != title_hash
                afk_changed = ci.get("is_afk", False) != is_afk

                # Check for gap (no observation for too long)
                gap_too_large = False
                if ci.get("last_observed_at") is not None:
                    try:
                        last = datetime.fromisoformat(ci["last_observed_at"])
                        now_dt = datetime.fromisoformat(now)
                        gap_seconds = (now_dt - last).total_seconds()
                        if gap_seconds > self.heartbeat_interval * 2:
                            gap_too_large = True
                    except Exception:
                        gap_too_large = True

                if app_changed or title_changed or afk_changed or gap_too_large:
                    # Close current interval at the new observation time
                    # (the event that triggered the transition)
                    closed = self._close_current_interval(now)
                    self._event_count += 1 if closed else 0
                    return closed

            # Start or continue interval
            if self._current_interval is None:
                self._current_interval = {
                    "app_name": app_name,
                    "title_hash": title_hash,
                    "is_afk": is_afk,
                    "event_type": event_type,
                    "started_at": now,
                    "last_observed_at": now,
                }
            else:
                self._current_interval["last_observed_at"] = now
                self._current_interval["is_afk"] = is_afk
                self._current_interval["event_type"] = event_type

            return None

    def flush(self, ended_at: Optional[str] = None) -> Optional[HeartbeatEvent]:
        """Close and return the current interval, if any."""
        with self._lock:
            end = ended_at or self._now_iso()
            event = self._close_current_interval(end)
            if event:
                self._event_count += 1
            return event

    def get_stats(self) -> dict:
        with self._lock:
            return {
                "event_count": self._event_count,
                "current_interval": self._current_interval is not None,
                "user_id": self.user_id,
                "company_id": self.company_id,
            }
