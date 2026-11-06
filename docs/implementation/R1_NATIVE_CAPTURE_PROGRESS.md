# R1 Native Capture — Implementation Checkpoint

- Branch: `build/bimspend-r1-04-revit-correlation` (created from `build/bimspend-r1-native-capture` at `59d5dd259dcc57538a1211ce808b005245aebbdf`)
- Base main: `65e344b340967108e35e54721d76ec223f8769e0`
- Status: R1-01/R1-02/R1-03 complete, R1-04 complete. All 126 domain tests + 45 GUI+capture tests pass.
- Schema version: v7 (revit_sessions, revit_documents, revit_document_mappings, revit_correlation_evidence).

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

## SQLite Integration

- v7 migration: Revit tables + indexes
- WAL mode, busy timeout, transaction safety preserved
- Idempotent ingestion via UNIQUE(source, external_id)

## Tests

- `tests/capture/test_capture_module.py` — 29 tests (capture module)
- `tests/capture/test_correlation.py` — 9 tests (correlation engine)
- 126 domain tests pass (97 original + 29 capture)
- 45 GUI+capture tests pass (7 GUI + 38 capture)

## CI

- `.github/workflows/preview-tests.yml` — includes `build/bimspend-r1-04-revit-correlation`

## Remaining Limitations

- Real Windows capture validation pending (requires pywin32 + Windows desktop)
- Real Revit integration validation pending (requires Revit installation)
- IPC named pipe not tested on real Windows (pywin32 pipe functions unavailable locally)
- No Windows autostart or background service (by design)

## Next Implementation Action

R1-05 — Turn attributed activity into user-reviewable timesheet suggestions
(correlation evidence → suggested time entries → designer review workflow)
