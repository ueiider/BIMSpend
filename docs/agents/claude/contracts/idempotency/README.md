# BIMSpend Integration Contracts — Idempotency & Event Deduplication

Version: 1.0.0
Status: Draft — Implementation Checkpoint 1
Branch: `build/claude-integration-contracts`

## Idempotency Strategy

Two-layer idempotency: **Adapter-side** (offline queue) + **Server-side** (Miru uniqueness constraints).

### Layer 1: Adapter-Side (Offline Queue)

Every correlated activity interval gets a deterministic `external_run_id` and `external_session_id`:

```
external_run_id = SHA256("run" + adapter_instance_id + run_start_utc)[:32]
external_session_id = SHA256("session" + revit_process_id + revit_session_id)[:32]
```

**Properties:**
- Deterministic: same inputs → same IDs
- Collision-resistant: SHA-256 truncated to 32 chars (128 bits)
- Scoped: includes adapter instance to prevent cross-device collisions

### Layer 2: Server-Side (Miru)

Miru `TimesheetEntry` model must enforce uniqueness:

```ruby
# Migration (to be applied by Miru team)
add_index :timesheet_entries, [:agent_id, :external_run_id], unique: true, where: "external_run_id IS NOT NULL"
add_index :timesheet_entries, [:agent_id, :external_session_id], unique: true, where: "external_session_id IS NOT NULL"
```

**Required Miru Changes:**
1. Add unique partial indexes on `external_run_id` and `external_session_id` scoped to `agent_id`
2. Return `409 Conflict` with existing entry ID on duplicate submission
3. Do not create duplicate entries on retry

## Deduplication Rules

### Event-Level Deduplication (Adapter Input)

Raw events from AW/Revit may contain duplicates. Adapter deduplicates before correlation:

| Event Type | Deduplication Key | Window |
|------------|-------------------|--------|
| `window.focus.changed` | `current.process_id + current.window_title` | 5 seconds |
| `afk.state.changed` | `state` | 10 seconds |
| `revit.document.opened` | `document_id` | Session (ignore duplicates) |
| `revit.document.closed` | `document_id` | Session |
| `revit.view.activated` | `document_id + current_view.view_id` | 2 seconds |
| `revit.application.idling` | `process_id + document_id + active_view_id` | 30 seconds |

**Algorithm:** Keep first event in window, discard subsequent with same key.

### Interval-Level Deduplication (Adapter Output)

Correlated intervals submitted to Miru:

1. **Exact duplicate**: Same `external_run_id` → Miru returns 409, adapter marks acknowledged
2. **Overlapping interval**: Same `external_session_id`, overlapping time range → merge or split per policy
3. **Adjacent intervals**: Same session, contiguous → merge into single submission (configurable)

### Merge Policy for Adjacent Intervals

```json
{
  "merge_adjacent": true,
  "max_gap_seconds": 60,
  "max_merged_duration_minutes": 120
}
```

If gap ≤ 60s and merged duration ≤ 120min → combine into single timesheet entry.

## Retry Semantics

### Retryable Errors (Exponential Backoff)

| Error | Max Retries | Base Delay | Max Delay |
|-------|-------------|------------|-----------|
| Network timeout | 5 | 2s | 60s |
| 5xx Server Error | 5 | 2s | 60s |
| 429 Rate Limited | 10 | 5s | 300s |
| DNS/Connection | 5 | 2s | 60s |

### Non-Retryable Errors (Fail Fast → Dead Letter Queue)

| Error | Action |
|-------|--------|
| 400 Bad Request | Log, alert, dead-letter (schema violation) |
| 401/403 Auth | Alert, rotate credentials, dead-letter |
| 404 Not Found | Dead-letter (project deleted?) |
| 409 Conflict | Acknowledge (duplicate), do not retry |
| 422 Unprocessable | Log, alert, dead-letter (validation) |

### Retry Algorithm

```python
def retry_with_backoff(attempt: int, base_delay: float, max_delay: float, jitter: float = 0.1) -> float:
    delay = min(base_delay * (2 ** attempt), max_delay)
    jitter_range = delay * jitter
    return delay + random.uniform(-jitter_range, jitter_range)
```

## Offline Queue Guarantees

### Ordering

- FIFO within same `external_session_id`
- Cross-session: no ordering guarantee (parallel submission OK)

### Acknowledgment

An interval is **acknowledged** only when:
1. Miru returns `201 Created` or `409 Conflict` (duplicate)
2. Response persisted to local acknowledgment log
3. Queue entry marked `acked = true`

### Replay Safety

On adapter restart:
1. Load unacknowledged queue entries
2. Re-submit with same `external_run_id` / `external_session_id`
3. Miru deduplicates via unique indexes
4. Mark acknowledged on success

### Bounded Retention

- Max queue size: 10,000 entries or 7 days, whichever comes first
- Dead-letter entries: retained 30 days for debugging
- Acknowledged entries: purged after 24 hours

## Testing Requirements

### Unit Tests

- [ ] Deterministic ID generation from fixed inputs
- [ ] Deduplication window logic for each event type
- [ ] Merge policy for adjacent intervals
- [ ] Retry backoff calculation
- [ ] Retryable vs non-retryable classification

### Integration Tests (Synthetic)

- [ ] Submit → 201 → ack → restart → no duplicate
- [ ] Submit → 409 → ack → restart → no duplicate
- [ ] Submit → 500 → retry → 201 → ack
- [ ] Submit → 401 → dead-letter → credential rotation → replay → 201
- [ ] Network partition → queue fills → partition heals → drain → all ack
- [ ] Overlapping intervals from clock skew → merge or reject per policy

### Chaos Tests

- [ ] Kill adapter mid-submit → restart → exactly-once
- [ ] Corrupt queue file → recovery → no data loss
- [ ] Miru schema change → 422 → adapter handles gracefully