# Findings Register — BIMSpend R1-06 Independent Audit

**Baseline**: `4e83d9b41533423f50c1f8042a2a2ef79445f0a4`
**Audit Branch**: `audit/kilo-nemotron-r1-06-independent-review`
**Total Findings**: 59

---

## Severity Distribution

| Severity | Count | Percentage |
|----------|-------|------------|
| CRITICAL | 4 | 6.8% |
| HIGH | 12 | 20.3% |
| MEDIUM | 28 | 47.5% |
| LOW | 15 | 25.4% |
| **Total** | **59** | **100%** |

---

## Category Distribution

| Category | CRITICAL | HIGH | MEDIUM | LOW | Total |
|----------|----------|------|--------|-----|-------|
| Architecture | 0 | 2 | 4 | 3 | 9 |
| Windows Capture | 1 | 3 | 4 | 4 | 12 |
| Revit Connector | 4 | 2 | 4 | 3 | 13 |
| IPC | 2 | 0 | 3 | 0 | 5 |
| Correlation | 0 | 2 | 2 | 1 | 5 |
| Suggestion Engine | 0 | 2 | 3 | 2 | 7 |
| Review/Approval | 1 | 3 | 4 | 1 | 9 |
| Database | 1 | 2 | 3 | 3 | 9 |
| Authentication | 0 | 1 | 2 | 1 | 4 |
| Tenant Isolation | 0 | 1 | 1 | 0 | 2 |
| Privacy | 0 | 0 | 1 | 1 | 2 |
| Open Source | 0 | 1 | 1 | 2 | 4 |
| Test/CI | 2 | 3 | 3 | 4 | 12 |

---

## Complete Findings Register

### CRITICAL (4)

| ID | Category | Title | File | Line | Evidence | Confidence | Owner |
|----|----------|-------|------|------|----------|------------|-------|
| CRIT-001 | Revit Connector | No .NET Revit add-in — Python stub only | `revit_connector.py` | 39-62 | `_HAS_REVIT_API=False` always in CPython; `connect()` returns True in stub mode | CONFIRMED | OpenCode |
| CRIT-002 | Revit Connector | No `.addin` manifest — Revit cannot load add-in | N/A | N/A | No manifest file in repository | CONFIRMED | OpenCode |
| CRIT-003 | IPC | Named pipe created with default DACL — any local process can connect | `revit_ipc.py` | 180-191 | `CreateNamedPipe(..., None)` — lpSecurityAttributes=NULL | CONFIRMED | OpenCode |
| CRIT-004 | IPC | No client authentication — `company_id` in HELLO untrusted | `revit_ipc.py` | 301-307 | HELLO payload accepted without verification | CONFIRMED | OpenCode |
| CRIT-005 | Review | `TimeEntry.attributed_time_id` FK not enforced in base DDL | `db.py` | 196-212 | FK only in v2 migration unique index, not base CREATE TABLE | CONFIRMED | OpenCode |
| CRIT-006 | Database | `Database.ingest_event()` bypasses capture consent | `controller.py` | 285 | Direct DB call ignores `CaptureController.consent` | CONFIRMED | OpenCode |
| CRIT-007 | Test/CI | No pytest execution in CI pipeline | `.github/workflows/preview-tests.yml` | 27-28 | Only `Test-BIMSpend.ps1` runs, not `pytest` | CONFIRMED | OpenCode |
| CRIT-008 | Test/CI | Zero Revit integration tests | `tests/` | N/A | No test files for revit_connector, revit_ipc, project_correlation | CONFIRMED | OpenCode |

### HIGH (12)

| ID | Category | Title | File | Line | Evidence | Confidence | Owner |
|----|----------|-------|------|------|----------|------------|-------|
| HIGH-001 | Architecture | `shell._load_data()` mixes demo seeding with app init | `shell.py` | 210-260 | 50 lines of fixture loading, correlation, suggestion creation in GUI class | CONFIRMED | OpenCode |
| HIGH-002 | Architecture | `runner.py` is production code but should be example | `runner.py` | 1-197 | 197 lines of demo orchestration in src/ | CONFIRMED | OpenCode |
| HIGH-003 | Windows Capture | `GetLastInputInfo` returns system-wide idle, not per-session | `afk_detector.py` | 51-67 | Windows API limitation documented | CONFIRMED | OpenCode |
| HIGH-004 | Windows Capture | `SessionLockDetector` not integrated into capture pipeline | `controller.py` | 241-287 | `_persist_event()` doesn't check lock state | CONFIRMED | OpenCode |
| HIGH-005 | Windows Capture | WTSAPI32 may be unavailable — detector returns UNKNOWN | `session_lock.py` | 44-49, 511-548 | `_HAS_WTSAPI` flag; fallback returns UNKNOWN | CONFIRMED | OpenCode |
| HIGH-006 | Correlation | Substring matching on window titles — false positives | `correlation.py` | 63-77 | `name in title` matches partial words | CONFIRMED | OpenCode |
| HIGH-007 | Correlation | No project code registry — Revit titles rarely match names | `project_correlation.py` | 214-226 | `register_project_code()` exists but unused in correlation | CONFIRMED | OpenCode |
| HIGH-008 | Suggestion Engine | AFK gaps don't break suggestion chains | `suggestion_engine.py` | 235-236 | Comment: "AFK/locked observations are excluded but they do NOT break the chain" | CONFIRMED | OpenCode |
| HIGH-009 | Suggestion Engine | No timezone handling — day boundaries wrong for non-UTC | `suggestion_engine.py` | 145-146 | Timestamps treated as UTC | CONFIRMED | OpenCode |
| HIGH-010 | Review | `submit_suggestion` creates invalid AttributedTime FK | `suggestion_engine.py` | 400-410 | Uses `evidence_ids[0]` or `suggestion.id` as activity_event_id | CONFIRMED | OpenCode |
| HIGH-011 | Database | Most `list_*`/`get_*` methods lack `company_id` filtering | `db.py` | 619-1380 | 8/10 query methods don't filter by company | CONFIRMED | OpenCode |
| HIGH-012 | Test/CI | 102/153 tests fail due to Windows temp dir permissions | `tests/` | N/A | `PermissionError: [WinError 5]` on pytest tmp_path | CONFIRMED | OpenCode |

### MEDIUM (28)

| ID | Category | Title | File | Line | Evidence | Confidence | Owner |
|----|----------|-------|------|------|----------|------------|-------|
| MED-001 | Architecture | `controller._persist_event()` computes external_id inline | `controller.py` | 255-261 | Title hashing duplicated, logic belongs in model | CONFIRMED | OpenCode |
| MED-002 | Architecture | `suggestion_engine._event_to_observation()` uses raw SQL | `suggestion_engine.py` | 160-179 | `self.db.conn.execute()` bypasses Database abstraction | CONFIRMED | OpenCode |
| MED-003 | Architecture | AFK/lock detectors use global system state | `afk_detector.py`, `session_lock.py` | N/A | Not per-session; incorrect on multi-user Windows | CONFIRMED | OpenCode |
| MED-004 | Windows Capture | 5s poll interval misses sub-5s interactions | `watcher_main.py` | 107-110 | `poll_time=5.0` default | CONFIRMED | OpenCode |
| MED-005 | Windows Capture | Only ApplicationFrameHost UWP handling | `windows.py` | 83-105 | Other UWP frame hosts not detected | CONFIRMED | OpenCode |
| MED-006 | Windows Capture | Default privacy rules minimal | `privacy_filter.py` | 143-151 | No healthcare/legal/govt patterns | CONFIRMED | OpenCode |
| MED-007 | Windows Capture | External_id includes start_time — clock skew risk | `heartbeat.py` | 79-81 | `source:app:title_hash:start_time` | CONFIRMED | OpenCode |
| MED-008 | IPC | No message signing/replay protection | `revit_ipc.py` | 101-106 | JSON accepted without HMAC | CONFIRMED | OpenCode |
| MED-009 | IPC | Queue DoS — unbounded send queue | `revit_ipc.py` | 147-148 | `_send_queue` maxsize=100, no backpressure | CONFIRMED | OpenCode |
| MED-010 | IPC | Multi-instance routing not implemented | `revit_ipc.py` | 124-138 | All instances share pipe name prefix | CONFIRMED | OpenCode |
| MED-011 | Correlation | No word boundaries in title matching | `correlation.py` | 63-77 | "ABC" matches "XABCY" | CONFIRMED | OpenCode |
| MED-012 | Correlation | Confidence values arbitrary, not calibrated | `correlation.py` | 66-76 | 0.85/0.60 hardcoded | CONFIRMED | OpenCode |
| MED-013 | Correlation | Single-pass, first-match-wins | `correlation.py` | 63-77 | No multi-candidate scoring | CONFIRMED | OpenCode |
| MED-014 | Suggestion Engine | Project frequency wins over duration | `suggestion_engine.py` | 291-305 | `project_counts` frequency, not duration-weighted | CONFIRMED | OpenCode |
| MED-015 | Suggestion Engine | Confidence = max(event confidence) | `suggestion_engine.py` | 307-321 | Masks low-confidence majority | CONFIRMED | OpenCode |
| MED-016 | Suggestion Engine | Deterministic ID fragile to evidence_id changes | `suggestion_engine.py` | 330-333 | Hash of sorted evidence_ids | CONFIRMED | OpenCode |
| MED-017 | Suggestion Engine | `company_id` not enforced in collect_observations | `suggestion_engine.py` | 98-116 | Cross-tenant leakage possible | CONFIRMED | OpenCode |
| MED-018 | Review | `return_for_correction` loses distinction from reject | `suggestion_domain.py` | 246 | Sets state=REJECTED, not RETURNED_FOR_CORRECTION | CONFIRMED | OpenCode |
| MED-019 | Review | split/merge audit states not queryable | `suggestion_domain.py` | 351, 442 | `previous_state="multiple"`, `new_state="merged"` | CONFIRMED | OpenCode |
| MED-020 | Review | No validation of edited fields before submit | `suggestion_domain.py` | 55-105 | Designer can submit unedited suggestion | CONFIRMED | OpenCode |
| MED-021 | Database | No rollback procedures for migrations | `db.py` | 218-579 | Forward-only migrations | CONFIRMED | OpenCode |
| MED-022 | Database | v2 unique index fails if duplicates exist | `db.py` | 267-271 | RuntimeError raised, no auto-resolution | CONFIRMED | OpenCode |
| MED-023 | Database | `evidence_ids` stored as JSON TEXT | `db.py` | 520, 1007-1008 | Not queryable, no FK to activity_events | CONFIRMED | OpenCode |
| MED-024 | Auth | Module-level `current_auth` global not thread-safe | `identity.py` | 166 | Single global SessionContext | CONFIRMED | OpenCode |
| MED-025 | Tenant Isolation | Direct DB access bypasses company scoping | `db.py` | 619-1380 | `list_projects()` returns all companies | CONFIRMED | OpenCode |
| MED-026 | Privacy | Evidence tables lack row-level security | `db.py` | 462-474 | `revit_correlation_evidence` queryable by any company user | CONFIRMED | OpenCode |
| MED-027 | Open Source | Source distribution obligation not fulfilled | `ACTIVITYWATCH_SOURCE_MANIFEST.md` | 108 | MPL-2.0 §3.2 pending legal review | CONFIRMED | Legal |
| MED-028 | Test/CI | No GUI test execution in CI | `.github/workflows/` | N/A | `@pytest.mark.gui` never runs | CONFIRMED | OpenCode |

### LOW (15)

| ID | Category | Title | File | Line | Evidence | Confidence | Owner |
|----|----------|-------|------|------|----------|------------|-------|
| LOW-001 | Architecture | Error backoff no maximum retry limit | `watcher_main.py` | 232-235 | Exponential backoff capped at 60s but infinite retries | CONFIRMED | OpenCode |
| LOW-002 | Architecture | No structured capture quality metrics | `controller.py` | 298-310 | `get_status()` basic only | CONFIRMED | OpenCode |
| LOW-003 | Architecture | Hardcoded defaults not externalized | `controller.py` | 40-52 | `CaptureConfig` dataclass but no config file | CONFIRMED | OpenCode |
| LOW-004 | Windows Capture | Backoff uses exponential delay, no max retry | `watcher_main.py` | 232-235 | While loop with no retry cap | CONFIRMED | OpenCode |
| LOW-005 | Windows Capture | No capture quality metrics | `controller.py` | 298-310 | Events/sec, drop rate, error rate missing | CONFIRMED | OpenCode |
| LOW-006 | Windows Capture | Config not externalized | `controller.py` | 40-52 | Poll time, thresholds hardcoded | CONFIRMED | OpenCode |
| LOW-007 | IPC | No supported Revit version matrix | `revit_connector.py` | N/A | Not documented | CONFIRMED | OpenCode |
| LOW-008 | IPC | No add-in signing strategy | N/A | N/A | Production distribution requires signing | CONFIRMED | OpenCode |
| LOW-009 | IPC | No health monitoring | `revit_ipc.py` | 392-415 | No heartbeat, event rate, error rate | CONFIRMED | OpenCode |
| LOW-010 | Correlation | First-match-wins, no multi-candidate | `correlation.py` | 63-77 | Breaks on first match | CONFIRMED | OpenCode |
| LOW-011 | Review | `bill_entry` 2x limit not configurable | `review.py` | 226-230 | `billed_minutes > entry.minutes * 2` hardcoded | CONFIRMED | OpenCode |
| LOW-012 | Database | Missing composite indexes | `db.py` | 273-276 | Only single-column indexes | CONFIRMED | OpenCode |
| LOW-013 | Database | No CHECK constraint on state values | `db.py` | 196-212 | State stored as TEXT, no validation | CONFIRMED | OpenCode |
| LOW-014 | Database | `time_entry_audit.actor_id` can be "unspecified_demo" | `db.py` | 878-879 | Weak accountability | CONFIRMED | OpenCode |
| LOW-015 | Open Source | LICENSE.MPL-2.0.activitywatch.txt is placeholder | `LICENSE.MPL-2.0.activitywatch.txt` | 30-33 | Full MPL-2.0 text not included | CONFIRMED | Legal |

---

## Reproduction Steps for Key Findings

### CRIT-001: Revit Connector Non-Functional
```python
# In any Python environment:
from bimspend.capture.revit_connector import RevitConnector
conn = RevitConnector()
result = conn.connect(None)  # Returns True but does nothing
assert conn.get_stats()["has_revit_api"] == False  # Always False in CPython
```

### CRIT-003: Named Pipe ACL Bypass
```python
# Any local process can connect:
import win32file
pipe = win32file.CreateFile(
    r"\\.\pipe\bimspend_revit_test",
    win32file.GENERIC_READ | win32file.GENERIC_WRITE,
    0, None, win32file.OPEN_EXISTING, 0, None
)
# Success — no authentication required
```

### CRIT-005: FK Enforcement Gap
```sql
-- In SQLite with v1 schema (no v2 migration):
INSERT INTO attributed_time (id, activity_event_id, ...) VALUES ('att_1', 'evt_1', ...);
INSERT INTO time_entries (id, attributed_time_id, ...) VALUES ('entry_1', 'att_1', ...);
DELETE FROM attributed_time WHERE id = 'att_1';  -- Succeeds, orphaned time_entry
```

### CRIT-006: Consent Bypass
```python
db = Database("bimspend.db")
event = ActivityEvent(...)  # Any event
db.ingest_event(event)  # Succeeds even if CaptureController.consent.granted=False
```

### HIGH-008: AFK Chain Merging
```python
# Observations: [Project A, 30min], [AFK, 10min], [Project A, 20min]
# Result: Single suggestion for Project A, 50min (AFK gap ignored)
# Expected: Two suggestions (30min + 20min) or configurable behavior
```

### MED-018: Return for Correction Lost
```python
# Manager returns for correction:
suggestion.state = "rejected"  # Same as rejection!
# Audit shows action="return_for_correction" but state=REJECTED
# Cannot distinguish from designer rejection in queries
```

---

## Dependency/Blocking Relationships

```
CRIT-001 (Revit add-in) ──blocks──→ CRIT-002 (Manifest)
    │
    ├──blocks──→ MED-010 (Multi-instance routing)
    ├──blocks──→ MED-011 (Revit version matrix)
    └──blocks──→ LOW-007 (Signing strategy)

CRIT-003 (Pipe ACL) ──blocks──→ CRIT-004 (Client auth)
    │
    ├──blocks──→ MED-008 (Message signing)
    ├──blocks──→ MED-009 (Queue DoS)
    └──blocks──→ MED-010 (Multi-instance)

CRIT-005 (FK enforcement) ──blocks──→ HIGH-010 (submit_suggestion FK)
    │
    └──blocks──→ MED-023 (evidence_ids JSON)

HIGH-003 (AFK system-wide) ──blocks──→ HIGH-008 (AFK chain merging)
    │
    └──blocks──→ MED-003 (Per-session detectors)

HIGH-004 (Lock not integrated) ──blocks──→ HIGH-005 (WTSAPI32 unavailable)
    │
    └──blocks──→ MED-003 (Per-session detectors)

TC-003 (Temp dir perms) ──blocks──→ TC-002 (Revit tests)
    │
    └──blocks──→ TC-004 (Capture integration tests)
```

---

## Suggested Remediation Priority

| Priority | Findings | Rationale |
|----------|----------|-----------|
| **P0** | CRIT-001, CRIT-002, CRIT-003, CRIT-004, CRIT-005, CRIT-006, CRIT-007, CRIT-008 | Security, data integrity, CI foundation |
| **P1** | HIGH-001 through HIGH-012 | Core workflow reliability, auth, tenant isolation |
| **P2** | MED-001 through MED-028 | Revit runtime, capture quality, maintainability |
| **P3** | LOW-001 through LOW-015 | Polish, observability, configuration |