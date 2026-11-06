# R1 Native Capture — Implementation Checkpoint

- Branch: `build/bimspend-r1-06-review-approval-ui` (created from `build/bimspend-r1-05-timesheet-suggestions` at `556b7b8291896175ec92602b52e6b0ce8901ab76`)
- Base main: `65e344b340967108e35e54721d76ec223f8769e0`
- Status: R1-01/R1-02/R1-03 complete, R1-04 complete, R1-05 complete, R1-06 complete. All 146 domain tests pass.
- Schema version: v9 (suggestion_decisions audit table).

## R1-01 — ActivityWatch Source Provenance

- Upstream: ActivityWatch bundle `9fee4702fea08dbe0149cc6e28f4ef66b49f54ec` (MPL-2.0)
- Upstream: aw-watcher-window `12000f58d16b8fc1376af42755c688b3d7157280` (MPL-2.0)
- Manifest: `docs/open-source/ACTIVITYWATCH_SOURCE_MANIFEST.md`
- License: `docs/open-source/LICENSE.MPL-2.0.activitywatch.txt`
- Adapted files (MPL-2.0, in `src/bimspend/capture/activitywatch_derived/`):
  - `windows.py` ← `aw_watcher_window/windows.py` — Win32 API window capture primitives
  - `privacy_filter.py` ← `aw_watcher_window/privacy_filter.py` — drop/redact privacy rules
  - `watcher_main.py` ← `aw_watcher_window/main.py` — polling heartbeat loop, pulsetime, error backoff

## R1-02 — Native Windows Foreground Capture

- `src/bimspend/capture/activitywatch_derived/windows.py` — Win32 API window capture
- `src/bimspend/capture/controller.py` — CaptureController with lifecycle states
- Capture disabled by default; explicit consent required
- Fail-closed session validation
- Company-scoped events
- Privacy filtering before persistence
- No automatic billing

## R1-03 — AFK Detection, Session Lock, Heartbeat

- `src/bimspend/capture/afk_detector.py` — AFKDetector (GetLastInputInfo API)
- `src/bimspend/capture/session_lock.py` — SessionLockDetector with WTSRegisterSessionNotification
  - Event-driven lock/unlock detection via WM_WTSSESSION_CHANGE
  - Fallback to WTSQuerySessionInformation polling
  - Graceful degradation on non-Windows/missing WTSAPI32
- `src/bimspend/capture/heartbeat.py` — HeartbeatManager with idempotent events
- State model: ACTIVE → AFK → LOCKED → ACTIVE → PAUSED → STOPPED

## R1-04 — Native Revit Activity Detection & Project Correlation

- `src/bimspend/capture/revit_connector.py` — Read-only Revit API event observer
  - DocumentOpened, DocumentClosing, DocumentClosed, DocumentChanged, ViewActivated
  - Multiple Revit instance support (per-process session GUID)
  - No model geometry access, no Revit transactions
  - Graceful degradation when Revit API unavailable
- `src/bimspend/capture/revit_ipc.py` — Windows named pipe IPC (local-only)
- `src/bimspend/capture/project_correlation.py` — 5-strategy correlation engine
  - Strategies: explicit, stable_id, project_code, historical, unassigned
  - Confidence: CONFIRMED, HIGH, MEDIUM, LOW, UNASSIGNED
  - Company-scoped tenancy isolation
- Database v7 migration: 4 new tables + 9 indexes

## R1-06 — Designer Review and Manager Approval UI

- `src/bimspend/capture/suggestion_domain.py` — SuggestionService domain service
  - submit_suggestion: pending_review → submitted (designer-owned, company-scoped)
  - approve_suggestion: submitted → approved (manager-only, no billing)
  - reject_suggestion: pending_review → rejected (designer), submitted → rejected (manager)
  - return_for_correction: submitted → rejected (manager)
  - split_suggestion: split pending suggestion into two
  - merge_suggestions: combine multiple pending suggestions into one
  - get_suggestion_audit_trail: audit history for a suggestion
  - All actions require authenticated session-validated actor with company scope
- `src/bimspend/app/screens/designer_review.py` — DesignerReviewScreen
  - Table view: project, start, end, minutes, confidence, source, state
  - Filters: project
  - Actions: edit, submit, reject, split, merge
  - Edit dialog: project ID, minutes, review notes
- `src/bimspend/app/screens/manager_approval.py` — ManagerApprovalScreen
  - Table view: entry ID, project, user, start, end, minutes, confidence, state
  - Filters: project
  - Actions: approve, reject, return for correction, bulk approve, bulk reject
- `src/bimspend/app/shell.py` — Navigation entries for designer_review and manager_approval
- `src/bimspend/db.py` — v9 migration: suggestion_decisions table + 3 indexes
  - Fixed upsert_suggestion to use DO UPDATE instead of DO NOTHING
- Tests: `tests/capture/test_suggestion_domain.py` — 7 tests (auth, RBAC, company scope, audit trail)
- 146 domain tests pass

## CI

- `.github/workflows/preview-tests.yml` — includes `build/bimspend-r1-06-review-approval-ui`

## Remaining Limitations

- Real Windows capture validation pending (requires pywin32 + Windows desktop)
- Real Revit integration validation pending (requires Revit installation)
- GUI tests not run (no Tcl/Tk display available in this environment)