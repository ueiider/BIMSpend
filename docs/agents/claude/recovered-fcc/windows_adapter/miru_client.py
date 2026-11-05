#!/usr/bin/env python3
"""
Miru API Client for Windows Adapter

Handles submission of timesheet entries to Miru with:
- Idempotency via external_run_id/external_session_id
- Exponential backoff retry
- Dead letter queue for non-retryable errors
"""

import asyncio
import json
import logging
import os
import random
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger("miru_client")


@dataclass
class SubmissionResult:
    entry_id: str
    status: str  # "acked", "retry", "dead_letter"
    http_status: Optional[int] = None
    response_body: Optional[str] = None
    error: Optional[str] = None


class MiruClient:
    """
    Client for submitting timesheet entries to Miru API.
    """

    # Retryable HTTP status codes
    RETRYABLE_STATUS = {429, 500, 502, 503, 504}
    # Non-retryable (dead letter immediately)
    DEAD_LETTER_STATUS = {400, 401, 403, 404, 409, 422}

    # Max retries per error type
    MAX_RETRIES = {
        "network": 5,
        "timeout": 3,
        "server_error": 5,
        "rate_limit": 10,
    }

    # Backoff base delays (seconds)
    BASE_DELAYS = {
        "network": 2,
        "timeout": 5,
        "server_error": 2,
        "rate_limit": 5,
    }

    # Max delays (seconds)
    MAX_DELAYS = {
        "network": 60,
        "timeout": 20,
        "server_error": 60,
        "rate_limit": 300,
    }

    def __init__(self, config: Dict):
        self.config = config
        self.base_url = config.get("miru_base_url", "").rstrip("/")
        self.agent_key = config.get("agent_key", "") or os.environ.get("MIRU_AGENT_KEY", "")
        self.company_id = config.get("company_id", "") or os.environ.get("MIRU_COMPANY_ID", "")
        self.timeout = config.get("submission", {}).get("timeout_seconds", 30)
        self.batch_size = config.get("submission", {}).get("batch_size", 50)
        self.interval = config.get("submission", {}).get("interval_seconds", 30)

        # Queue database
        queue_path = config.get("queue", {}).get("path", "data/bimspend_queue.db")
        self.queue_path = Path(queue_path)

        # Session for connection pooling
        self._session: Optional[aiohttp.ClientSession] = None
        self._running = False
        self._submit_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the submission worker."""
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={
                "Authorization": f"Bearer {self.agent_key}",
                "Content-Type": "application/json",
            }
        )
        self._running = True
        self._submit_task = asyncio.create_task(self._submission_loop())
        logger.info("Miru client started")

    async def stop(self):
        """Stop the submission worker."""
        self._running = False
        if self._submit_task:
            self._submit_task.cancel()
            try:
                await self._submit_task
            except asyncio.CancelledError:
                pass
        if self._session:
            await self._session.close()
        logger.info("Miru client stopped")

    async def _submission_loop(self):
        """Main submission loop."""
        while self._running:
            try:
                await self._process_batch()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Submission loop error: {e}")

            await asyncio.sleep(self.interval)

    async def _process_batch(self):
        """Process a batch of pending queue entries."""
        entries = self._dequeue_batch(self.batch_size)
        if not entries:
            return

        entry_ids = [e["id"] for e in entries]
        self._mark_submitting(entry_ids)

        results = await asyncio.gather(
            *[self._submit_entry(e) for e in entries],
            return_exceptions=True
        )

        for entry, result in zip(entries, results):
            if isinstance(result, Exception):
                logger.error(f"Submission error for {entry['id']}: {result}")
                self._record_failure(entry["id"], {
                    "code": "exception",
                    "message": str(result),
                    "http_status": None,
                    "response_body": None,
                })
            elif result.status == "acked":
                self._acknowledge(entry["id"])
            elif result.status == "retry":
                self._record_failure(entry["id"], {
                    "code": result.error or "retryable",
                    "message": result.response_body or "Retryable error",
                    "http_status": result.http_status,
                    "response_body": result.response_body,
                })
            elif result.status == "dead_letter":
                self._record_failure(entry["id"], {
                    "code": result.error or "dead_letter",
                    "message": result.response_body or "Non-retryable error",
                    "http_status": result.http_status,
                    "response_body": result.response_body,
                })

    def _dequeue_batch(self, max_batch: int) -> List[Dict]:
        """Get pending entries ready for submission."""
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        with sqlite3.connect(self.queue_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM queue_entries
                WHERE status IN ('pending', 'submitting')
                  AND (next_retry_utc IS NULL OR next_retry_utc <= ?)
                ORDER BY correlation_confidence DESC, created_utc ASC
                LIMIT ?
            """, (now, max_batch))
            return [dict(row) for row in cursor.fetchall()]

    def _mark_submitting(self, entry_ids: List[str]) -> None:
        """Mark entries as submitting."""
        if not entry_ids:
            return
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        placeholders = ",".join("?" * len(entry_ids))
        with sqlite3.connect(self.queue_path) as conn:
            conn.execute(f"""
                UPDATE queue_entries
                SET status = 'submitting', last_attempt_utc = ?
                WHERE id IN ({placeholders})
            """, (now, *entry_ids))
            conn.commit()

    def _acknowledge(self, entry_id: str) -> None:
        """Mark entry as acknowledged."""
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        with sqlite3.connect(self.queue_path) as conn:
            conn.execute("""
                UPDATE queue_entries
                SET status = 'acked', acked_utc = ?, error_code = NULL, error_message = NULL,
                    error_http_status = NULL, error_response_body = NULL
                WHERE id = ?
            """, (now, entry_id))
            conn.commit()
        logger.debug(f"Acknowledged entry {entry_id}")

    def _record_failure(self, entry_id: str, error: Dict) -> None:
        """Record failure and schedule retry or dead-letter."""
        # Get current entry
        with sqlite3.connect(self.queue_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM queue_entries WHERE id = ?", (entry_id,))
            entry = cursor.fetchone()

        if not entry:
            logger.warning(f"Entry {entry_id} not found for failure recording")
            return

        new_attempts = entry["attempts"] + 1
        error_type = self._classify_error(error)
        is_retryable = self._is_retryable(error, error_type)
        max_retries = self.MAX_RETRIES.get(error_type, 3)

        if is_retryable and new_attempts <= max_retries:
            # Schedule retry
            delay = self._calculate_backoff(new_attempts, error_type)
            next_retry = datetime.now(timezone.utc).timestamp() + delay
            next_retry_utc = datetime.fromtimestamp(next_retry, tz=timezone.utc).isoformat().replace("+00:00", "Z")
            status = "pending"
        else:
            # Dead letter
            next_retry_utc = None
            status = "dead_letter"
            logger.warning(f"Entry {entry_id} moved to dead letter after {new_attempts} attempts")

        with sqlite3.connect(self.queue_path) as conn:
            conn.execute("""
                UPDATE queue_entries
                SET status = ?, attempts = ?, last_attempt_utc = ?,
                    next_retry_utc = ?, error_code = ?, error_message = ?,
                    error_http_status = ?, error_response_body = ?
                WHERE id = ?
            """, (
                status,
                new_attempts,
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                next_retry_utc,
                error.get("code"),
                error.get("message"),
                error.get("http_status"),
                error.get("response_body"),
                entry_id,
            ))
            conn.commit()

    def _classify_error(self, error: Dict) -> str:
        """Classify error type for retry policy."""
        http_status = error.get("http_status")
        if http_status == 429:
            return "rate_limit"
        elif http_status and 500 <= http_status < 600:
            return "server_error"
        elif http_status is None:
            return "network"
        else:
            return "network"

    def _is_retryable(self, error: Dict, error_type: str) -> bool:
        """Check if error is retryable."""
        http_status = error.get("http_status")
        if http_status in self.DEAD_LETTER_STATUS:
            return False
        if http_status in self.RETRYABLE_STATUS:
            return True
        if http_status is None:  # Network error
            return True
        return False

    def _calculate_backoff(self, attempt: int, error_type: str) -> float:
        """Calculate exponential backoff with jitter."""
        base = self.BASE_DELAYS.get(error_type, 2)
        max_delay = self.MAX_DELAYS.get(error_type, 60)
        delay = min(base * (2 ** (attempt - 1)), max_delay)
        jitter = delay * 0.1
        return delay + random.uniform(-jitter, jitter)

    async def _submit_entry(self, entry: Dict) -> SubmissionResult:
        """Submit a single queue entry to Miru."""
        entry_id = entry["id"]
        external_run_id = entry["external_run_id"]
        payload = json.loads(entry["payload"])

        # Only submit ingestion drafts to Miru
        if entry["event_type"] != "adapter.ingestion.draft":
            return SubmissionResult(entry_id, "acked")

        try:
            # Build request body from ingestion draft
            timesheet_entry = payload["payload"]["timesheet_entry"]
            request_body = {"timesheet_entry": timesheet_entry}

            # Add idempotency header
            headers = {
                "Idempotency-Key": external_run_id,
            }

            url = f"{self.base_url}/api/v1/agent/timesheet_entries"

            async with self._session.post(url, json=request_body, headers=headers) as resp:
                response_body = await resp.text()

                if resp.status == 201:
                    logger.info(f"Successfully submitted {entry_id} (run_id={external_run_id})")
                    return SubmissionResult(entry_id, "acked", resp.status, response_body)

                elif resp.status == 409:
                    # Duplicate - already exists, treat as success
                    logger.info(f"Duplicate submission {entry_id} (run_id={external_run_id}) - 409 Conflict")
                    return SubmissionResult(entry_id, "acked", resp.status, response_body)

                elif resp.status in self.RETRYABLE_STATUS:
                    return SubmissionResult(entry_id, "retry", resp.status, response_body, f"HTTP {resp.status}")

                else:
                    return SubmissionResult(entry_id, "dead_letter", resp.status, response_body, f"HTTP {resp.status}")

        except asyncio.TimeoutError:
            return SubmissionResult(entry_id, "retry", None, None, "Timeout")
        except aiohttp.ClientError as e:
            return SubmissionResult(entry_id, "retry", None, None, f"Client error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error submitting {entry_id}: {e}")
            return SubmissionResult(entry_id, "dead_letter", None, None, f"Exception: {e}")

    async def health_check(self) -> bool:
        """Check Miru API health."""
        if not self._session:
            return False

        try:
            async with self._session.get(f"{self.base_url}/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                return resp.status == 200
        except Exception:
            return False

    def get_queue_stats(self) -> Dict:
        """Get queue statistics."""
        with sqlite3.connect(self.queue_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT
                    status,
                    COUNT(*) as count
                FROM queue_entries
                GROUP BY status
            """)
            stats = {row["status"]: row["count"] for row in cursor.fetchall()}

            # Get oldest pending
            cursor = conn.execute("""
                SELECT created_utc FROM queue_entries
                WHERE status = 'pending'
                ORDER BY created_utc ASC
                LIMIT 1
            """)
            oldest = cursor.fetchone()
            stats["oldest_pending"] = oldest["created_utc"] if oldest else None

            return stats

    def replay_submitting_entries(self) -> int:
        """Replay entries stuck in 'submitting' state (crash recovery)."""
        with sqlite3.connect(self.queue_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT id FROM queue_entries WHERE status = 'submitting'")
            entries = cursor.fetchall()

        count = 0
        for entry in entries:
            # Reset to pending for retry
            with sqlite3.connect(self.queue_path) as conn:
                conn.execute("""
                    UPDATE queue_entries
                    SET status = 'pending', next_retry_utc = ?
                    WHERE id = ?
                """, (datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), entry["id"]))
                conn.commit()
            count += 1

        if count > 0:
            logger.info(f"Replayed {count} submitting entries")

        return count