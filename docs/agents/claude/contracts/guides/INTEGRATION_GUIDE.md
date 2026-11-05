# BIMSpend Integration Guide for OpenCode Implementation Agent

Version: 1.0.0
Status: Draft — Implementation Checkpoint 1
Branch: `build/claude-integration-contracts`

## Overview

This guide describes the integration contracts for the four BIMSpend components:

1. **ActivityWatch Adapter** (`aw-adapter`) — Consumes local AW REST API, emits normalized events
2. **Revit Connector** (`revit-connector`) — Read-only .NET add-in, emits document/view/session events
3. **Windows Adapter** (`windows-adapter`) — Correlates AW + Revit, manages offline queue, submits to Miru
4. **Miru Ingestion Boundary** — Existing `POST /api/v1/agent/timesheet_entries` endpoint

## Component Responsibilities

```
┌─────────────────┐     ┌──────────────────┐     ┌────────────────────┐
│  ActivityWatch  │     │   Revit          │     │   Windows          │
│  (Local Service)│     │   Connector      │     │   Adapter          │
│                 │     │   (.NET Add-in)  │     │   (Python/Rust)    │
│  - aw-server    │     │                  │     │                  │
│  - watchers     │     │  - DocumentOpened│     │  - Correlation   │
│  - REST API     │     │  - ViewActivated │     │  - Idempotency   │
│  :5600 (loopback)     │  - Idling        │     │  - Offline Queue │
└────────┬────────┘     └────────┬─────────┘     └────────┬───────────┘
         │                       │                        │
         │  window.focus.changed │                        │
         │  afk.state.changed    │                        │
         │◄──────────────────────│                        │
         │                       │ revit.document.*       │
         │                       │ revit.view.*           │
         │                       │ revit.application.idling    │
         │                       │◄───────────────────────│
         │                       │                        │
         │                       │                        │ adapter.correlated.activity
         │                       │                        │ adapter.ingestion.draft
         │                       │                        │──────────────────────►
         │                       │                        │                       Miru
         │                       │                        │                       POST /api/v1/agent/timesheet_entries
```

## Implementation Checkpoints

### Checkpoint 1: Event Schemas & Contracts (THIS DELIVERABLE)
- [x] Versioned JSON schemas for all 8 event types
- [x] Common envelope with correlation IDs
- [x] Identity resolution rules
- [x] Idempotency & deduplication rules
- [x] Offline queue interface
- [x] Metric separation (observed/attributed/approved/billed)
- [x] Synthetic test fixtures

### Checkpoint 2: Component Implementation
- [ ] ActivityWatch Adapter (Python)
- [ ] Revit Connector (C# .NET 8 / .NET Framework 4.8)
- [ ] Windows Adapter (Python/Rust)
- [ ] Miru integration client

### Checkpoint 3: Integration Testing
- [ ] Schema validation pipeline
- [ ] Contract tests with synthetic fixtures
- [ ] End-to-end integration test
- [ ] Chaos/recovery tests

## Quick Start for Each Component

### 1. ActivityWatch Adapter (`aw-adapter`)

**Language:** Python 3.9+
**Dependencies:** `aiohttp`, `jsonschema`, `pydantic`, `sqlite3`

**Entry Point:** `aw_adapter/main.py`

**Configuration:**
```yaml
# config/aw_adapter.yaml
aw_server_url: "http://localhost:5600"
poll_interval_seconds: 5
event_types:
  - "window.focus.changed"
  - "afk.state.changed"
output: "local_queue"  # or "stdout" for testing
instance_id: "uuid-v4"  # Generated on first run
```

**Implementation Steps:**
1. Connect to AW REST API `/api/0/buckets/`
2. Poll `/api/0/events/` for `aw-watcher-window` and `aw-watcher-afk` buckets
3. Transform to `window.focus.changed` and `afk.state.changed` events
4. Validate against schemas in `schemas/`
5. Write to local SQLite queue (shared with Windows Adapter)

**Key Classes:**
```python
class AWClient:
    async def get_buckets(self) -> List[Bucket]
    async def get_events(self, bucket_id: str, limit: int) -> List[Event]

class EventTransformer:
    def transform_window_event(self, raw: dict) -> WindowFocusChangedEvent
    def transform_afk_event(self, raw: dict) -> AFKStateChangedEvent

class QueueWriter:
    def enqueue(self, event: BaseEvent) -> str
```

### 2. Revit Connector (`revit-connector`)

**Language:** C# (.NET 8.0 for Revit 2025+, .NET Framework 4.8 for Revit 2021-2024)
**Build:** Multi-target project with conditional compilation
**Signing:** Strong-name + Authenticode (required for production)

**Entry Point:** `RevitConnector/Addin.cs` (implements `IExternalApplication`)

**Events to Subscribe:**
```csharp
// Application events
UIControlledApplication.Application.DocumentOpened += OnDocumentOpened;
UIControlledApplication.Application.DocumentClosed += OnDocumentClosed;
UIControlledApplication.Application.ViewActivated += OnViewActivated;
UIApplication.Idling += OnIdling;  // Use sparingly!

// Helper: UIApplication.Idling is NOT a productivity signal
// Only use for heartbeat when document is active
```

**Event Emission:**
- Write events to named pipe / local TCP / file drop zone
- Windows Adapter reads from same transport
- Recommended: Named pipe `\\.\pipe\bimspend_revit_events`

**Configuration:**
```xml
<!-- RevitConnector.addin -->
<AddIn Type="Application">
  <Name>BIMSpend Revit Connector</Name>
  <Assembly>RevitConnector.dll</Assembly>
  <AddInId>guid-here</AddInId>
  <FullClassName>RevitConnector.Addin</FullClassName>
  <VendorId>BIMSpend</VendorId>
  <VendorDescription>BIMSpend Read-Only Connector</VendorDescription>
</AddIn>
```

**Key Classes:**
```csharp
public class RevitEventEmitter
{
    public void EmitDocumentOpened(Document doc, View activeView) { ... }
    public void EmitDocumentClosed(Document doc, CloseReason reason) { ... }
    public void EmitViewActivated(Document doc, View prev, View current) { ... }
    public void EmitIdling(Document doc, View activeView, bool isForeground) { ... }
}

public class ModelIdentityResolver
{
    public ModelIdentity Resolve(Document doc) { ... }
    // Priority: Admin mapping > ACC > Central GUID > File hash > Unsaved
}
```

### 3. Windows Adapter (`windows-adapter`)

**Language:** Python 3.11+ (or Rust for performance)
**Dependencies:** `aiohttp`, `jsonschema`, `pydantic`, `aiohttp-client`, `sqlite3`, `cryptography`

**Entry Point:** `windows_adapter/main.py`

**Architecture:**
```
┌─────────────────────────────────────────────────────────────┐
│                    Windows Adapter                           │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ AW Event    │  │ Revit Event │  │ Correlation Engine  │  │
│  │ Consumer    │  │ Consumer    │  │                     │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         │                │                     │             │
│         └────────────────┼─────────────────────┘             │
│                          ▼                                   │
│              ┌─────────────────────┐                          │
│              │  Interval Builder   │                          │
│              │  (30-min windows)   │                          │
│              └──────────┬──────────┘                          │
│                         ▼                                     │
│              ┌─────────────────────┐                          │
│              │  Identity Resolver  │                          │
│              │  (Admin > ACC >     │                          │
│              │   Central > Hash)   │                          │
│              └──────────┬──────────┘                          │
│                         ▼                                     │
│              ┌─────────────────────┐                          │
│              │  Confidence Calc    │                          │
│              │  (5 factors)        │                          │
│              └──────────┬──────────┘                          │
│                         ▼                                     │
│              ┌─────────────────────┐                          │
│              │  Offline Queue      │                          │
│              │  (SQLite + WAL)     │                          │
│              └──────────┬──────────┘                          │
│                         ▼                                     │
│              ┌─────────────────────┐                          │
│              │  Submission Worker  │                          │
│              │  (Miru API Client)  │                          │
│              └─────────────────────┘                          │
└─────────────────────────────────────────────────────────────┘
```

**Configuration:**
```yaml
# config/windows_adapter.yaml
instance_id: "uuid-v4"  # Generated on first run
agent_key: "from_env_or_config"
miru_base_url: "https://miru.company.com"
company_id: "uuid-v4"

queue:
  path: "data/bimspend_queue.db"
  max_entries: 10000
  max_age_days: 7

correlation:
  interval_minutes: 30
  confidence_weights:
    revit_foreground: 0.25
    document_match: 0.25
    view_active: 0.15
    afk_excluded: 0.20
    single_revit_process: 0.15
  confidence_thresholds:
    high: 0.80
    medium: 0.50
    low: 0.00

submission:
  batch_size: 50
  interval_seconds: 30
  timeout_seconds: 30
  max_retries: 5

identity:
  admin_mappings_path: "config/admin_mappings.json"
  acc_credentials: "from_env"
```

**Key Classes:**
```python
class CorrelationEngine:
    def consume_aw_event(self, event: WindowFocusChanged | AFKStateChanged) -> None
    def consume_revit_event(self, event: RevitEvent) -> None
    def build_intervals(self) -> List[CorrelatedInterval]

class IdentityResolver:
    def resolve(self, revit_events: List[RevitEvent]) -> ModelIdentity
    def load_admin_mappings(self) -> Dict[str, ProjectMapping]

class ConfidenceCalculator:
    def calculate(self, interval: CorrelatedInterval) -> float

class OfflineQueue:
    def enqueue(self, event: AdapterCorrelatedActivity) -> str
    def dequeue_batch(self, max_batch: int) -> List[QueueEntry]
    def acknowledge(self, entry_id: str) -> None
    def record_failure(self, entry_id: str, error: Error) -> None

class MiruClient:
    async def submit_timesheet_entry(self, entry: AdapterIngestionDraft) -> Result
    async def health_check(self) -> bool
```

### 4. Miru Integration Client

**Use Miru's existing endpoint:** `POST /api/v1/agent/timesheet_entries`

**Authentication:** Bearer token (AgentKey)
```http
Authorization: Bearer <agent_key>
Content-Type: application/json
Idempotency-Key: <external_run_id>
```

**Request Body** (matches `adapter.ingestion.draft` payload):
```json
{
  "timesheet_entry": {
    "external_run_id": "run-uuid",
    "external_session_id": "session-uuid",
    "duration_minutes": 25,
    "work_date": "2026-11-05",
    "project_id": "project-uuid",
    "source": "automation",
    "note": "Correlated Revit activity...",
    "proof_url": "https://bimspend.example.com/evidence/run-uuid",
    "source_metadata": { ... },
    "proof_metadata": { ... }
  }
}
```

**Response Handling:**
- `201 Created` → Success, acknowledge queue entry
- `409 Conflict` → Duplicate, acknowledge queue entry (idempotent)
- `429 Too Many Requests` → Retry with backoff
- `5xx` → Retry with backoff
- `4xx` (except 409, 429) → Dead letter queue

## Shared Infrastructure

### SQLite Queue Schema (Shared by AW Adapter + Windows Adapter)

See `queue/README.md` for full schema.

### Admin Mappings File

```json
// config/admin_mappings.json
{
  "mappings": [
    {
      "mapping_id": "uuid-v4",
      "project_id": "project-uuid-1",
      "project_name": "Project Alpha",
      "model_identity": {
        "type": "workshared_central",
        "central_path": "\\\\server\\central\\Project_A_Central.rvt",
        "central_guid": "11111111-2222-3333-4444-555555555555"
      },
      "is_active": true
    }
  ]
}
```

### Privacy Filter (Windows Adapter)

```python
# Required: Apply before any event leaves adapter
class PrivacyFilter:
    def __init__(self, config_path: str):
        self.allowlist = load_allowlist(config_path)
        self.denylist = load_denylist(config_path)
    
    def filter_window_title(self, title: str) -> str:
        # 1. Check denylist patterns (password, secret, token, etc.)
        # 2. Check allowlist patterns (known project prefixes)
        # 3. Default: hash the title
        if any(p.match(title) for p in self.denylist):
            return "[REDACTED]"
        if any(p.match(title) for p in self.allowlist):
            return title  # Allow known patterns
        return f"[HASH:{sha256(title)[:8]}]"
```

## Testing Checklist

### Per Component

| Component | Schema Validation | Unit Tests | Integration Tests |
|-----------|-------------------|------------|-------------------|
| AW Adapter | ✅ All 2 event types | ✅ Transformer, queue writer | ✅ Against live AW (test instance) |
| Revit Connector | ✅ All 4 event types | ✅ Identity resolver, emitter | ✅ Against Revit test document |
| Windows Adapter | ✅ All 8 event types | ✅ Correlation, confidence, queue | ✅ Full pipeline with fixtures |
| Miru Client | ✅ Ingestion draft | ✅ Retry, idempotency | ✅ Against Miru test instance |

### Cross-Component

- [ ] AW Adapter → Queue → Windows Adapter correlation
- [ ] Revit Connector → Named Pipe → Windows Adapter correlation
- [ ] Windows Adapter → Miru → Idempotency verified
- [ ] Full pipeline: Fixture 1 → Miru draft → 201 Created

## Deployment Notes

### Development

```bash
# Terminal 1: ActivityWatch (local)
aw-server --host localhost --port 5600 --testing

# Terminal 2: AW Adapter
python -m aw_adapter.main --config config/aw_adapter.yaml

# Terminal 3: Revit Connector (load in Revit)
# Build: dotnet build RevitConnector.sln -c Debug
# Copy .addin to %APPDATA%\Autodesk\Revit\Addins\2025\

# Terminal 4: Windows Adapter
python -m windows_adapter.main --config config/windows_adapter.yaml
```

### Production Considerations

1. **Installer**: MSI with per-machine install, auto-start via Task Scheduler
2. **Updates**: Signed binaries, versioned, rollback capability
3. **Monitoring**: Health check endpoint, queue depth metric, submission latency
4. **Logs**: Structured JSON, rotated, no PII
5. **Secrets**: AgentKey from Windows Credential Manager / DPAPI
6. **Telemetry**: Opt-in only, anonymized, no raw events

## Version Compatibility Matrix

| Component | Schema Version | Min Adapter Version | Max Adapter Version |
|-----------|----------------|---------------------|---------------------|
| AW Adapter | 1.0.0 | 1.0.0 | 1.x.x |
| Revit Connector | 1.0.0 | 1.0.0 | 1.x.x |
| Windows Adapter | 1.0.0 | 1.0.0 | 1.x.x |
| Miru Ingestion | 1.0.0 | 1.0.0 | 1.x.x |

**Rule:** MAJOR version mismatch = hard stop. MINOR = log warning, proceed. PATCH = silent.

## Support Contacts

- **Architecture/Contracts:** This document + `schemas/`, `identity/`, `idempotency/`, `queue/`, `metrics/`, `tests/`
- **Miru API:** Miru team / `docs/technical-feasibility/PLAN_AUDIT_REPORT.md` evidence index
- **ActivityWatch:** Upstream docs + local `aw-server --help`
- **Revit API:** Autodesk Revit API docs (linked in PLAN_AUDIT_REPORT.md §11)

## Next Steps for OpenCode

1. **Clone this branch:** `git checkout build/claude-integration-contracts`
2. **Review schemas** in `schemas/` — these are the contract
3. **Implement Checkpoint 2** components per this guide
4. **Run contract tests** in `tests/` against your implementation
5. **Report blockers** via GitHub issues on this branch
6. **Checkpoint 3** will be integration testing and chaos validation

---

**Status:** Checkpoint 1 complete. Ready for Checkpoint 2 implementation.
**Branch:** `build/claude-integration-contracts`
**Base Commit:** `eb13fc90eb768080f6790bb364b482274860688c`