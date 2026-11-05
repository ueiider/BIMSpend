# BIMSpend Integration Contracts — Offline Queue Interface & Retry Semantics

Version: 1.0.0
Status: Draft — Implementation Checkpoint 1
Branch: `build/claude-integration-contracts`

## Queue Interface

### Data Model

```typescript
interface QueueEntry {
  id: string;                    // UUIDv4, queue-internal
  event_type: "adapter.correlated.activity" | "adapter.ingestion.draft";
  payload: object;               // Full event payload (validated)
  external_run_id: string;       // Idempotency key
  external_session_id: string;   // Idempotency key
  status: "pending" | "submitting" | "acked" | "dead_letter";
  attempts: number;
  last_attempt_utc: string | null;
  next_retry_utc: string | null;
  created_utc: string;
  acked_utc: string | null;
  error: {
    code: string;
    message: string;
    http_status: number | null;
    response_body: string | null;
  } | null;
  metadata: {
    correlation_confidence: number;
    project_id: string;
    interval_start_utc: string;
    interval_end_utc: string;
  };
}
```

### Storage

**Primary:** SQLite database (`bimspend_queue.db`) with WAL mode for durability.
**Backup:** Periodic JSONL export to `queue_backup_YYYYMMDD.jsonl`.

Schema:
```sql
CREATE TABLE queue_entries (
  id TEXT PRIMARY KEY,
  event_type TEXT NOT NULL,
  payload TEXT NOT NULL,           -- JSON
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
);

CREATE INDEX idx_queue_status_next_retry ON queue_entries(status, next_retry_utc);
CREATE INDEX idx_queue_external_run ON queue_entries(external_run_id);
CREATE INDEX idx_queue_external_session ON queue_entries(external_session_id);
CREATE INDEX idx_queue_created ON queue_entries(created_utc);
```

### Operations

#### Enqueue

```python
def enqueue(event: dict, metadata: dict) -> str:
    """Add validated event to queue. Returns queue entry ID."""
    entry = QueueEntry(
        id=uuid4(),
        event_type=event["event_type"],
        payload=event,
        external_run_id=event["correlation"]["external_run_id"],
        external_session_id=event["correlation"]["external_session_id"],
        status="pending",
        attempts=0,
        last_attempt_utc=None,
        next_retry_utc=now_utc(),  # Immediate first attempt
        created_utc=now_utc(),
        acked_utc=None,
        error=None,
        metadata=metadata
    )
    db.insert(entry)
    return entry.id
```

#### Dequeue (for Submission Worker)

```python
def dequeue_batch(max_batch: int = 50) -> List[QueueEntry]:
    """Get pending entries ready for submission, ordered by priority."""
    # Priority: higher confidence first, then older entries
    return db.query("""
        SELECT * FROM queue_entries
        WHERE status IN ('pending', 'submitting')
          AND (next_retry_utc IS NULL OR next_retry_utc <= ?)
        ORDER BY correlation_confidence DESC, created_utc ASC
        LIMIT ?
    """, (now_utc(), max_batch))
```

#### Mark Submitting

```python
def mark_submitting(entry_ids: List[str]) -> None:
    db.execute("""
        UPDATE queue_entries
        SET status = 'submitting', last_attempt_utc = ?
        WHERE id IN ({})
    """.format(",".join("?" * len(entry_ids))), (now_utc(), *entry_ids))
```

#### Acknowledge

```python
def acknowledge(entry_id: str, response: dict) -> None:
    """Mark entry as successfully submitted (201 or 409)."""
    db.execute("""
        UPDATE queue_entries
        SET status = 'acked', acked_utc = ?, error = NULL
        WHERE id = ?
    """, (now_utc(), entry_id))
```

#### Record Failure

```python
def record_failure(entry_id: str, error: dict) -> None:
    """Record failure, schedule retry or dead-letter."""
    entry = db.get(entry_id)
    new_attempts = entry.attempts + 1
    
    if is_retryable(error) and new_attempts <= MAX_RETRIES[error.type]:
        next_retry = calculate_backoff(new_attempts, error.type)
        status = "pending"
    else:
        next_retry = None
        status = "dead_letter"
    
    db.execute("""
        UPDATE queue_entries
        SET status = ?, attempts = ?, last_attempt_utc = ?,
            next_retry_utc = ?, error_code = ?, error_message = ?,
            error_http_status = ?, error_response_body = ?
        WHERE id = ?
    """, (status, new_attempts, now_utc(), next_retry,
          error.code, error.message, error.http_status, error.response_body,
          entry_id))
```

## Submission Worker

### Concurrency Model

- Single writer (submission worker) per adapter instance
- Multiple adapter instances → each has own queue DB → no coordination needed
- Miru handles deduplication via unique indexes

### Batch Submission

```python
async def submit_batch(entries: List[QueueEntry]) -> List[Result]:
    """Submit batch to Miru, return per-entry results."""
    results = []
    for entry in entries:
        try:
            response = await http_post(
                f"{MIRU_BASE_URL}/api/v1/agent/timesheet_entries",
                headers={
                    "Authorization": f"Bearer {AGENT_KEY}",
                    "Content-Type": "application/json",
                    "Idempotency-Key": entry.external_run_id  # Additional header
                },
                json=entry.payload["payload"],
                timeout=30
            )
            if response.status in (201, 409):
                results.append(Result(entry.id, "acked", response))
            elif is_retryable(response):
                results.append(Result(entry.id, "retry", response))
            else:
                results.append(Result(entry.id, "dead_letter", response))
        except Exception as e:
            results.append(Result(entry.id, "retry", e))
    return results
```

### Scheduler

- Run every 30 seconds when online
- Immediate flush on network reconnect
- Exponential backoff per-entry (not global)

## Retry Semantics

### Retryable Conditions

| Condition | HTTP Status | Max Retries | Backoff |
|-----------|-------------|-------------|---------|
| Network error | N/A | 5 | 2s, 4s, 8s, 16s, 32s (max 60s) |
| Server error | 500, 502, 503, 504 | 5 | 2s, 4s, 8s, 16s, 32s (max 60s) |
| Rate limited | 429 | 10 | 5s, 10s, 20s, 40s, 80s, 160s, 300s (max 5min) |
| Timeout | N/A | 3 | 5s, 10s, 20s |

### Non-Retryable (Immediate Dead Letter)

| Condition | HTTP Status | Reason |
|-----------|-------------|--------|
| Bad request | 400 | Schema/contract violation |
| Unauthorized | 401 | Invalid/expired agent key |
| Forbidden | 403 | Agent not authorized for project |
| Not found | 404 | Project deleted |
| Conflict | 409 | Duplicate (already acknowledged) |
| Unprocessable | 422 | Validation failure |

### Dead Letter Queue

- Separate table `dead_letter_entries` with same schema + `failure_reason`
- Retained 30 days
- Admin tooling for inspection, manual replay, or purge
- Alert on dead-letter count > 100

## Durability Guarantees

### Write-Ahead Logging

- SQLite WAL mode: commits durable on `fsync`
- `PRAGMA synchronous = FULL` for maximum durability
- Queue entry persisted before `enqueue()` returns

### Power Loss / Crash Recovery

On restart:
1. Open queue DB (WAL auto-recovers)
2. Find entries with `status = 'submitting'` → these may have been submitted but not acked
3. For each: re-submit with same `external_run_id` (Miru deduplicates)
4. If 201/409 → ack; if other → treat as failure

### Disk Space Protection

- Max queue entries: 10,000
- Max queue age: 7 days
- On limit: pause enqueue, alert, oldest dead-letter purged first
- Background vacuum weekly

## Testing Requirements

### Unit Tests

- [ ] Enqueue → persist → restart → entry present
- [ ] Dequeue priority ordering (confidence, age)
- [ ] Mark submitting → ack → entry removed
- [ ] Failure → retry scheduling → backoff calculation
- [ ] Dead letter on non-retryable error
- [ ] Dead letter on max retries exceeded
- [ ] Crash recovery: submitting entries re-submitted

### Integration Tests

- [ ] Full flow: enqueue → submit → 201 → ack
- [ ] Duplicate submit: enqueue → submit → 409 → ack
- [ ] Retry flow: 500 → retry → 201 → ack
- [ ] Rate limit: 429 → backoff → 201 → ack
- [ ] Network partition: queue fills → heal → drain
- [ ] Concurrent adapter instances: independent queues, Miru deduplicates

### Chaos Tests

- [ ] Kill process mid-submit → restart → exactly-once
- [ ] Corrupt WAL → recovery
- [ ] Disk full → graceful degradation
- [ ] Clock skew → backoff calculation correct