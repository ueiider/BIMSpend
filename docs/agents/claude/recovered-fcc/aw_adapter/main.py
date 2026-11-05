#!/usr/bin/env python3
"""
ActivityWatch Adapter for BIMSpend

Consumes local AW REST API, emits normalized events to shared offline queue.
"""

import asyncio
import json
import logging
import os
import signal
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
import yaml

# Add schemas to path
sys.path.insert(0, str(Path(__file__).parent.parent / "tests"))
from test_schemas import SchemaTester

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("aw_adapter")


class Config:
    """Configuration loader."""

    def __init__(self, config_path: str):
        with open(config_path, "r") as f:
            self.data = yaml.safe_load(f)

        # Generate instance_id if not present
        if not self.data.get("instance_id"):
            self.data["instance_id"] = str(uuid.uuid4())
            self.save(config_path)

    def save(self, config_path: str):
        with open(config_path, "w") as f:
            yaml.dump(self.data, f)

    def __getattr__(self, name: str) -> Any:
        return self.data.get(name)


class PrivacyFilter:
    """Filters window titles for privacy before events leave adapter."""

    def __init__(self, config: Dict):
        self.enabled = config.get("enabled", True)
        self.allowlist = [p for p in config.get("allowlist_patterns", []) if p]
        self.denylist = [p for p in config.get("denylist_patterns", []) if p]

    def filter_window_title(self, title: str) -> str:
        """Filter window title - hash by default, allow known patterns."""
        if not self.enabled:
            return title

        # Check denylist first (explicit redaction)
        for pattern in self.denylist:
            if pattern.lower() in title.lower():
                return "[REDACTED]"

        # Check allowlist (known safe patterns)
        for pattern in self.allowlist:
            if pattern in title:
                return title

        # Default: hash the title
        import hashlib
        hash_suffix = hashlib.sha256(title.encode()).hexdigest()[:8]
        return f"[HASH:{hash_suffix}]"

    def filter_event(self, event: Dict) -> Dict:
        """Apply privacy filter to window focus event."""
        if event.get("event_type") != "window.focus.changed":
            return event

        filtered = event.copy()
        payload = filtered.get("payload", {}).copy()

        # Filter previous window title
        if "previous" in payload and payload["previous"].get("window_title"):
            payload["previous"]["window_title"] = self.filter_window_title(
                payload["previous"]["window_title"]
            )

        # Filter current window title
        if "current" in payload and payload["current"].get("window_title"):
            payload["current"]["window_title"] = self.filter_window_title(
                payload["current"]["window_title"]
            )

        filtered["payload"] = payload
        return filtered


class AWClient:
    """ActivityWatch REST API client."""

    def __init__(self, base_url: str, session: aiohttp.ClientSession):
        self.base_url = base_url.rstrip("/")
        self.session = session

    async def get_buckets(self) -> List[Dict]:
        """Get all buckets from AW server."""
        async with self.session.get(f"{self.base_url}/api/0/buckets/") as resp:
            resp.raise_for_status()
            return await resp.json()

    async def get_events(self, bucket_id: str, limit: int = 100) -> List[Dict]:
        """Get events from a bucket."""
        async with self.session.get(
            f"{self.base_url}/api/0/events/", params={"bucket": bucket_id, "limit": limit}
        ) as resp:
            resp.raise_for_status()
            return await resp.json()


class EventTransformer:
    """Transforms raw AW events to BIMSpend contract events."""

    def __init__(self, config: Config, privacy_filter: PrivacyFilter, instance_id: str):
        self.config = config
        self.privacy_filter = privacy_filter
        self.instance_id = instance_id
        self.process_id = os.getpid()

        # Track last seen events for deduplication
        self._last_window_event: Dict[str, float] = {}  # key -> timestamp
        self._last_afk_event: Dict[str, float] = {}

    def _now_utc(self) -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def _generate_event_id(self) -> str:
        return str(uuid.uuid4())

    def _generate_session_id(self) -> str:
        return str(uuid.uuid4())

    def _generate_run_id(self) -> str:
        return str(uuid.uuid4())

    def _deduplicate_window(self, raw_event: Dict) -> bool:
        """Check if window event should be deduplicated (5 second window)."""
        data = raw_event.get("data", {})
        key = f"{data.get('app', '')}:{data.get('title', '')}"
        now = raw_event.get("timestamp", 0)

        if key in self._last_window_event:
            if now - self._last_window_event[key] < 5:
                return True

        self._last_window_event[key] = now
        return False

    def _deduplicate_afk(self, raw_event: Dict) -> bool:
        """Check if AFK event should be deduplicated (10 second window)."""
        data = raw_event.get("data", {})
        key = data.get("status", "")
        now = raw_event.get("timestamp", 0)

        if key in self._last_afk_event:
            if now - self._last_afk_event[key] < 10:
                return True

        self._last_afk_event[key] = now
        return False

    def transform_window_event(self, raw_event: Dict) -> Optional[Dict]:
        """Transform AW window event to window.focus.changed."""
        if self._deduplicate_window(raw_event):
            return None

        data = raw_event.get("data", {})
        timestamp = datetime.fromtimestamp(raw_event["timestamp"], tz=timezone.utc)

        # Build previous state (unknown from AW, use placeholder)
        previous = {
            "app_name": None,
            "window_title": None,
            "process_id": None,
            "exe_path": None,
        }

        # Current state from AW
        current = {
            "app_name": data.get("app", "unknown"),
            "window_title": data.get("title", ""),
            "process_id": data.get("pid", 0),
            "exe_path": data.get("exe_path", ""),
        }

        # Determine transition type
        transition_type = "foreground_gained"
        idle_state = "active"

        event = {
            "event_id": self._generate_event_id(),
            "event_type": "window.focus.changed",
            "schema_version": "1.0.0",
            "timestamp_utc": timestamp.isoformat().replace("+00:00", "Z"),
            "source": {
                "component": "aw-adapter",
                "version": "1.0.0",
                "instance_id": self.instance_id,
                "process_id": self.process_id,
            },
            "correlation": {
                "session_id": self._generate_session_id(),
                "run_id": self._generate_run_id(),
            },
            "payload": {
                "previous": previous,
                "current": current,
                "transition_type": transition_type,
                "idle_state": idle_state,
                "monitor_info": {
                    "monitor_count": 1,
                    "primary_monitor": 0,
                },
            },
        }

        # Apply privacy filter
        return self.privacy_filter.filter_event(event)

    def transform_afk_event(self, raw_event: Dict) -> Optional[Dict]:
        """Transform AW AFK event to afk.state.changed."""
        if self._deduplicate_afk(raw_event):
            return None

        data = raw_event.get("data", {})
        timestamp = datetime.fromtimestamp(raw_event["timestamp"], tz=timezone.utc)

        state = data.get("status", "not_afk")
        # AW uses "afk" and "not-afk", normalize
        if state == "not-afk":
            state = "not_afk"

        event = {
            "event_id": self._generate_event_id(),
            "event_type": "afk.state.changed",
            "schema_version": "1.0.0",
            "timestamp_utc": timestamp.isoformat().replace("+00:00", "Z"),
            "source": {
                "component": "aw-adapter",
                "version": "1.0.0",
                "instance_id": self.instance_id,
                "process_id": self.process_id,
            },
            "correlation": {
                "session_id": self._generate_session_id(),
                "run_id": self._generate_run_id(),
            },
            "payload": {
                "state": state,
                "idle_duration_seconds": data.get("idle_duration", 0),
                "trigger": "timeout" if state == "afk" else "mouse",
                "previous_state": "not_afk" if state == "afk" else "afk",
            },
        }

        return event


class QueueWriter:
    """Writes events to shared SQLite queue."""

    def __init__(self, queue_path: str):
        self.queue_path = Path(queue_path)
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        import sqlite3

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
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_queue_external_session
                ON queue_entries(external_session_id)
            """)
            conn.commit()

    def _generate_external_ids(self, event: Dict) -> tuple:
        """Generate deterministic external_run_id and external_session_id."""
        import hashlib

        adapter_instance_id = event["source"]["instance_id"]
        run_start = event["timestamp_utc"]
        revit_process_id = event["source"]["process_id"]
        revit_session_id = event["correlation"]["session_id"]

        external_run_id = hashlib.sha256(
            f"run{adapter_instance_id}{run_start}".encode()
        ).hexdigest()[:32]

        external_session_id = hashlib.sha256(
            f"session{revit_process_id}{revit_session_id}".encode()
        ).hexdigest()[:32]

        return external_run_id, external_session_id

    def enqueue(self, event: Dict) -> str:
        """Add validated event to queue. Returns queue entry ID."""
        import sqlite3
        import uuid as uuid_lib

        # Generate deterministic external IDs
        external_run_id, external_session_id = self._generate_external_ids(event)

        entry_id = str(uuid_lib.uuid4())
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        # Extract metadata for indexing
        metadata = {
            "correlation_confidence": 0.5,  # Default for raw AW events
            "project_id": "unknown",  # Will be resolved by Windows Adapter
            "interval_start_utc": event["timestamp_utc"],
            "interval_end_utc": event["timestamp_utc"],
        }

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
                now,  # Immediate first attempt
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


class AWAdapter:
    """Main ActivityWatch Adapter."""

    def __init__(self, config_path: str):
        self.config = Config(config_path)
        self.privacy_filter = PrivacyFilter(self.config.data.get("privacy", {}))
        self.instance_id = self.config.data["instance_id"]
        self.poll_interval = self.config.data.get("poll_interval_seconds", 5)
        self.running = False
        self._last_event_timestamps: Dict[str, float] = {}  # bucket_id -> last timestamp

    async def run(self):
        """Main adapter loop."""
        self.running = True
        logger.info(f"Starting AW Adapter (instance_id={self.instance_id})")

        # Initialize queue writer
        queue_path = self.config.data.get("queue", {}).get("path", "data/bimspend_queue.db")
        queue_writer = QueueWriter(queue_path)

        # Initialize schema validator
        tester = SchemaTester()
        tester.load_schemas()

        async with aiohttp.ClientSession() as session:
            aw_client = AWClient(self.config.data["aw_server_url"], session)
            transformer = EventTransformer(self.config, self.privacy_filter, self.instance_id)

            # Find relevant buckets
            buckets = await aw_client.get_buckets()
            window_buckets = [b for b in buckets if "window" in b.get("id", "").lower()]
            afk_buckets = [b for b in buckets if "afk" in b.get("id", "").lower()]

            logger.info(f"Found {len(window_buckets)} window buckets, {len(afk_buckets)} AFK buckets")

            # Initialize last timestamps
            for bucket in window_buckets + afk_buckets:
                self._last_event_timestamps[bucket["id"]] = 0

            while self.running:
                try:
                    # Poll window buckets
                    for bucket in window_buckets:
                        await self._poll_bucket(
                            aw_client, bucket["id"], transformer, queue_writer, tester, "window"
                        )

                    # Poll AFK buckets
                    for bucket in afk_buckets:
                        await self._poll_bucket(
                            aw_client, bucket["id"], transformer, queue_writer, tester, "afk"
                        )

                except Exception as e:
                    logger.error(f"Poll error: {e}")

                await asyncio.sleep(self.poll_interval)

    async def _poll_bucket(
        self,
        client: AWClient,
        bucket_id: str,
        transformer: EventTransformer,
        queue_writer: QueueWriter,
        tester: SchemaTester,
        bucket_type: str,
    ):
        """Poll a single bucket for new events."""
        last_ts = self._last_event_timestamps.get(bucket_id, 0)
        events = await client.get_events(bucket_id, limit=100)

        new_events = [e for e in events if e.get("timestamp", 0) > last_ts]
        if not new_events:
            return

        self._last_event_timestamps[bucket_id] = max(e.get("timestamp", 0) for e in new_events)

        for raw_event in new_events:
            try:
                if bucket_type == "window":
                    event = transformer.transform_window_event(raw_event)
                else:
                    event = transformer.transform_afk_event(raw_event)

                if event is None:
                    continue

                # Validate against schema
                valid, msg = tester.validate_event(event, tester.get_schema_for_event(event))
                if not valid:
                    logger.warning(f"Event validation failed: {msg}")
                    continue

                # Enqueue
                queue_writer.enqueue(event)
                logger.info(f"Enqueued {event['event_type']} (event_id={event['event_id']})")

            except Exception as e:
                logger.error(f"Error processing event: {e}")

    def stop(self):
        """Stop the adapter."""
        self.running = False
        logger.info("Stopping AW Adapter")


async def main():
    """Entry point."""
    config_path = os.environ.get(
        "AW_ADAPTER_CONFIG", str(Path(__file__).parent / "config.yaml")
    )

    adapter = AWAdapter(config_path)

    # Handle shutdown signals
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, adapter.stop)

    try:
        await adapter.run()
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("AW Adapter stopped")


if __name__ == "__main__":
    asyncio.run(main())