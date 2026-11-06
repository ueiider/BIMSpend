"""Capture controller — BIMSpend proprietary orchestration layer.

Manages the capture lifecycle (Stopped/Running/Paused/Error), user consent,
company-scoped authorization, and SQLite persistence of activity events.

This is BIMSpend proprietary code — it does not modify ActivityWatch covered
files. It communicates with activitywatch_derived through well-defined
interfaces.
"""

from __future__ import annotations

import logging
import secrets
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Optional

from bimspend.auth import current_auth
from bimspend.db import Database
from bimspend.identity import Role
from bimspend.models import ActivityEvent

logger = logging.getLogger(__name__)


class CaptureState(Enum):
    """Capture lifecycle states."""

    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class CaptureConfig:
    """Configuration for the capture controller."""

    poll_time: float = 5.0  # seconds between window polls
    consent_required: bool = True  # explicit consent needed to start
    company_id: Optional[str] = None  # company scope for events
    member_id: Optional[str] = None  # authenticated member id
    session_id: Optional[str] = None  # active session id
    privacy_rules: Optional[list] = None  # privacy filter rules
    exclude_title: bool = False
    exclude_titles: Optional[list] = None
    exclude_apps: Optional[list] = None


@dataclass
class ConsentRecord:
    """Records user consent for capture."""

    granted: bool = False
    granted_at: Optional[str] = None
    granted_by: Optional[str] = None
    revoked_at: Optional[str] = None
    revoked_by: Optional[str] = None


class CaptureController:
    """Controls native Windows foreground-window capture.

    States:
        STOPPED  - capture not running, no events collected
        RUNNING  - capture actively polling and persisting events
        PAUSED   - capture suspended (no events, resources retained)
        ERROR    - capture encountered a fatal error

    Capture is disabled by default. Starting requires explicit consent and
    a valid authenticated session with company scope.
    """

    def __init__(self, db: Database, config: Optional[CaptureConfig] = None):
        self.db = db
        self.config = config or CaptureConfig()
        self.state = CaptureState.STOPPED
        self.consent = ConsentRecord()
        self._loop_thread: Optional[threading.Thread] = None
        self._loop: Optional[object] = None  # HeartbeatLoop instance
        self._lock = threading.Lock()
        self._last_window: Optional[dict] = None
        self._last_window_time: Optional[float] = None
        self._session_started_at: Optional[str] = None

    # ------------------------------------------------------------------
    # Consent
    # ------------------------------------------------------------------

    def grant_consent(self, granted_by: str) -> None:
        """Record explicit user consent to start capture."""
        self.consent.granted = True
        self.consent.granted_at = datetime.now(timezone.utc).isoformat()
        self.consent.granted_by = granted_by
        self.consent.revoked_at = None
        self.consent.revoked_by = None
        logger.info("Capture consent granted by %s", granted_by)

    def revoke_consent(self, revoked_by: str) -> None:
        """Revoke consent and stop capture if running."""
        self.consent.granted = False
        self.consent.revoked_at = datetime.now(timezone.utc).isoformat()
        self.consent.revoked_by = revoked_by
        logger.info("Capture consent revoked by %s", revoked_by)
        if self.state in (CaptureState.RUNNING, CaptureState.PAUSED):
            self.stop()

    def has_consent(self) -> bool:
        return self.consent.granted and self.consent.revoked_at is None

    # ------------------------------------------------------------------
    # Authentication / company scope validation
    # ------------------------------------------------------------------

    def _validate_auth(self) -> None:
        """Validate that an authenticated actor exists with company scope.

        Fail-closed: raises PermissionError if no valid session.
        """
        actor = current_auth.actor  # validates session against DB
        if actor is None:
            raise PermissionError("No authenticated actor — capture requires a valid session.")
        if actor.company_id is None:
            raise PermissionError("Actor has no company scope — capture requires company context.")
        # Update config from authenticated context
        self.config.member_id = actor.id
        self.config.company_id = actor.company_id

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self, granted_by: str) -> None:
        """Start capture. Requires consent and valid authenticated session."""
        with self._lock:
            if self.state == CaptureState.RUNNING:
                logger.warning("Capture already running")
                return

            if not self.config.consent_required or self.has_consent():
                pass
            else:
                raise PermissionError(
                    "Capture consent required — call grant_consent() before start()"
                )

            self._validate_auth()

            if self.config.company_id is None:
                raise PermissionError("No company_id — cannot scope capture events")

            # Import here to avoid hard dependency on activitywatch_derived
            # when running on non-Windows or in test environments.
            from bimspend.capture.activitywatch_derived.watcher_main import (
                HeartbeatLoop,
            )
            from bimspend.capture.activitywatch_derived.windows import get_current_window

            self._loop = HeartbeatLoop(
                get_window_fn=get_current_window,
                poll_time=self.config.poll_time,
                exclude_title=self.config.exclude_title,
                exclude_titles=self.config.exclude_titles,
                exclude_apps=self.config.exclude_apps,
                privacy_filter_rules=self.config.privacy_rules,
                on_window=self._on_window_observed,
            )

            self._session_started_at = datetime.now(timezone.utc).isoformat()
            self.state = CaptureState.RUNNING

            self._loop_thread = threading.Thread(target=self._run, daemon=True)
            self._loop_thread.start()
            logger.info(
                "Capture started for member %s in company %s",
                self.config.member_id,
                self.config.company_id,
            )

    def _run(self) -> None:
        """Run the heartbeat loop in a background thread."""
        try:
            self._loop.start()  # blocking
        except Exception as exc:
            logger.error("Capture loop error: %s", exc)
            with self._lock:
                self.state = CaptureState.ERROR
        finally:
            with self._lock:
                if self.state == CaptureState.RUNNING:
                    self.state = CaptureState.STOPPED

    def pause(self) -> None:
        """Pause capture without stopping the loop."""
        with self._lock:
            if self.state != CaptureState.RUNNING:
                return
            self.state = CaptureState.PAUSED
            if self._loop is not None:
                self._loop.pause()
            logger.info("Capture paused")

    def resume(self) -> None:
        """Resume capture after pause."""
        with self._lock:
            if self.state != CaptureState.PAUSED:
                return
            self.state = CaptureState.RUNNING
            if self._loop is not None:
                self._loop.resume()
            logger.info("Capture resumed")

    def stop(self) -> None:
        """Stop capture and release resources."""
        with self._lock:
            if self.state == CaptureState.STOPPED:
                return
            self.state = CaptureState.STOPPED
            if self._loop is not None:
                self._loop.stop()
            self._loop_thread = None
            self._loop = None
            self._session_started_at = None
            logger.info("Capture stopped")

    def get_state(self) -> CaptureState:
        with self._lock:
            return self.state

    def is_running(self) -> bool:
        return self.get_state() == CaptureState.RUNNING

    # ------------------------------------------------------------------
    # Event delivery callback (called by HeartbeatLoop)
    # ------------------------------------------------------------------

    def _on_window_observed(self, window: dict, chain_broken: bool) -> None:
        """Called by HeartbeatLoop for each accepted window observation.

        Persists the event to SQLite with company scope and idempotency key.
        Fail-closed: any persistence error is logged but does not crash the
        capture loop.
        """
        try:
            self._persist_event(window, chain_broken)
        except Exception as exc:
            logger.error("Failed to persist window event: %s", exc)

    def _persist_event(self, window: dict, chain_broken: bool) -> None:
        """Persist a window observation as an ActivityEvent."""
        # Compute external_id for idempotency: source + app + title hash + start time
        app = window.get("app") or "unknown"
        title = window.get("title") or ""
        title_hash = self._hash_title(title)
        start_time = window.get("timestamp") or datetime.now(timezone.utc).isoformat()

        external_id = f"aw:{app}:{title_hash}:{start_time}"

        event = ActivityEvent(
            id=secrets.token_urlsafe(16),
            source="activitywatch",
            external_id=external_id,
            user_id=self.config.member_id or "unknown",
            app_name=app,
            window_title=title_hash,  # always hashed — never store raw title
            started_at=start_time,
            ended_at=start_time,  # single-point observation; duration set on next poll
            duration_minutes=0.0,
            is_afk=False,  # set by AFK detector integration
            event_type="active_window",
            raw_payload=None,  # never store raw payload
            title_redacted=True,  # title is always hashed
        )

        # Set company_id on the event for scoping
        # ActivityEvent doesn't have company_id field; we store it via the
        # database method extension. For now, use the existing ingest_event
        # which doesn't take company_id. We'll add company scoping via the
        # v6 migration and a new method.

        self.db.ingest_event(event, company_id=self.config.company_id)
        self._last_window = window
        self._last_window_time = time.time()

    def _hash_title(self, title: str) -> str:
        import hashlib

        return f"[HASH:{hashlib.sha256(title.encode('utf-8')).hexdigest()[:8]}]"

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        """Return current capture status for UI/diagnostic display."""
        with self._lock:
            return {
                "state": self.state.value,
                "consent_granted": self.consent.granted,
                "consent_revoked_at": self.consent.revoked_at,
                "member_id": self.config.member_id,
                "company_id": self.config.company_id,
                "session_started_at": self._session_started_at,
                "poll_time": self.config.poll_time,
                "last_window": self._last_window,
                "last_window_time": self._last_window_time,
            }
