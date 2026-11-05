#!/usr/bin/env python3
"""
Unit tests for ActivityWatch Adapter.
"""

import json
import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone

sys.path.insert(0, str(os.path.dirname(__file__)))

from main import (
    AWAdapter,
    AWClient,
    EventTransformer,
    QueueWriter,
    PrivacyFilter,
    Config,
)


def test_privacy_filter():
    """Test privacy filter behavior."""
    config = {
        "enabled": True,
        "allowlist_patterns": ["Project_A", "Project_B"],
        "denylist_patterns": ["password", "secret", "token"],
    }
    pf = PrivacyFilter(config)

    # Test denylist
    assert pf.filter_window_title("Enter password") == "[REDACTED]"
    assert pf.filter_window_title("API token") == "[REDACTED]"
    assert pf.filter_window_title("secret key") == "[REDACTED]"

    # Test allowlist
    assert pf.filter_window_title("Project_A.rvt - Revit") == "Project_A.rvt - Revit"
    assert pf.filter_window_title("Project_B - Design") == "Project_B - Design"

    # Test default hashing
    result = pf.filter_window_title("Some random window title")
    assert result.startswith("[HASH:")
    assert result.endswith("]")
    assert len(result) == len("[HASH:abcdef12]")

    print("PASS PrivacyFilter tests passed")


def test_event_transformer_window():
    """Test window event transformation."""
    import yaml

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({
            "aw_server_url": "http://localhost:5600",
            "poll_interval_seconds": 5,
            "instance_id": str(uuid.uuid4()),
            "privacy": {"enabled": False},
        }, f)
        config_path = f.name

    try:
        config = Config(config_path)
        pf = PrivacyFilter(config.data.get("privacy", {}))
        transformer = EventTransformer(config, pf, config.data["instance_id"])

        # Raw AW window event
        raw_event = {
            "id": 123,
            "timestamp": datetime.now(timezone.utc).timestamp(),
            "duration": 1.5,
            "data": {
                "app": "Revit.exe",
                "title": "Project_A.rvt - Autodesk Revit 2025",
                "pid": 8842,
                "exe_path": "C:\\Program Files\\Autodesk\\Revit 2025\\Revit.exe",
            },
        }

        event = transformer.transform_window_event(raw_event)

        assert event is not None
        assert event["event_type"] == "window.focus.changed"
        assert event["schema_version"] == "1.0.0"
        assert event["source"]["component"] == "aw-adapter"
        assert event["source"]["instance_id"] == config.data["instance_id"]
        assert event["payload"]["current"]["app_name"] == "Revit.exe"
        assert event["payload"]["current"]["window_title"] == "Project_A.rvt - Autodesk Revit 2025"
        assert event["payload"]["current"]["process_id"] == 8842
        assert event["payload"]["transition_type"] == "foreground_gained"
        assert event["payload"]["idle_state"] == "active"

        print("PASS EventTransformer window event tests passed")

    finally:
        os.unlink(config_path)


def test_event_transformer_afk():
    """Test AFK event transformation."""
    import yaml

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({
            "aw_server_url": "http://localhost:5600",
            "poll_interval_seconds": 5,
            "instance_id": str(uuid.uuid4()),
            "privacy": {"enabled": False},
        }, f)
        config_path = f.name

    try:
        config = Config(config_path)
        pf = PrivacyFilter(config.data.get("privacy", {}))
        transformer = EventTransformer(config, pf, config.data["instance_id"])

        # Raw AW AFK event
        raw_event = {
            "id": 124,
            "timestamp": datetime.now(timezone.utc).timestamp(),
            "duration": 0,
            "data": {
                "status": "afk",
                "idle_duration": 300,
            },
        }

        event = transformer.transform_afk_event(raw_event)

        assert event is not None
        assert event["event_type"] == "afk.state.changed"
        assert event["schema_version"] == "1.0.0"
        assert event["source"]["component"] == "aw-adapter"
        assert event["payload"]["state"] == "afk"
        assert event["payload"]["idle_duration_seconds"] == 300
        assert event["payload"]["trigger"] == "timeout"
        assert event["payload"]["previous_state"] == "not_afk"

        print("PASS EventTransformer AFK event tests passed")

    finally:
        os.unlink(config_path)


def test_deduplication():
    """Test event deduplication."""
    import yaml

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({
            "aw_server_url": "http://localhost:5600",
            "poll_interval_seconds": 5,
            "instance_id": str(uuid.uuid4()),
            "privacy": {"enabled": False},
        }, f)
        config_path = f.name

    try:
        config = Config(config_path)
        pf = PrivacyFilter(config.data.get("privacy", {}))
        transformer = EventTransformer(config, pf, config.data["instance_id"])

        base_ts = datetime.now(timezone.utc).timestamp()

        # First window event
        raw1 = {
            "id": 1,
            "timestamp": base_ts,
            "duration": 1.0,
            "data": {"app": "Revit.exe", "title": "Project_A.rvt", "pid": 8842, "exe_path": ""},
        }
        event1 = transformer.transform_window_event(raw1)
        assert event1 is not None

        # Duplicate within 5 seconds
        raw2 = {
            "id": 2,
            "timestamp": base_ts + 2,  # 2 seconds later
            "duration": 1.0,
            "data": {"app": "Revit.exe", "title": "Project_A.rvt", "pid": 8842, "exe_path": ""},
        }
        event2 = transformer.transform_window_event(raw2)
        assert event2 is None  # Should be deduplicated

        # After 5 seconds - should pass
        raw3 = {
            "id": 3,
            "timestamp": base_ts + 6,  # 6 seconds later
            "duration": 1.0,
            "data": {"app": "Revit.exe", "title": "Project_A.rvt", "pid": 8842, "exe_path": ""},
        }
        event3 = transformer.transform_window_event(raw3)
        assert event3 is not None  # Should NOT be deduplicated

        print("PASS Deduplication tests passed")

    finally:
        os.unlink(config_path)


def test_queue_writer():
    """Test queue writer."""
    import yaml

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({
            "aw_server_url": "http://localhost:5600",
            "poll_interval_seconds": 5,
            "instance_id": str(uuid.uuid4()),
            "privacy": {"enabled": False},
            "queue": {"path": ":memory:"},
        }, f)
        config_path = f.name

    try:
        config = Config(config_path)

        # Use temp file for queue
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as qf:
            queue_path = qf.name

        try:
            qw = QueueWriter(queue_path)

            # Create a test event
            event = {
                "event_id": str(uuid.uuid4()),
                "event_type": "window.focus.changed",
                "schema_version": "1.0.0",
                "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "source": {
                    "component": "aw-adapter",
                    "version": "1.0.0",
                    "instance_id": config.data["instance_id"],
                    "process_id": os.getpid(),
                },
                "correlation": {
                    "session_id": str(uuid.uuid4()),
                    "run_id": str(uuid.uuid4()),
                },
                "payload": {
                    "previous": {"app_name": None, "window_title": None, "process_id": None, "exe_path": None},
                    "current": {"app_name": "Revit.exe", "window_title": "Project_A.rvt", "process_id": 8842, "exe_path": ""},
                    "transition_type": "foreground_gained",
                    "idle_state": "active",
                    "monitor_info": {"monitor_count": 1, "primary_monitor": 0},
                },
            }

            entry_id = qw.enqueue(event)
            assert entry_id is not None

            # Verify entry in database
            import sqlite3
            conn = sqlite3.connect(queue_path)
            cursor = conn.execute("SELECT * FROM queue_entries WHERE id = ?", (entry_id,))
            row = cursor.fetchone()
            conn.close()
            assert row is not None
            # Columns: id, event_type, payload, external_run_id, external_session_id, status, attempts, ...
            assert row[1] == "window.focus.changed"  # event_type
            assert row[3] is not None  # external_run_id
            assert row[4] is not None  # external_session_id
            assert row[5] == "pending"  # status

            print("PASS QueueWriter tests passed")

        finally:
            # Ensure connections are closed before deleting
            import gc
            gc.collect()
            if os.path.exists(queue_path):
                try:
                    os.unlink(queue_path)
                except PermissionError:
                    pass  # Windows file locking, ignore in tests

    finally:
        os.unlink(config_path)


def test_external_id_generation():
    """Test deterministic external ID generation."""
    import yaml

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({
            "aw_server_url": "http://localhost:5600",
            "poll_interval_seconds": 5,
            "instance_id": "test-instance-id",
            "privacy": {"enabled": False},
            "queue": {"path": ":memory:"},
        }, f)
        config_path = f.name

    try:
        config = Config(config_path)

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as qf:
            queue_path = qf.name

        try:
            qw = QueueWriter(queue_path)

            timestamp = "2026-11-05T12:00:00.000Z"

            event1 = {
                "event_id": str(uuid.uuid4()),
                "event_type": "window.focus.changed",
                "schema_version": "1.0.0",
                "timestamp_utc": timestamp,
                "source": {
                    "component": "aw-adapter",
                    "version": "1.0.0",
                    "instance_id": "test-instance-id",
                    "process_id": 8842,
                },
                "correlation": {
                    "session_id": "test-session-id",
                    "run_id": "test-run-id",
                },
                "payload": {},
            }

            event2 = {
                "event_id": str(uuid.uuid4()),
                "event_type": "window.focus.changed",
                "schema_version": "1.0.0",
                "timestamp_utc": timestamp,
                "source": {
                    "component": "aw-adapter",
                    "version": "1.0.0",
                    "instance_id": "test-instance-id",
                    "process_id": 8842,
                },
                "correlation": {
                    "session_id": "test-session-id",
                    "run_id": "test-run-id",
                },
                "payload": {},
            }

            entry_id1 = qw.enqueue(event1)
            entry_id2 = qw.enqueue(event2)

            import sqlite3
            conn = sqlite3.connect(queue_path)
            cursor = conn.execute("SELECT external_run_id, external_session_id FROM queue_entries WHERE id IN (?, ?)", (entry_id1, entry_id2))
            rows = cursor.fetchall()
            conn.close()

                # Same inputs should produce same external IDs
            assert rows[0][0] == rows[1][0]  # external_run_id
            assert rows[0][1] == rows[1][1]  # external_session_id
            assert len(rows[0][0]) == 32  # SHA256 truncated to 32 chars
            assert len(rows[0][1]) == 32

            print("PASS External ID generation tests passed")

        finally:
            # Ensure connections are closed before deleting
            import gc
            gc.collect()
            if os.path.exists(queue_path):
                try:
                    os.unlink(queue_path)
                except PermissionError:
                    pass  # Windows file locking, ignore in tests

    finally:
        os.unlink(config_path)


def run_all_tests():
    """Run all unit tests."""
    print("Running AW Adapter unit tests...\n")

    test_privacy_filter()
    test_event_transformer_window()
    test_event_transformer_afk()
    test_deduplication()
    test_queue_writer()
    test_external_id_generation()

    print("\nALL TESTS All AW Adapter unit tests passed!")


if __name__ == "__main__":
    run_all_tests()