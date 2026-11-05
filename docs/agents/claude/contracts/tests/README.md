# BIMSpend Integration Contracts — Contract Validation Tests & Synthetic Fixtures

Version: 1.0.0
Status: Draft — Implementation Checkpoint 1
Branch: `build/claude-integration-contracts`

## Test Strategy

- **Schema Validation**: Every event type validates against JSON Schema
- **Contract Tests**: Verify transformation rules (observed→attributed→approved→billed)
- **Integration Fixtures**: Synthetic end-to-end scenarios
- **Property Tests**: Idempotency, ordering, deduplication invariants

## Synthetic Fixtures

### Fixture 1: Standard Revit Session

```json
{
  "name": "standard_revit_session",
  "description": "3-hour Revit session with one AFK break, single document",
  "events": [
    {
      "event_type": "revit.document.opened",
      "timestamp_utc": "2026-11-05T09:00:00.000Z",
      "payload": {
        "document": {
          "document_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
          "title": "Project_A.rvt",
          "path": "\\\\server\\central\\Project_A_Central.rvt",
          "is_workshared": true,
          "central_path": "\\\\server\\central\\Project_A_Central.rvt",
          "central_guid": "11111111-2222-3333-4444-555555555555",
          "version_number": 15,
          "last_saved_by": "designer@company.com",
          "last_saved_utc": "2026-11-04T17:00:00Z",
          "is_detached": false,
          "is_new": false
        },
        "view": { "view_id": 1001, "view_name": "Level 1 - Floor Plan", "view_type": "FloorPlan" },
        "process": { "process_id": 8842, "session_id": "bbbbbbbb-cccc-dddd-eeee-ffffffffffff", "revit_version": "2025.2", "dotnet_runtime": ".NET 8.0" }
      }
    },
    {
      "event_type": "window.focus.changed",
      "timestamp_utc": "2026-11-05T09:00:01.000Z",
      "payload": {
        "previous": { "app_name": "explorer.exe", "window_title": "File Explorer", "process_id": 1234, "exe_path": "C:\\Windows\\explorer.exe" },
        "current": { "app_name": "Revit.exe", "window_title": "Project_A.rvt - Autodesk Revit 2025", "process_id": 8842, "exe_path": "C:\\Program Files\\Autodesk\\Revit 2025\\Revit.exe" },
        "transition_type": "app_switch",
        "idle_state": "active",
        "monitor_info": { "monitor_count": 2, "primary_monitor": 0 }
      }
    },
    {
      "event_type": "revit.application.idling",
      "timestamp_utc": "2026-11-05T09:00:05.000Z",
      "payload": { "document_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "active_view_id": 1001, "is_foreground": true, "process_id": 8842, "session_id": "bbbbbbbb-cccc-dddd-eeee-ffffffffffff" }
    },
    {
      "event_type": "afk.state.changed",
      "timestamp_utc": "2026-11-05T10:30:00.000Z",
      "payload": { "state": "afk", "idle_duration_seconds": 300, "trigger": "timeout", "previous_state": "not_afk" }
    },
    {
      "event_type": "afk.state.changed",
      "timestamp_utc": "2026-11-05T10:45:00.000Z",
      "payload": { "state": "not_afk", "idle_duration_seconds": 0, "trigger": "mouse", "previous_state": "afk" }
    },
    {
      "event_type": "revit.view.activated",
      "timestamp_utc": "2026-11-05T11:00:00.000Z",
      "payload": {
        "document_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "previous_view": { "view_id": 1001, "view_name": "Level 1 - Floor Plan", "view_type": "FloorPlan" },
        "current_view": { "view_id": 1002, "view_name": "3D View", "view_type": "ThreeD" }
      }
    },
    {
      "event_type": "revit.document.closed",
      "timestamp_utc": "2026-11-05T12:00:00.000Z",
      "payload": {
        "document_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "title": "Project_A.rvt",
        "close_reason": "save_and_close",
        "was_modified": true,
        "last_view": { "view_id": 1002, "view_name": "3D View" },
        "session_duration_seconds": 10800,
        "process": { "process_id": 8842, "session_id": "bbbbbbbb-cccc-dddd-eeee-ffffffffffff" }
      }
    }
  ],
  "expected_correlated": {
    "interval": { "start_utc": "2026-11-05T09:00:00.000Z", "end_utc": "2026-11-05T12:00:00.000Z", "duration_seconds": 10800 },
    "attribution": {
      "project_id": "project-uuid-1",
      "project_name": "Project Alpha",
      "model_identity": { "type": "workshared_central", "central_path": "\\\\server\\central\\Project_A_Central.rvt", "central_guid": "11111111-2222-3333-4444-555555555555", "document_title": "Project_A.rvt" },
      "confidence": 0.95,
      "confidence_factors": { "revit_foreground": true, "document_match": true, "view_active": true, "afk_excluded": true, "single_revit_process": true }
    },
    "activity": {
      "observed_seconds": 10800,
      "active_seconds": 9900,
      "afk_seconds": 900,
      "idle_seconds": 0,
      "revit_foreground_seconds": 9900,
      "other_app_seconds": 0
    },
    "evidence": { "window_events_count": 2, "afk_events_count": 2, "revit_idling_events_count": 360, "source_event_ids": [...] }
  },
  "expected_ingestion": {
    "duration_minutes": 165,
    "work_date": "2026-11-05",
    "confidence": 0.95,
    "note_contains": ["Project_A.rvt", "Level 1", "3D View", "AFK excluded: 15min"]
  }
}
```

### Fixture 2: Multi-Document Session

```json
{
  "name": "multi_document_session",
  "description": "Two Revit documents in same process, view switches",
  "events": [
    {
      "event_type": "revit.document.opened",
      "timestamp_utc": "2026-11-05T09:00:00.000Z",
      "payload": { "document": { "document_id": "doc-1", "title": "Project_A.rvt", "is_workshared": true, "central_guid": "guid-1" }, "view": { "view_id": 1, "view_name": "Level 1" }, "process": { "process_id": 8842, "session_id": "sess-1" } }
    },
    {
      "event_type": "revit.document.opened",
      "timestamp_utc": "2026-11-05T10:00:00.000Z",
      "payload": { "document": { "document_id": "doc-2", "title": "Project_B.rvt", "is_workshared": true, "central_guid": "guid-2" }, "view": { "view_id": 1, "view_name": "Level 1" }, "process": { "process_id": 8842, "session_id": "sess-1" } }
    },
    {
      "event_type": "revit.view.activated",
      "timestamp_utc": "2026-11-05T10:00:01.000Z",
      "payload": { "document_id": "doc-2", "previous_view": { "view_id": 1, "view_name": "Level 1" }, "current_view": { "view_id": 2, "view_name": "Level 2" } }
    },
    {
      "event_type": "revit.document.closed",
      "timestamp_utc": "2026-11-05T11:00:00.000Z",
      "payload": { "document_id": "doc-1", "close_reason": "user_closed", "session_duration_seconds": 7200 }
    },
    {
      "event_type": "revit.document.closed",
      "timestamp_utc": "2026-11-05T12:00:00.000Z",
      "payload": { "document_id": "doc-2", "close_reason": "save_and_close", "session_duration_seconds": 7200 }
    }
  ],
  "expected_correlated": [
    {
      "interval": { "start_utc": "2026-11-05T09:00:00.000Z", "end_utc": "2026-11-05T10:00:00.000Z", "duration_seconds": 3600 },
      "attribution": { "project_id": "project-a", "model_identity": { "central_guid": "guid-1" }, "confidence": 0.90 }
    },
    {
      "interval": { "start_utc": "2026-11-05T10:00:00.000Z", "end_utc": "2026-11-05T11:00:00.000Z", "duration_seconds": 3600 },
      "attribution": { "project_id": "project-b", "model_identity": { "central_guid": "guid-2" }, "confidence": 0.90 }
    },
    {
      "interval": { "start_utc": "2026-11-05T11:00:00.000Z", "end_utc": "2026-11-05T12:00:00.000Z", "duration_seconds": 3600 },
      "attribution": { "project_id": "project-b", "model_identity": { "central_guid": "guid-2" }, "confidence": 0.90 }
    }
  ]
}
```

### Fixture 3: Dual Revit Processes

```json
{
  "name": "dual_revit_processes",
  "description": "Two Revit processes running simultaneously, only foreground gets attribution",
  "events": [
    {
      "event_type": "revit.document.opened",
      "timestamp_utc": "2026-11-05T09:00:00.000Z",
      "payload": { "document": { "document_id": "doc-fg", "title": "Project_A.rvt" }, "process": { "process_id": 8842, "session_id": "sess-fg" } }
    },
    {
      "event_type": "revit.document.opened",
      "timestamp_utc": "2026-11-05T09:00:00.000Z",
      "payload": { "document": { "document_id": "doc-bg", "title": "Project_B.rvt" }, "process": { "process_id": 9953, "session_id": "sess-bg" } }
    },
    {
      "event_type": "window.focus.changed",
      "timestamp_utc": "2026-11-05T09:00:00.000Z",
      "payload": { "current": { "app_name": "Revit.exe", "process_id": 8842 }, "transition_type": "foreground_gained" }
    },
    {
      "event_type": "window.focus.changed",
      "timestamp_utc": "2026-11-05T10:00:00.000Z",
      "payload": { "current": { "app_name": "Revit.exe", "process_id": 9953 }, "transition_type": "app_switch" }
    },
    {
      "event_type": "window.focus.changed",
      "timestamp_utc": "2026-11-05T11:00:00.000Z",
      "payload": { "current": { "app_name": "Revit.exe", "process_id": 8842 }, "transition_type": "app_switch" }
    }
  ],
  "expected_correlated": [
    { "interval": { "start_utc": "2026-11-05T09:00:00", "end_utc": "2026-11-05T10:00:00" }, "attribution": { "project_id": "project-a", "confidence": 0.95, "confidence_factors": { "single_revit_process": false } } },
    { "interval": { "start_utc": "2026-11-05T10:00:00", "end_utc": "2026-11-05T11:00:00" }, "attribution": { "project_id": "project-b", "confidence": 0.85, "confidence_factors": { "single_revit_process": false, "revit_foreground": true } } },
    { "interval": { "start_utc": "2026-11-05T11:00:00", "end_utc": "2026-11-05T12:00:00" }, "attribution": { "project_id": "project-a", "confidence": 0.95 } }
  ],
  "notes": "Background process time attributed at lower confidence, flagged for review"
}
```

### Fixture 4: Save As / Remapping

```json
{
  "name": "save_as_remapping",
  "description": "Document saved as new file — triggers identity remapping",
  "events": [
    {
      "event_type": "revit.document.opened",
      "timestamp_utc": "2026-11-05T09:00:00.000Z",
      "payload": { "document": { "document_id": "doc-orig", "title": "Project_A.rvt", "central_guid": "guid-1" } }
    },
    {
      "event_type": "revit.document.closed",
      "timestamp_utc": "2026-11-05T10:00:00.000Z",
      "payload": { "document_id": "doc-orig", "close_reason": "save_as", "was_modified": true }
    },
    {
      "event_type": "revit.document.opened",
      "timestamp_utc": "2026-11-05T10:00:01.000Z",
      "payload": { "document": { "document_id": "doc-new", "title": "Project_A_v2.rvt", "central_guid": "guid-2" } }
    }
  ],
  "expected_remap_event": {
    "event_type": "identity.remapped",
    "trigger": "save_as",
    "previous_identity": { "type": "workshared_central", "central_guid": "guid-1" },
    "new_identity": { "type": "workshared_central", "central_guid": "guid-2" },
    "requires_review": true
  }
}
```

## Validation Test Suite

### Schema Validation

```python
import jsonschema

def test_all_events_validate():
    for schema_file in SCHEMA_FILES:
        schema = load_json(schema_file)
        for fixture in load_fixtures():
            for event in fixture["events"]:
                if event["event_type"] == schema_type(schema):
                    jsonschema.validate(event, schema)
```

### Contract Tests

```python
def test_observed_to_attributed_transformation():
    """Observed seconds → attributed minutes with AFK/idle exclusion, confidence weighting."""
    fixture = load_fixture("standard_revit_session")
    correlated = correlate(fixture["events"])
    expected = fixture["expected_correlated"]
    
    # AFK excluded
    assert correlated["activity"]["afk_seconds"] == 900
    assert correlated["activity"]["active_seconds"] == 9900
    
    # Confidence applied
    attributed_min = round(correlated["activity"]["active_seconds"] / 60 * correlated["attribution"]["confidence"])
    assert attributed_min == 165  # 9900/60 * 0.95 = 156.75 → 165 rounded

def test_attributed_preserves_metadata_on_approval():
    """Approval must not strip source_metadata."""
    draft = create_draft(confidence=0.92, observed_seconds=1620)
    approved = approve(draft, approved_by="manager-uuid")
    
    assert approved["source_metadata"]["correlation_confidence"] == 0.92
    assert approved["source_metadata"]["observed_seconds"] == 1620
    assert approved["proof_metadata"]["correlation_algorithm"] == "v1.0"

def test_billed_cannot_exceed_approved():
    """Invoice line item quantity validated against approved entries."""
    approved_entries = [create_approved(duration_minutes=600)]  # 10 hours
    invoice = create_invoice_line_item(quantity_hours=11.0, linked_entries=approved_entries)
    
    assert not invoice.is_valid()
    assert "billed_hours_exceed_approved" in invoice.errors

def test_idempotent_submission():
    """Same external_run_id submitted twice → second returns 409, no duplicate."""
    entry = create_queue_entry(external_run_id="run-123")
    result1 = submit(entry)
    result2 = submit(entry)
    
    assert result1.status == 201
    assert result2.status == 409
    assert count_timesheet_entries(external_run_id="run-123") == 1

def test_offline_queue_replay():
    """Restart with unacked entries → replay → exactly once."""
    entry = create_queue_entry(status="submitting")  # Crashed mid-submit
    restart_adapter()
    result = drain_queue()
    
    assert result.acked == 1
    assert count_timesheet_entries(entry.external_run_id) == 1
```

### Property Tests (Hypothesis/QuickCheck Style)

```python
@given(st.integers(min_value=0, max_value=86400))
def test_attribution_monotonic(observed_seconds):
    """Attributed time never exceeds observed time."""
    attributed = calculate_attributed(observed_seconds, confidence=1.0)
    assert attributed <= observed_seconds / 60

@given(st.floats(min_value=0.0, max_value=1.0))
def test_confidence_bounds(confidence):
    """Attributed time monotonic in confidence."""
    base = calculate_attributed(3600, confidence=0.5)
    higher = calculate_attributed(3600, confidence=confidence)
    if confidence > 0.5:
        assert higher >= base

@given(st.lists(st.uuids(), min_size=1, max_size=100))
def test_deduplication_idempotent(event_ids):
    """Deduplicating twice = deduplicating once."""
    once = deduplicate(event_ids)
    twice = deduplicate(deduplicate(event_ids))
    assert once == twice
```

## Test Execution

```bash
# Schema validation
pytest tests/test_schemas.py -v

# Contract tests
pytest tests/test_contracts.py -v

# Property tests
pytest tests/test_properties.py -v --hypothesis-show-statistics

# Integration fixtures
pytest tests/test_fixtures.py -v

# All
pytest tests/ -v --cov=contracts --cov-report=term-missing
```

## CI Integration

```yaml
# .github/workflows/contract-tests.yml
name: Contract Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -r requirements-test.txt
      - run: pytest tests/ -v --junitxml=results.xml
      - uses: actions/upload-artifact@v4
        if: always()
        with: { name: test-results, path: results.xml }
```