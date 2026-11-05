# BIMSpend Integration Contracts — Project & Model Identity Rules

Version: 1.0.0
Status: Draft — Implementation Checkpoint 1
Branch: `build/claude-integration-contracts`

## Identity Hierarchy

BIMSpend uses a hierarchical identity strategy to map Revit documents to commercial projects. The adapter resolves identity in priority order:

```
1. Explicit Admin Mapping (Highest Confidence)
   └── BIMSpend Project ID ↔ Approved Model Identity
   
2. ACC/Cloud Identifiers (When Available)
   └── ACC Project ID + ACC Model ID (stable, cloud-native)
   
3. Workshared Central Identity
   └── Normalized Central Path + Central GUID
   
4. Standalone File Identity
   └── Normalized Path + File Hash (SHA-256)
   
5. Unsaved/New Document (Lowest Confidence)
   └── Temporary Session Identity — Never Auto-Post Approved Time
```

## Identity Resolution Rules

### Rule 1: Explicit Admin Mapping Takes Precedence

If an admin has configured a mapping in BIMSpend, it overrides all other resolution methods.

```json
{
  "mapping_id": "uuid-v4",
  "project_id": "uuid-v4",
  "project_name": "Project Alpha",
  "model_identity": {
    "type": "workshared_central",
    "central_path": "\\\\server\\central\\Project_A_Central.rvt",
    "central_guid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  },
  "created_by": "admin@company.com",
  "created_utc": "2026-11-01T00:00:00Z",
  "is_active": true
}
```

### Rule 2: ACC Cloud Identity (When Available)

For Autodesk Construction Cloud / BIM 360 models, use stable cloud identifiers:

```json
{
  "type": "acc_cloud_model",
  "acc_project_id": "b.12345678-abcd-ef01-2345-6789abcdef01",
  "acc_model_id": "urn:adsk.wipprod:fs.file:vf.xyz...",
  "document_title": "Project_A.rvt"
}
```

### Rule 3: Workshared Central Identity

For workshared (central) models, use normalized central path + GUID:

```json
{
  "type": "workshared_central",
  "central_path": "\\\\server\\central\\Project_A_Central.rvt",
  "central_guid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "document_title": "Project_A.rvt"
}
```

**Normalization Rules:**
- UNC paths: normalize case, resolve `\\server\share\..\path` to canonical form
- Drive letters: convert to UNC where possible, otherwise normalize case
- Central GUID: from `BasicFileInfo.CentralGUID` (Revit API)

### Rule 4: Standalone File Identity

For non-workshared (standalone) files:

```json
{
  "type": "standalone_file",
  "file_path": "C:\\Projects\\Project_A\\Project_A.rvt",
  "file_hash": "sha256:abcdef1234567890...",
  "file_size_bytes": 52428800,
  "document_title": "Project_A.rvt"
}
```

**Normalization Rules:**
- Resolve absolute path, normalize case
- Compute SHA-256 hash of file content (first 64KB + last 64KB + size for large files)
- On `Save As` / rename: treat as new identity → trigger remapping event

### Rule 5: Unsaved / New Documents

For documents never saved or detached:

```json
{
  "type": "unsaved",
  "session_document_id": "uuid-v4",
  "document_title": "Untitled.rvt"
}
```

**Policy:** Never automatically post approved/billed time for unsaved documents. Require explicit admin mapping before any time can be approved.

## Identity Change Events

### Remapping Event

Emitted when identity resolution changes (Save As, detach, central path change, admin remap):

```json
{
  "event_type": "identity.remapped",
  "schema_version": "1.0.0",
  "payload": {
    "previous_identity": { /* previous model_identity object */ },
    "new_identity": { /* new model_identity object */ },
    "trigger": "save_as|detach|central_move|admin_remap|acc_sync",
    "timestamp_utc": "2026-11-05T12:34:56.789Z",
    "requires_review": true
  }
}
```

### Confidence Scoring

Confidence factors (all boolean, combined for 0.0–1.0 score):

| Factor | Weight | Description |
|--------|--------|-------------|
| `revit_foreground` | 0.25 | Revit process is foreground window |
| `document_match` | 0.25 | Active document matches mapped identity |
| `view_active` | 0.15 | Active view is a working view (not sheet, schedule) |
| `afk_excluded` | 0.20 | AFK state is not_afk |
| `single_revit_process` | 0.15 | Only one Revit process running |

**Thresholds:**
- `≥ 0.80`: High confidence → auto-submit draft
- `0.50–0.79`: Medium confidence → submit draft, flag for review
- `< 0.50`: Low confidence → queue locally, do not submit

## Multi-Process / Multi-Document Handling

### Process Isolation

Each Revit process gets a distinct `process_id` and `session_id`. The adapter tracks per-process state independently.

### Document Switching Within Process

When active document changes within a process:
1. Close previous document session (emit `revit.document.closed`)
2. Open new document session (emit `revit.document.opened`)
3. Time allocation: split at exact view activation timestamp

### Multiple Simultaneous Revit Processes

Only the **foreground** Revit process can accumulate high-confidence time.

Background Revit processes:
- Track separately with `is_foreground: false`
- Accumulate `revit_foreground_seconds = 0`
- Do not contribute to high-confidence attribution
- May contribute to low-confidence "Revit open but not focused" metric

### Multiple Documents in One Process

Revit allows multiple open documents per process. Only the **active view's document** receives attribution at any moment.

Time allocation:
- On `revit.view.activated`: end previous document interval, start new
- Precision: timestamp of view activation event
- Idle/AFK time allocated to currently active document

## Implementation Checklist

- [ ] Admin mapping CRUD API in BIMSpend
- [ ] Identity resolver with priority hierarchy
- [ ] Normalization functions for paths, GUIDs, ACC IDs
- [ ] File hashing utility (streaming, large file support)
- [ ] Remapping event emission
- [ ] Confidence calculator with configurable weights
- [ ] Multi-process tracker with foreground detection
- [ ] Per-process, per-document time allocator
- [ ] Unit tests for all identity scenarios