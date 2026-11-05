# BIMSpend Integration Contracts — Event Schemas

Version: 1.0.0
Status: Draft — Implementation Checkpoint 1
Branch: `build/claude-integration-contracts`

## Schema Versioning

All schemas use semantic versioning in the `schema_version` field:
- `MAJOR`: Breaking changes (field removal, type change, semantic change)
- `MINOR`: Backward-compatible additions (new optional fields, new enum values)
- `PATCH`: Clarifications, bug fixes in validation rules

Consumers MUST validate `schema_version` and reject events with unsupported MAJOR versions.

## Event Envelope

All events share a common envelope:

```json
{
  "event_id": "uuid-v4",
  "event_type": "string",
  "schema_version": "1.0.0",
  "timestamp_utc": "2026-11-05T12:34:56.789Z",
  "source": {
    "component": "revit-connector|aw-adapter|windows-adapter",
    "version": "1.0.0",
    "instance_id": "uuid-v4",
    "process_id": 12345
  },
  "correlation": {
    "session_id": "uuid-v4",
    "run_id": "uuid-v4",
    "external_run_id": "string",
    "external_session_id": "string"
  },
  "payload": {}
}
```

### Field Requirements

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| event_id | YES | UUIDv4 | Globally unique event identifier |
| event_type | YES | string | One of registered event types |
| schema_version | YES | semver | Schema version for this event_type |
| timestamp_utc | YES | ISO8601 UTC | Event creation timestamp |
| source.component | YES | enum | Originating component |
| source.version | YES | semver | Component version |
| source.instance_id | YES | UUIDv4 | Component instance identifier |
| source.process_id | YES | integer | OS process ID |
| correlation.session_id | YES | UUIDv4 | Logical session (Revit session, AW session) |
| correlation.run_id | YES | UUIDv4 | Execution run (adapter run, connector run) |
| correlation.external_run_id | NO | string | Miru AgentKey external_run_id |
| correlation.external_session_id | NO | string | Miru AgentKey external_session_id |

## Registered Event Types

### 1. `window.focus.changed` — ActivityWatch Window Watcher

Emitted when foreground window changes.

```json
{
  "event_type": "window.focus.changed",
  "schema_version": "1.0.0",
  "payload": {
    "previous": {
      "app_name": "string|null",
      "window_title": "string|null",
      "process_id": "integer|null",
      "exe_path": "string|null"
    },
    "current": {
      "app_name": "Revit.exe",
      "window_title": "Project_A.rvt - Autodesk Revit 2025",
      "process_id": 8842,
      "exe_path": "C:\\Program Files\\Autodesk\\Revit 2025\\Revit.exe"
    },
    "transition_type": "foreground_gained|foreground_lost|app_switch|title_change",
    "idle_state": "active|idle|away",
    "monitor_info": {
      "monitor_count": 2,
      "primary_monitor": 0
    }
  }
}
```

**Privacy Rule**: `window_title` MUST be processed through privacy filter before leaving adapter. Raw titles never transmitted to Miru.

### 2. `afk.state.changed` — ActivityWatch AFK Watcher

Emitted on AFK/not-AFK transitions.

```json
{
  "event_type": "afk.state.changed",
  "schema_version": "1.0.0",
  "payload": {
    "state": "afk|not_afk",
    "idle_duration_seconds": 300,
    "trigger": "mouse|keyboard|timeout",
    "previous_state": "not_afk|afk|null"
  }
}
```

### 3. `revit.document.opened` — Revit Connector

Emitted when a document is opened in Revit.

```json
{
  "event_type": "revit.document.opened",
  "schema_version": "1.0.0",
  "payload": {
    "document": {
      "document_id": "uuid-v4",
      "title": "Project_A.rvt",
      "path": "C:\\Projects\\Project_A\\Project_A.rvt",
      "is_workshared": true,
      "central_path": "\\\\server\\central\\Project_A_Central.rvt",
      "central_guid": "guid-string",
      "version_number": 42,
      "last_saved_by": "user@domain.com",
      "last_saved_utc": "2026-11-05T10:00:00Z",
      "is_detached": false,
      "is_new": false
    },
    "view": {
      "view_id": "integer",
      "view_name": "Level 1 - Floor Plan",
      "view_type": "FloorPlan"
    },
    "process": {
      "process_id": 8842,
      "session_id": "uuid-v4",
      "revit_version": "2025.2",
      "dotnet_runtime": ".NET 8.0"
    }
  }
}
```

### 4. `revit.document.closed` — Revit Connector

Emitted when a document is closed.

```json
{
  "event_type": "revit.document.closed",
  "schema_version": "1.0.0",
  "payload": {
    "document_id": "uuid-v4",
    "title": "Project_A.rvt",
    "close_reason": "user_closed|save_and_close|crash|revit_exit",
    "was_modified": true,
    "last_view": {
      "view_id": "integer",
      "view_name": "Level 1 - Floor Plan"
    },
    "session_duration_seconds": 7200,
    "process": {
      "process_id": 8842,
      "session_id": "uuid-v4"
    }
  }
}
```

### 5. `revit.view.activated` — Revit Connector

Emitted when active view changes within a document.

```json
{
  "event_type": "revit.view.activated",
  "schema_version": "1.0.0",
  "payload": {
    "document_id": "uuid-v4",
    "previous_view": {
      "view_id": "integer",
      "view_name": "Level 1 - Floor Plan",
      "view_type": "FloorPlan"
    },
    "current_view": {
      "view_id": "integer",
      "view_name": "3D View",
      "view_type": "ThreeD"
    },
    "timestamp_utc": "2026-11-05T12:34:56.789Z"
  }
}
```

### 6. `revit.application.idling` — Revit Connector

Emitted on Revit Idling events (heartbeat).

```json
{
  "event_type": "revit.application.idling",
  "schema_version": "1.0.0",
  "payload": {
    "document_id": "uuid-v4|null",
    "active_view_id": "integer|null",
    "is_foreground": true,
    "process_id": 8842,
    "session_id": "uuid-v4"
  }
}
```

### 7. `adapter.correlated.activity` — Windows Adapter (Correlated Output)

Emitted by adapter after correlating AW + Revit signals. This is the event sent to Miru.

```json
{
  "event_type": "adapter.correlated.activity",
  "schema_version": "1.0.0",
  "payload": {
    "interval": {
      "start_utc": "2026-11-05T12:00:00.000Z",
      "end_utc": "2026-11-05T12:30:00.000Z",
      "duration_seconds": 1800
    },
    "attribution": {
      "project_id": "uuid-v4",
      "project_name": "Project Alpha",
      "model_identity": {
        "type": "workshared_central",
        "central_path": "\\\\server\\central\\Project_A_Central.rvt",
        "central_guid": "guid-string",
        "document_title": "Project_A.rvt"
      },
      "confidence": 0.92,
      "confidence_factors": {
        "revit_foreground": true,
        "document_match": true,
        "view_active": true,
        "afk_excluded": true,
        "single_revit_process": true
      }
    },
    "activity": {
      "observed_seconds": 1620,
      "active_seconds": 1500,
      "afk_seconds": 120,
      "idle_seconds": 180,
      "revit_foreground_seconds": 1450,
      "other_app_seconds": 170
    },
    "evidence": {
      "window_events_count": 45,
      "afk_events_count": 3,
      "revit_idling_events_count": 180,
      "source_event_ids": ["uuid1", "uuid2", "..."]
    }
  }
}
```

### 8. `adapter.ingestion.draft` — Windows Adapter (Miru Ingestion)

Final event submitted to Miru `POST /api/v1/agent/timesheet_entries`.

```json
{
  "event_type": "adapter.ingestion.draft",
  "schema_version": "1.0.0",
  "payload": {
    "timesheet_entry": {
      "external_run_id": "uuid-v4",
      "external_session_id": "uuid-v4",
      "duration_minutes": 25,
      "work_date": "2026-11-05",
      "project_id": "uuid-v4",
      "source": "automation",
      "note": "Correlated Revit activity: Project_A.rvt (Level 1, 3D View). Confidence: 0.92. Observed: 27min, Active: 25min, AFK excluded: 2min.",
      "proof_url": "https://bimspend.example.com/evidence/run-uuid",
      "source_metadata": {
        "correlation_confidence": 0.92,
        "observed_seconds": 1620,
        "active_seconds": 1500,
        "afk_seconds": 120,
        "evidence_event_ids": ["uuid1", "uuid2"],
        "model_identity": {
          "type": "workshared_central",
          "central_path": "\\\\server\\central\\Project_A_Central.rvt",
          "central_guid": "guid-string"
        },
        "attribution_factors": {
          "revit_foreground": true,
          "document_match": true,
          "view_active": true,
          "afk_excluded": true,
          "single_revit_process": true
        }
      },
      "proof_metadata": {
        "window_events": 45,
        "afk_events": 3,
        "revit_idling_events": 180,
        "correlation_algorithm": "v1.0",
        "privacy_filter_applied": true
      }
    },
    "agent": {
      "agent_key_id": "string",
      "company_id": "uuid-v4"
    }
  }
}
```

## Schema Registry

Schemas are stored as JSON Schema Draft 2020-12 files in `schemas/` directory:

- `schemas/envelope.schema.json` — Common envelope
- `schemas/window_focus_changed.schema.json`
- `schemas/afk_state_changed.schema.json`
- `schemas/revit_document_opened.schema.json`
- `schemas/revit_document_closed.schema.json`
- `schemas/revit_view_activated.schema.json`
- `schemas/revit_application_idling.schema.json`
- `schemas/adapter_correlated_activity.schema.json`
- `schemas/adapter_ingestion_draft.schema.json`

## Validation

All events MUST pass JSON Schema validation before:
- Writing to offline queue
- Transmitting to Miru
- Persisting to evidence store

Validation failures are logged with full event payload (sanitized) and event discarded.