#!/usr/bin/env python3
"""
Windows Adapter - Main Entry Point

Correlates AW and Revit events, builds attributed intervals, submits to Miru.
"""

import asyncio
import json
import logging
import os
import signal
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# Add correlation engine to path
sys.path.insert(0, str(Path(__file__).parent))

from correlation_engine import CorrelationEngine, QueueWriter
from miru_client import MiruClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("windows_adapter")


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


class RevitEventConsumer:
    """Consumes Revit events from dropzone or named pipe."""

    def __init__(self, config: Dict, correlation_engine: CorrelationEngine):
        self.config = config
        self.correlation_engine = correlation_engine
        self.running = False
        self._thread: Optional[threading.Thread] = None

        transport_config = config.get("revit_transport", {})
        self.transport_type = transport_config.get("type", "dropzone")
        self.dropzone_path = Path(transport_config.get("dropzone_path", "C:/ProgramData/BIMSpend/dropzone"))
        self.named_pipe_name = transport_config.get("named_pipe_name", r"\\.\pipe\bimspend_revit_events")

        self._processed_files = set()

    def start(self):
        """Start consuming Revit events."""
        self.running = True
        self._thread = threading.Thread(target=self._consume_loop, daemon=True)
        self._thread.start()
        logger.info(f"Revit event consumer started ({self.transport_type})")

    def stop(self):
        """Stop consuming Revit events."""
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Revit event consumer stopped")

    def _consume_loop(self):
        """Main consumption loop."""
        while self.running:
            try:
                if self.transport_type == "dropzone":
                    self._process_dropzone()
                elif self.transport_type == "named_pipe":
                    self._process_named_pipe()

            except Exception as e:
                logger.error(f"Error in Revit consumer loop: {e}")

            time.sleep(1)  # Poll interval

    def _process_dropzone(self):
        """Process events from dropzone directory."""
        if not self.dropzone_path.exists():
            return

        for file_path in sorted(self.dropzone_path.glob("revit_event_*.json")):
            if file_path in self._processed_files:
                continue

            try:
                with open(file_path, "r") as f:
                    event = json.load(f)

                self.correlation_engine.consume_revit_event(event)
                self._processed_files.add(file_path)

                # Archive or delete
                file_path.unlink()

            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")

            # Limit memory
            if len(self._processed_files) > 10000:
                self._processed_files.clear()

    def _process_named_pipe(self):
        """Process events from named pipe (Windows only)."""
        # Named pipe implementation would go here
        # For now, fallback to dropzone
        self._process_dropzone()


class AWQueueConsumer:
    """Consumes AW events from shared SQLite queue."""

    def __init__(self, config: Dict, correlation_engine: CorrelationEngine):
        self.config = config
        self.correlation_engine = correlation_engine
        self.running = False
        self._thread: Optional[threading.Thread] = None

        queue_path = config.get("queue", {}).get("path", "data/bimspend_queue.db")
        self.queue_path = Path(queue_path)
        self._last_processed_id = 0

    def start(self):
        """Start consuming AW events."""
        self.running = True
        self._thread = threading.Thread(target=self._consume_loop, daemon=True)
        self._thread.start()
        logger.info("AW queue consumer started")

    def stop(self):
        """Stop consuming AW events."""
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("AW queue consumer stopped")

    def _consume_loop(self):
        """Main consumption loop."""
        while self.running:
            try:
                self._process_queue()
            except Exception as e:
                logger.error(f"Error in AW queue consumer: {e}")

            time.sleep(2)  # Poll interval

    def _process_queue(self):
        """Process new events from queue."""
        if not self.queue_path.exists():
            return

        with sqlite3.connect(self.queue_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM queue_entries
                WHERE id > ? AND event_type IN ('window.focus.changed', 'afk.state.changed')
                ORDER BY id ASC
            """, (str(self._last_processed_id),))

            for row in cursor.fetchall():
                try:
                    event = json.loads(row["payload"])
                    event_type = event.get("event_type")

                    if event_type == "window.focus.changed":
                        self.correlation_engine.consume_aw_window_event(event)
                    elif event_type == "afk.state.changed":
                        self.correlation_engine.consume_aw_afk_event(event)

                    self._last_processed_id = max(self._last_processed_id, int(row["id"], 16) if row["id"].replace("-", "").isalnum() else 0)

                except Exception as e:
                    logger.error(f"Error processing queue entry: {e}")


class WindowsAdapter:
    """Main Windows Adapter application."""

    def __init__(self, config_path: str):
        self.config = Config(config_path)
        self.running = False

        # Initialize components
        self.queue_writer = QueueWriter(self.config.data.get("queue", {}).get("path", "data/bimspend_queue.db"))
        self.correlation_engine = CorrelationEngine(self.config.data, None, self.queue_writer)
        self.revit_consumer = RevitEventConsumer(self.config.data, self.correlation_engine)
        self.aw_consumer = AWQueueConsumer(self.config.data, self.correlation_engine)
        self.miru_client = MiruClient(self.config.data)

    async def run(self):
        """Run the Windows Adapter."""
        self.running = True
        logger.info(f"Starting Windows Adapter (instance_id={self.config.instance_id})")

        # Start consumers
        self.revit_consumer.start()
        self.aw_consumer.start()

        # Start Miru client
        await self.miru_client.start()

        # Replay any stuck submissions
        self.miru_client.replay_submitting_entries()

        # Main loop
        try:
            while self.running:
                # Periodic flush of correlation engine
                self.correlation_engine.flush()

                # Log queue stats
                stats = self.miru_client.get_queue_stats()
                logger.debug(f"Queue stats: {stats}")

                await asyncio.sleep(30)  # Main loop interval

        except asyncio.CancelledError:
            pass
        finally:
            await self.shutdown()

    async def shutdown(self):
        """Shutdown the adapter."""
        logger.info("Shutting down Windows Adapter...")
        self.running = False

        # Flush pending intervals
        self.correlation_engine.flush()

        # Stop consumers
        self.revit_consumer.stop()
        self.aw_consumer.stop()

        # Stop Miru client
        await self.miru_client.stop()

        logger.info("Windows Adapter stopped")


async def main():
    """Entry point."""
    config_path = os.environ.get(
        "WINDOWS_ADAPTER_CONFIG",
        str(Path(__file__).parent / "config.yaml")
    )

    adapter = WindowsAdapter(config_path)

    # Handle shutdown signals
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(adapter.shutdown()))

    try:
        await adapter.run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    asyncio.run(main())