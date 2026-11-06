# R1 Native Capture — Implementation Checkpoint

- Branch: `build/bimspend-r1-native-capture` (created from `build/bimspend-p0-security-hardening` at `70d4074fc82853a0a80b9d375c691cbc70f0f303`)
- Base main: `65e344b340967108e35e54721d76ec223f8769e0`
- Status: R1-01/R1-02 complete, R1-03 complete. All 113 domain tests + 7 GUI tests pass.
- Schema version: v6 (activity_events.company_id for tenant isolation).

## R1-01 — ActivityWatch Source Provenance

- Upstream: ActivityWatch bundle `9fee4702fea08dbe0149cc6e28f4ef66b49f54ec` (MPL-2.0)
- Upstream: aw-watcher-window `12000f58d16b8fc1376af42755c688b3d7157280` (MPL-2.0)
- Manifest: `docs/open-source/ACTIVITYWATCH_SOURCE_MANIFEST.md`
- License: `docs/open-source/LICENSE.MPL-2.0.activitywatch.txt`
- Adapted files (MPL-2.0, in `src/bimspend/capture/activitywatch_derived/`):
  - `windows.py` ← `aw_watcher_window/windows.py` — Win32 API window capture primitives
  - `privacy_filter.py` ← `aw_watcher_window/privacy_filter.py` — drop/redact privacy rules
  - `watcher_main.py` ← `aw_watcher_window/main.py` — polling heartbeat loop, pulsetime, error backoff
- BIMSpend proprietary orchestration in `src/bimspend/capture/` (not ActivityWatch-derived)

## R1-02 — Native Windows Foreground Capture

- `src/bimspend/capture/activitywatch_derived/windows.py` — `get_active_window_handle()`, `get_window_title()`, `get_app_name()`, `get_app_path()`, WMI fallback for elevated processes, UWP frame host handling
- `src/bimspend/capture/controller.py` — CaptureController with lifecycle states (STOPPED/Running/PAUSED/ERROR), consent management, company-scoped authorization, SQLite persistence
- Capture disabled by default; explicit consent required via `grant_consent()`
- Fail-closed session validation at capture start
- Company-scoped events stored in `activity_events` with `company_id`
- Privacy filtering before persistence (raw titles never stored)
- No automatic billing — activity events are observed data only
- Graceful handling of missing pywin32 (import-safe on non-Windows)

## R1-03 — AFK Detection, Session Lock, Heartbeat

- `src/bimspend/capture/afk_detector.py` — AFKDetector using Windows GetLastInputInfo API, configurable threshold (default 5 min), ACTIVE/AFK states, transition detection
- `src/bimspend/capture/session_lock.py` — SessionLockDetector with UNKNOWN fail-safe state, LOCKED/UNLOCKED/UNKNOWN states, callback support
- `src/bimspend/capture/heartbeat.py` — HeartbeatManager with stable event IDs, idempotent external_id, interval management across app switches/AFK/lock transitions, UTC timestamps
- State model: ACTIVE → AFK → LOCKED → ACTIVE → PAUSED → STOPPED

## SQLite Integration

- v6 migration: `activity_events.company_id` column + indexes
- `ActivityEvent.company_id` field added to model
- `Database.ingest_event()` accepts optional `company_id` parameter
- Idempotent ingestion via UNIQUE(source, external_id)
- WAL mode, busy timeout, transaction safety preserved

## Tests

- `tests/capture/test_capture_module.py` — 25 tests covering privacy filters, heartbeat intervals, AFK detector, session lock, capture controller lifecycle, consent, SQLite persistence, idempotency, no auto-billing
- 113 domain tests pass (88 original + 25 capture)
- 7 GUI tests pass

## CI

- `.github/workflows/preview-tests.yml` — added `build/bimspend-r1-native-capture` branch
- CI not yet triggered on this branch

## Remaining Limitations

- Real Windows capture validation pending (requires pywin32 + Windows desktop)
- AFK threshold is configurable but not yet wired to company policy
- Session lock detection returns UNKNOWN (WMI alone cannot reliably detect lock state)
- No Windows autostart or background service (by design, phase 1 limitation)
- Real Windows CI validation pending

## Next Implementation Action

R1-04 — Native Revit Activity Detection and Project Correlation (read-only Revit connector, document/view signals, correlation with Windows foreground capture)
