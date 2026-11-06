"""Tests for ActivityWatch-derived capture module (R1-01/R1-02).

Tests cover:
- Windows window detection primitives (mocked)
- Privacy filter behavior
- Heartbeat loop and interval management
- Capture controller lifecycle and consent
- AFK detector state transitions
- Session lock detector
- SQLite persistence with company scoping
- Idempotent event ingestion
- No raw titles in storage
- No automatic billing
"""

import os
import sys
import time
import hashlib

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bimspend.db import Database
from bimspend.models import ActivityEvent, TimeEntryState
from bimspend.identity import current_auth, Actor, Role
from bimspend.capture import (
    CaptureController,
    CaptureState,
    CaptureConfig,
    AFKDetector,
    AFKState,
    SessionLockDetector,
    SessionLockState,
    HeartbeatManager,
    HeartbeatEvent,
)
from bimspend.capture.activitywatch_derived import (
    compile_privacy_rules,
    apply_privacy_filters,
    hash_title,
)
from bimspend.capture.activitywatch_derived.watcher_main import (
    compute_pulsetime,
    transform_window,
)


# ------------------------------------------------------------------
# Privacy filter tests
# ------------------------------------------------------------------

def test_privacy_filter_drop_rule():
    rules = compile_privacy_rules([
        {"pattern": r"(?i)incognito", "action": "drop"},
    ])
    window = {"app": "chrome.exe", "title": "Incognito - Secret Document"}
    result = apply_privacy_filters(window, rules)
    assert result is None


def test_privacy_filter_redact_rule():
    rules = compile_privacy_rules([
        {"pattern": r"(?i)bank", "action": "redact", "replacement": "[REDACTED]"},
    ])
    window = {"app": "chrome.exe", "title": "Bank of Example - Account"}
    result = apply_privacy_filters(window, rules)
    assert result is not None
    assert result["title"] == "[REDACTED]"
    assert result["app"] == "chrome.exe"


def test_privacy_filter_no_rules_passthrough():
    window = {"app": "notepad.exe", "title": "Document.txt"}
    result = apply_privacy_filters(window, [])
    assert result == window


def test_hash_title_deterministic():
    h1 = hash_title("Secret Document")
    h2 = hash_title("Secret Document")
    assert h1 == h2
    assert h1.startswith("[HASH:")
    assert "Secret" not in h1


def test_hash_title_different_inputs():
    assert hash_title("Doc A") != hash_title("Doc B")


# ------------------------------------------------------------------
# Window transform tests
# ------------------------------------------------------------------

def test_transform_window_excludes_app():
    rules = []
    window = {"app": "1password.exe", "title": "Vault"}
    result = transform_window(
        window, exclude_apps=[__import__("re").compile(r"(?i)1password")],
        privacy_filter_rules=rules,
    )
    assert result is None


def test_transform_window_excludes_title():
    window = {"app": "chrome.exe", "title": "Private Browsing"}
    result = transform_window(
        window, exclude_titles=[__import__("re").compile(r"(?i)private")],
        privacy_filter_rules=[],
    )
    assert result is not None
    assert result["title"] == "excluded"


def test_compute_pulsetime():
    assert compute_pulsetime(1.0) == max(1.5, 2.0)  # 2.0
    assert compute_pulsetime(5.0) == max(7.5, 6.0)  # 7.5


# ------------------------------------------------------------------
# Heartbeat manager tests
# ------------------------------------------------------------------

def test_heartbeat_same_app_continues_interval():
    hm = HeartbeatManager(user_id="u1", company_id="c1")
    # First observation starts interval
    event = hm.observe("notepad.exe", "[HASH:abcd1234]", is_afk=False)
    assert event is None
    # Same app continues
    event = hm.observe("notepad.exe", "[HASH:abcd1234]", is_afk=False)
    assert event is None


def test_heartbeat_app_switch_closes_interval():
    hm = HeartbeatManager(user_id="u1", company_id="c1")
    hm.observe("notepad.exe", "[HASH:abcd1234]", timestamp="2026-01-01T01:00:00Z")
    event = hm.observe("chrome.exe", "[HASH:efgh5678]", timestamp="2026-01-01T01:05:00Z")
    assert event is not None
    assert event.app_name == "notepad.exe"
    assert event.duration_minutes == 5.0


def test_heartbeat_afk_transition_closes_interval():
    hm = HeartbeatManager(user_id="u1", company_id="c1")
    hm.observe("notepad.exe", "[HASH:abcd1234]", is_afk=False, timestamp="2026-01-01T01:00:00Z")
    event = hm.observe("notepad.exe", "[HASH:abcd1234]", is_afk=True, timestamp="2026-01-01T01:05:00Z")
    assert event is not None
    assert event.is_afk is False  # closed interval was active


def test_heartbeat_flush_closes_interval():
    hm = HeartbeatManager(user_id="u1", company_id="c1")
    hm.observe("notepad.exe", "[HASH:abcd1234]", timestamp="2026-01-01T01:00:00Z")
    event = hm.flush(ended_at="2026-01-01T01:10:00Z")
    assert event is not None
    assert event.duration_minutes == 10.0


def test_heartbeat_event_has_company_id():
    hm = HeartbeatManager(user_id="u1", company_id="c1")
    hm.observe("notepad.exe", "[HASH:abcd1234]", timestamp="2026-01-01T01:00:00Z")
    event = hm.observe("chrome.exe", "[HASH:efgh5678]", timestamp="2026-01-01T01:05:00Z")
    assert event.company_id == "c1"
    assert event.user_id == "u1"
    assert event.title_redacted is True


# ------------------------------------------------------------------
# AFK detector tests
# ------------------------------------------------------------------

def test_afk_detector_initial_state():
    detector = AFKDetector(afk_threshold_minutes=5.0)
    assert detector.is_active()
    assert not detector.is_afk()


def test_afk_detector_threshold():
    detector = AFKDetector(afk_threshold_minutes=1.0)
    detector.set_threshold_minutes(5.0)
    assert detector.afk_threshold_seconds == 300.0


# ------------------------------------------------------------------
# Session lock detector tests
# ------------------------------------------------------------------

def test_session_lock_detector_initial_state():
    detector = SessionLockDetector()
    assert detector.is_unknown()


# ------------------------------------------------------------------
# Capture controller tests (mocked)
# ------------------------------------------------------------------

class FakeLoop:
    """Fake HeartbeatLoop for testing controller lifecycle.

    Blocks in start() to simulate a real blocking loop, allowing the
    controller's background thread to stay alive during tests.
    """
    def __init__(self, *args, **kwargs):
        self.started = False
        self.stopped = False
        self.paused = False
        self.resumed = False
        self.on_window = kwargs.get("on_window")
        self._stop_event = __import__("threading").Event()

    def start(self):
        self.started = True
        # Block until stop() is called, simulating a real loop
        self._stop_event.wait()

    def stop(self):
        self.stopped = True
        self._stop_event.set()

    def pause(self):
        self.paused = True

    def resume(self):
        self.resumed = True


def _make_controller_with_fake_loop(monkeypatch, db_path):
    """Create a controller with a fake HeartbeatLoop."""
    from bimspend.identity import current_auth
    current_auth.clear()  # Ensure clean auth state (clears _db too)

    import bimspend.capture.controller as ctrl_mod

    original_init = ctrl_mod.CaptureController.__init__

    def patched_init(self, db, config=None):
        original_init(self, db, config)
        # Replace HeartbeatLoop with fake
        import bimspend.capture.activitywatch_derived.watcher_main as wm
        wm.HeartbeatLoop = FakeLoop

    monkeypatch.setattr(ctrl_mod.CaptureController, "__init__", patched_init)

    db = Database(db_path)
    config = CaptureConfig(
        poll_time=5.0,
        consent_required=True,
        company_id="c1",
        member_id="m1",
    )
    controller = CaptureController(db, config)
    return controller, db


def test_capture_controller_initial_state(tmp_path):
    db = Database(str(tmp_path / "capture.db"))
    config = CaptureConfig(poll_time=5.0, consent_required=True)
    controller = CaptureController(db, config)
    assert controller.get_state() == CaptureState.STOPPED
    assert not controller.is_running()
    assert not controller.has_consent()
    db.close()


def test_capture_controller_grant_and_revoke_consent(tmp_path):
    db = Database(str(tmp_path / "capture.db"))
    config = CaptureConfig(consent_required=True)
    controller = CaptureController(db, config)

    assert not controller.has_consent()
    controller.grant_consent("user1")
    assert controller.has_consent()
    controller.revoke_consent("user2")
    assert not controller.has_consent()
    db.close()


def test_capture_controller_start_without_consent_raises(tmp_path, monkeypatch):
    db = Database(str(tmp_path / "capture.db"))
    controller, _ = _make_controller_with_fake_loop(monkeypatch, str(tmp_path / "capture.db"))
    # Don't grant consent
    with pytest.raises(PermissionError, match="consent required"):
        controller.start(granted_by="user1")
    db.close()


def test_capture_controller_start_stop(tmp_path, monkeypatch):
    db = Database(str(tmp_path / "capture.db"))
    controller, _ = _make_controller_with_fake_loop(monkeypatch, str(tmp_path / "capture.db"))
    controller.grant_consent("user1")

    # Need authenticated actor - set via current_auth
    current_auth.set_actor(Actor(id="m1", role=Role.DESIGNER, company_id="c1"))

    controller.start(granted_by="user1")
    assert controller.get_state() == CaptureState.RUNNING
    assert controller.is_running()

    controller.stop()
    assert controller.get_state() == CaptureState.STOPPED
    assert not controller.is_running()
    db.close()


def test_capture_controller_pause_resume(tmp_path, monkeypatch):
    db = Database(str(tmp_path / "capture.db"))
    controller, _ = _make_controller_with_fake_loop(monkeypatch, str(tmp_path / "capture.db"))
    controller.grant_consent("user1")
    current_auth.set_actor(Actor(id="m1", role=Role.DESIGNER, company_id="c1"))

    controller.start(granted_by="user1")
    assert controller.get_state() == CaptureState.RUNNING

    controller.pause()
    assert controller.get_state() == CaptureState.PAUSED

    controller.resume()
    assert controller.get_state() == CaptureState.RUNNING

    controller.stop()
    db.close()


def test_capture_controller_status(tmp_path, monkeypatch):
    db = Database(str(tmp_path / "capture.db"))
    controller, _ = _make_controller_with_fake_loop(monkeypatch, str(tmp_path / "capture.db"))
    controller.grant_consent("user1")
    current_auth.set_actor(Actor(id="m1", role=Role.DESIGNER, company_id="c1"))

    status = controller.get_status()
    assert status["state"] == "stopped"
    assert status["consent_granted"] is True
    assert status["company_id"] == "c1"
    assert status["member_id"] == "m1"
    db.close()


# ------------------------------------------------------------------
# SQLite integration tests
# ------------------------------------------------------------------

def test_activity_event_persists_with_company_id(tmp_path):
    db = Database(str(tmp_path / "capture_events.db"))
    db.upsert_company("c1", "Test Company", is_active=True)

    event = ActivityEvent(
        id="ev1",
        source="activitywatch",
        external_id="aw:notepad.exe:[HASH:abcd]:t1",
        user_id="m1",
        company_id="c1",
        app_name="notepad.exe",
        window_title="[HASH:abcd]",
        started_at="2026-01-01T01:00:00Z",
        ended_at="2026-01-01T01:05:00Z",
        duration_minutes=5.0,
        is_afk=False,
        event_type="active_window",
        title_redacted=True,
    )
    result = db.ingest_event(event, company_id="c1")
    assert result is True

    # Verify retrieval
    events = db.list_events()
    assert len(events) == 1
    assert events[0].company_id == "c1"
    assert events[0].app_name == "notepad.exe"
    # Raw title should NOT be stored
    assert events[0].window_title == "[HASH:abcd]"
    assert "notepad" not in events[0].window_title.lower() or "[HASH:" in events[0].window_title

    # Idempotent re-ingest
    result2 = db.ingest_event(event, company_id="c1")
    assert result2 is False
    events = db.list_events()
    assert len(events) == 1

    db.close()


def test_activity_event_without_company_still_works(tmp_path):
    db = Database(str(tmp_path / "capture_events.db"))
    event = ActivityEvent(
        id="ev1",
        source="activitywatch",
        external_id="aw:notepad.exe:[HASH:abcd]:t1",
        user_id="m1",
        app_name="notepad.exe",
        window_title="[HASH:abcd]",
        started_at="2026-01-01T01:00:00Z",
        ended_at="2026-01-01T01:05:00Z",
        duration_minutes=5.0,
        title_redacted=True,
    )
    result = db.ingest_event(event)
    assert result is True
    db.close()


# ------------------------------------------------------------------
# No automatic billing - activity events never create timesheets
# ------------------------------------------------------------------

def test_activity_events_do_not_auto_bill(tmp_path):
    db = Database(str(tmp_path / "capture_events.db"))
    event = ActivityEvent(
        id="ev1",
        source="activitywatch",
        external_id="aw:notepad.exe:[HASH:abcd]:t1",
        user_id="m1",
        company_id="c1",
        app_name="notepad.exe",
        window_title="[HASH:abcd]",
        started_at="2026-01-01T01:00:00Z",
        ended_at="2026-01-01T01:05:00Z",
        duration_minutes=5.0,
        title_redacted=True,
    )
    db.ingest_event(event, company_id="c1")
    # No time entries should exist
    entries = db.list_time_entries()
    assert len(entries) == 0
    db.close()
