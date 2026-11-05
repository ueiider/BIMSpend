# BIMSpend Integration Handoff for OpenCode Implementation Agent

**Version:** 1.0.0
**Status:** Ready for Checkpoint 2 Implementation
**Branch:** `build/claude-integration-contracts`
**Base Commit:** `eb13fc90eb768080f6790bb364b482274860688c`

---

## Overview

This document provides the complete integration contracts and implementation specifications for the four BIMSpend components. All schemas, identity rules, idempotency contracts, queue interfaces, and metric separation rules are defined and validated.

**Checkpoint 1 (Contracts) is COMPLETE.** You are now authorized to begin **Checkpoint 2 (Component Implementation)**.

---

## Quick Start

```bash
# 1. Clone the contracts branch
git clone https://github.com/ueiider/BIMSpend.git
cd BIMSpend
git checkout build/claude-integration-contracts

# 2. Review contracts
ls docs/agents/claude/contracts/
# schemas/       - 9 JSON Schema files (8 event types + envelope)
# identity/      - Model identity resolution rules
# idempotency/   - Two-layer idempotency (adapter + server)
# queue/         - SQLite WAL queue interface
# metrics/       - Four-tier metric separation
# tests/         - Contract validation tests & synthetic fixtures
# guides/        - This integration guide

# 3. Run contract tests (should all pass)
cd /c/tmp/bimspend-tests
python tests/test_schemas.py
# Expected: 60/60 tests passing
```

---

## Component Implementation Specifications

### 1. ActivityWatch Adapter (`aw-adapter`)

**Location:** `/c/tmp/bimspend-tests/aw_adapter/`
**Language:** Python 3.9+
**Entry Point:** `aw_adapter/main.py`
**Config:** `aw_adapter/config.yaml`

#### Responsibilities
- Connect to local AW REST API (`http://localhost:5600`)
- Poll `/api/0/buckets/` and `/api/0/events/` for `aw-watcher-window` and `aw-watcher-afk`
- Transform to `window.focus.changed` and `afk.state.changed` events
- Validate against schemas in `schemas/`
- Write to shared SQLite queue (shared with Windows Adapter)
- Apply privacy filter (hash/redact window titles)

#### Key Classes (Implemented in `main.py`)
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

#### Deduplication Rules
| Event Type | Key | Window |
|------------|-----|--------|
| `window.focus.changed` | `current.process_id + current.window_title` | 5 seconds |
| `afk.state.changed` | `state` | 10 seconds |

#### Testing
```bash
cd /c/tmp/bimspend-tests/aw_adapter
python test_aw_adapter.py          # Unit tests
python test_schema_validation.py   # Schema validation
```

---

### 2. Revit Connector (`revit-connector`)

**Location:** `/c/tmp/bimspend-tests/revit_connector/RevitConnector/`
**Language:** C# (.NET 8.0 for Revit 2025+, .NET Framework 4.8 for Revit 2021-2024)
**Build:** Multi-target project (`RevitConnector.csproj`)
**Entry Point:** `Addin.cs` (implements `IExternalApplication`)
**Transport:** Named pipe `\\.\pipe\bimspend_revit_events` + file drop zone fallback
**Config:** `admin_mappings.json` (in CommonApplicationData/BIMSpend/config/)

#### Events to Subscribe
```csharp
UIControlledApplication.Application.DocumentOpened += OnDocumentOpened;
UIControlledApplication.Application.DocumentClosed += OnDocumentClosed;
UIControlledApplication.Application.DocumentSaved += OnDocumentSaved;
UIControlledApplication.Application.DocumentSavedAs += OnDocumentSavedAs;
UIControlledApplication.ViewActivated += OnViewActivated;
UIApplication.Idling += OnIdling;  // Use sparingly - heartbeat only
```

#### Event Emission
- Write events to named pipe / file drop zone
- Windows Adapter reads from same transport
- Events: `revit.document.opened`, `revit.document.closed`, `revit.view.activated`, `revit.application.idling`, `identity.remapped`

#### Identity Resolution (Implemented in `Identity/ModelIdentityResolver.cs`)
Priority hierarchy:
1. **Explicit Admin Mapping** (highest) - BIMSpend Project ID ↔ Approved Model Identity
2. **ACC/Cloud Identifiers** - ACC Project ID + ACC Model ID
3. **Workshared Central Identity** - Normalized Central Path + Central GUID
4. **Standalone File Identity** - Normalized Path + File Hash (SHA-256)
5. **Unsaved/New Document** (lowest) - Never auto-post approved time

#### Key Classes
```csharp
public class EventEmitter
{
    public void EmitDocumentOpened(Document doc, View activeView) { ... }
    public void EmitDocumentClosed(Document doc, CloseReason reason) { ... }
    public void EmitViewActivated(Document doc, View prev, View current) { ... }
    public void EmitIdling(Document doc, View activeView, bool isForeground) { ... }
    public void EmitIdentityRemapped(Document doc, string oldPath, string trigger) { ... }
}

public class ModelIdentityResolver
{
    public ModelIdentity Resolve(Document doc) { ... }
    public ModelIdentity ResolveFromPath(string filePath) { ... }
    // Priority: Admin mapping > ACC > Central GUID > File hash > Unsaved
}
```

#### Build & Install
```bash
# Build
dotnet build RevitConnector.sln -c Debug

# Install .addin to Revit addins folder
# %APPDATA%\Autodesk\Revit\Addins\2025\RevitConnector.addin
```

---

### 3. Windows Adapter (`windows-adapter`)

**Location:** `/c/tmp/bimspend-tests/windows_adapter/`
**Language:** Python 3.11+
**Entry Point:** `main.py`
**Config:** `config.yaml`

#### Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    Windows Adapter                           │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ AW Queue    │  │ Revit Drop  │  │ Correlation Engine  │  │
│  │ Consumer    │  │ Zone Consumer│  │                     │  │
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

#### Key Modules
- `correlation_engine.py` - `CorrelationEngine`, `QueueWriter`
- `miru_client.py` - `MiruClient` with retry/backoff/dead-letter
- `metrics_enforcer.py` - `MetricsEnforcer` for metric separation
- `main.py` - Orchestrates all components

#### Correlation Algorithm
1. Maintain per-process Revit state (document, view, foreground)
2. Track window focus to know when Revit is foreground
3. Track AFK state to exclude away time
4. Build 30-minute intervals (configurable)
5. Calculate confidence based on 5 factors:
   - `revit_foreground` (0.25) - Revit is foreground window
   - `document_match` (0.25) - Active document matches mapped identity
   - `view_active` (0.15) - Active view is working view (not sheet/schedule)
   - `afk_excluded` (0.20) - AFK state is not_afk
   - `single_revit_process` (0.15) - Only one Revit process running
6. Resolve project identity via IdentityResolver
7. Submit `adapter.correlated.activity` + `adapter.ingestion.draft` (if confidence ≥ 0.5)

#### Confidence Thresholds
| Level | Threshold | Action |
|-------|-----------|--------|
| High | ≥ 0.80 | Auto-submit draft |
| Medium | 0.50–0.79 | Submit draft, flag for review |
| Low | < 0.50 | Queue locally only, do not submit |

#### Testing
```bash
cd /c/tmp/bimspend-tests/windows_adapter
python -c "from correlation_engine import CorrelationEngine; print('OK')"
python -c "from miru_client import MiruClient; print('OK')"
python -c "from metrics_enforcer import MetricsEnforcer; print('OK')"
```

---

### 4. Miru Integration Client

**Use Miru's existing endpoint:** `POST /api/v1/agent/timesheet_entries`

#### Authentication
```http
Authorization: Bearer <agent_key>
Content-Type: application/json
Idempotency-Key: <external_run_id>
```

#### Request Body (matches `adapter.ingestion.draft` payload)
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

#### Response Handling (Implemented in `miru_client.py`)
| Status | Action |
|--------|--------|
| `201 Created` | Success, acknowledge queue entry |
| `409 Conflict` | Duplicate, acknowledge (idempotent) |
| `429 Too Many Requests` | Retry with backoff |
| `5xx` | Retry with backoff |
| `4xx` (except 409, 429) | Dead letter queue |

#### Server-Side Requirements (Miru Team)
```ruby
# Migration required
add_index :timesheet_entries, [:agent_id, :external_run_id], unique: true, where: "external_run_id IS NOT NULL"
add_index :timesheet_entries, [:agent_id, :external_session_id], unique: true, where: "external_session_id IS NOT NULL"

# Policy: automation entries default to pending_review
# Cannot change review_status to approved without privileged role
```

---

## Shared Infrastructure

### SQLite Queue Schema (Shared by AW Adapter + Windows Adapter)
See `queue/README.md` for full schema.

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
```

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
class PrivacyFilter:
    def filter_window_title(self, title: str) -> str:
        # 1. Check denylist patterns (password, secret, token, etc.)
        # 2. Check allowlist patterns (known project prefixes)
        # 3. Default: hash the title
        if any(p.match(title) for p in self.denylist):
            return "[REDACTED]"
        if any(p.match(title) for p in self.allowlist):
            return title
        return f"[HASH:{sha256(title)[:8]}]"
```

---

## Contract Test Suite

All tests in `/c/tmp/bimspend-tests/tests/`:

```bash
# Schema validation (60 tests)
python tests/test_schemas.py

# Test categories:
# - Schema self-validation (9/9)
# - Valid fixture validation (8/8)
# - Invalid fixture rejection (6/6)
# - Version format (8/8)
# - Required field enforcement (8/8)
# - Timestamp format validation (10/10)
# - UUID validation (7/7)
# - Cross-event correlation (2/2)
# - Privacy assertions (2/2)
# - Cross-reference resolution (1/1)
```

### Synthetic Fixtures (in `tests/fixtures/`)
- **Valid (8):** One per event type with real UUIDs
- **Invalid (6):** Negative tests for enum, required fields, additionalProperties

### Integration Fixtures (in `contracts/tests/README.md`)
- Fixture 1: Standard Revit Session (3hr, 1 AFK break)
- Fixture 2: Multi-Document Session
- Fixture 3: Dual Revit Processes
- Fixture 4: Save As / Remapping

---

## Implementation Checklist for OpenCode

### Per Component
- [ ] **AW Adapter**: Schema validation, transformer, queue writer, privacy filter
- [ ] **Revit Connector**: All 4 event types, identity resolver, emitter, transport
- [ ] **Windows Adapter**: Correlation, confidence, queue, Miru client, metrics enforcer
- [ ] **Miru Client**: Retry, idempotency, dead-letter, health check

### Cross-Component
- [ ] AW Adapter → Queue → Windows Adapter correlation
- [ ] Revit Connector → Dropzone/Named Pipe → Windows Adapter correlation
- [ ] Windows Adapter → Miru → Idempotency verified
- [ ] Full pipeline: Fixture 1 → Miru draft → 201 Created

### Quality Gates
- [ ] All contract tests pass (60/60)
- [ ] Schema validation on every event emission
- [ ] Privacy filter applied before any event leaves adapter
- [ ] Deterministic external_run_id/external_session_id generation
- [ ] Crash recovery: submitting entries replayed on restart
- [ ] Metric separation enforced at each boundary

---

## Configuration Reference

### AW Adapter (`aw_adapter/config.yaml`)
```yaml
aw_server_url: "http://localhost:5600"
poll_interval_seconds: 5
instance_id: "uuid-v4"  # Generated on first run
queue:
  path: "data/bimspend_queue.db"
  max_entries: 10000
  max_age_days: 7
privacy:
  enabled: true
  denylist_patterns: ["password", "secret", "token", "api_key"]
```

### Windows Adapter (`windows_adapter/config.yaml`)
```yaml
instance_id: "uuid-v4"
agent_key: "from_env_or_config"
miru_base_url: "https://miru.company.com"
company_id: "uuid-v4"
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
```

### Revit Connector (`admin_mappings.json`)
See `/c/tmp/bimspend-tests/revit_connector/admin_mappings.json`

---

## Development Workflow

```bash
# Terminal 1: ActivityWatch (local)
aw-server --host localhost --port 5600 --testing

# Terminal 2: AW Adapter
cd /c/tmp/bimspend-tests/aw_adapter
python main.py --config config.yaml

# Terminal 3: Revit Connector (load in Revit)
# Build: dotnet build RevitConnector.sln -c Debug
# Copy .addin to %APPDATA%\Autodesk\Revit\Addins\2025\

# Terminal 4: Windows Adapter
cd /c/tmp/bimspend-tests/windows_adapter
export MIRU_AGENT_KEY="your-agent-key"
export MIRU_COMPANY_ID="your-company-id"
python main.py --config config.yaml
```

---

## Support Contacts

- **Architecture/Contracts:** This document + `contracts/` directory
- **Miru API:** Miru team / `docs/technical-feasibility/PLAN_AUDIT_REPORT.md`
- **ActivityWatch:** Upstream docs + `aw-server --help`
- **Revit API:** Autodesk Revit API docs

---

## Next Steps

1. **Implement Checkpoint 2** components per this guide
2. **Run contract tests** against your implementation
3. **Report blockers** via GitHub issues on `build/claude-integration-contracts` branch
4. **Checkpoint 3** will be integration testing and chaos validation

---

**Status:** Checkpoint 1 complete. Ready for Checkpoint 2 implementation.
**Branch:** `build/claude-integration-contracts`