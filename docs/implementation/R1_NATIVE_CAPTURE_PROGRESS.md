# R1 Native Capture — Implementation Checkpoint

- Branch: `build/bimspend-r1-05-timesheet-suggestions` (created from `build/bimspend-r1-04-revit-correlation` at `842ae0cbaa667a2f1aece0bfd60c24b4c013418a`)
- Base main: `65e344b340967108e35e54721d76ec223f8769e0`
- Status: R1-01/R1-02/R1-03 complete, R1-04 complete, R1-05 complete. All 139 domain tests + 58 GUI+capture tests pass.
- Schema version: v8 (time_entry_suggestions table).

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

## R1-05 — Automatic Time Entry Suggestions & Designer Review

- `src/bimspend/capture/suggestion_engine.py` — Session-based suggestion engine
  - Groups consecutive same-project observations into suggestions
  - Excludes AFK and locked-session intervals
  - Company-scoped, idempotent generation
  - Deterministic ID generation from input data
  - Confidence levels: CONFIRMED, HIGH, MEDIUM, LOW, UNASSIGNED
- `src/bimspend/models.py` — TimeEntrySuggestion dataclass, SuggestionState enum
- `src/bimspend/db.py` — v8 migration: time_entry_suggestions table + indexes
- Database methods: upsert_suggestion, get_suggestion, list_suggestions
- Domain actions: submit_suggestion, reject_suggestion
- Tests: `tests/capture/test_suggestion_engine.py` — 13 tests

## SQLite Integration

- v8 migration: time_entry_suggestions table + 4 indexes
- WAL mode, busy timeout, transaction safety preserved
- Idempotent ingestion via UNIQUE(source, external_id)

## Tests

- `tests/capture/test_capture_module.py` — 29 tests (capture module)
- `tests/capture/test_correlation.py` — 9 tests (correlation engine)
- `tests/capture/test_suggestion_engine.py` — 13 tests (suggestion engine)
- 139 domain tests pass
- 58 GUI+capture tests pass

## CI

- `.github/workflows/preview-tests.yml` — includes `build/bimspend-r1-05-timesheet-suggestions`

## Remaining Limitations

- Real Windows capture validation pending (requires pywin32 + Windows desktop)
- Real Revit integration validation pending (requires Revit installation)
- IPC named pipe not tested on real Windows (pywin32 pipe functions unavailable locally)
- No Windows autostart or background service (by design)

## Next Implementation Action

R1-05 is complete. Next milestone: R1-06 — Timesheet Review GUI & Manager Approval UI (designer review screens, manager approval dashboard, submission workflow UI).