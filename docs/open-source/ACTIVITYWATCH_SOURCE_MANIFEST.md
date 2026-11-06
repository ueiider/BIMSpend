# ActivityWatch Source Provenance Manifest

This document records every file copied or adapted from ActivityWatch for use in BIMSpend.
ActivityWatch-derived code is kept in `src/bimspend/capture/activitywatch_derived/`
under the MPL-2.0 license. Proprietary BIMSpend orchestration, domain logic,
privacy boundary enforcement, and SQLite integration live outside this package.

## Upstream Pinned Revisions

| Component | Repository | Commit SHA | Branch | License |
|-----------|-----------|------------|--------|---------|
| ActivityWatch bundle | https://github.com/ActivityWatch/activitywatch | `9fee4702fea08dbe0149cc6e28f4ef66b49f54ec` | master | MPL-2.0 |
| aw-watcher-window | https://github.com/ActivityWatch/aw-watcher-window | `12000f58d16b8fc1376af42755c688b3d7157280` | master | MPL-2.0 |

Source pointers:
- Bundle: https://github.com/ActivityWatch/activitywatch/commit/9fee4702fea08dbe0149cc6e28f4ef66b49f54ec
- MPL-2.0: https://github.com/ActivityWatch/activitywatch/blob/9fee4702fea08dbe0149cc6e28f4ef66b49f54ec/LICENSE.txt
- Window watcher: https://github.com/ActivityWatch/aw-watcher-window/commit/12000f58d16b8fc1376af42755c688b3d7157280

## File Inventory

### 1. `aw-watcher-window/aw_watcher_window/main.py` (upstream) → `src/bimspend/capture/activitywatch_derived/watcher_main.py` (BIMSpend)

- **Upstream repository**: https://github.com/ActivityWatch/aw-watcher-window
- **Upstream commit**: `12000f58d16b8fc1376af42755c688b3d7157280`
- **Upstream path**: `aw_watcher_window/main.py`
- **BIMSpend destination**: `src/bimspend/capture/activitywatch_derived/watcher_main.py`
- **Original license**: MPL-2.0
- **Original copyright**: ActivityWatch contributors (see LICENSE.txt at bundle commit)
- **Modification summary**: 
  - Removed aw-client dependency; replaced with BIMSpend SQLite persistence
  - Removed multiprocessing/freeze_support (single-process desktop app)
  - Removed macOS/Linux strategy branches; Windows-only foreground capture
  - Removed heartbeat queuing to aw-server; events written to BIMSpend SQLite
  - Added company_id scoping from authenticated session context
  - Added fail-closed privacy boundary before persistence
  - Added capture lifecycle states (Stopped/Running/Paused/Error)
  - Added explicit user-consent requirement (disabled by default)
- **Dependencies introduced**: None new (uses existing `win32api`, `win32gui`, `win32process`, `wmi` on Windows)
- **Relevant upstream tests adapted**: None (upstream has no Python unit tests for main.py)

### 2. `aw-watcher-window/aw_watcher_window/windows.py` (upstream) → `src/bimspend/capture/activitywatch_derived/windows.py` (BIMSpend)

- **Upstream repository**: https://github.com/ActivityWatch/aw-watcher-window
- **Upstream commit**: `12000f58d16b8fc1376af42755c688b3d7157280`
- **Upstream path**: `aw_watcher_window/windows.py`
- **BIMSpend destination**: `src/bimspend/capture/activitywatch_derived/windows.py`
- **Original license**: MPL-2.0
- **Original copyright**: ActivityWatch contributors (see LICENSE.txt at bundle commit)
- **Modification summary**:
  - Kept `get_active_window_handle()`, `get_window_title()`, `get_app_name()`, `get_app_path()`
  - Kept WMI fallback for elevated/admin processes
  - Added `get_current_window()` abstraction returning a dict with app, title, timestamp
  - Added graceful handling of invalid handles and destroyed windows
  - Added `process_terminated` detection
- **Dependencies introduced**: `pywin32` (win32api, win32gui, win32process), `wmi` (Windows only)
- **Relevant upstream tests adapted**: None

### 3. `aw-watcher-window/aw_watcher_window/privacy_filter.py` (upstream) → `src/bimspend/capture/activitywatch_derived/privacy_filter.py` (BIMSpend)

- **Upstream repository**: https://github.com/ActivityWatch/aw-watcher-window
- **Upstream commit**: `12000f58d16b8fc1376af42755c688b3d7157280`
- **Upstream path**: `aw_watcher_window/privacy_filter.py`
- **BIMSpend destination**: `src/bimspend/capture/activitywatch_derived/privacy_filter.py`
- **Original license**: MPL-2.0
- **Original copyright**: ActivityWatch contributors (see LICENSE.txt at bundle commit)
- **Modification summary**:
  - Kept `compile_privacy_rules()` and `apply_privacy_filters()` with MPL-2.0 header
  - Simplified rule config (no TOML parsing; rules passed as list of dicts)
  - Added `hash_title()` for deterministic title hashing
  - Added `PRIVACY_POLICY` documentation of stored fields
- **Dependencies introduced**: None (uses `re`, `logging`)
- **Relevant upstream tests adapted**: None

### 4. MPL-2.0 License Text

- **Source**: https://github.com/ActivityWatch/activitywatch/blob/9fee4702fea08dbe0149cc6e28f4ef66b49f54ec/LICENSE.txt
- **BIMSpend destination**: `docs/open-source/LICENSE.MPL-2.0.activitywatch.txt`
- **Purpose**: Required by MPL-2.0 section 3.4 (include license with covered source)
- **Notice**: MPL-2.0 requires that covered source files retain their license headers
  and that modified files distributed in executable form have corresponding source
  made available. BIMSpend must preserve MPL-2.0 headers on all activitywatch_derived
  files and include this license text in distributions.

## Local File Hashes

File hashes are recorded at commit time. Each activitywatch_derived file carries
an MPL-2.0 header with the upstream source path and commit SHA for provenance
tracking.

## Engineering Boundary

ActivityWatch-derived code is isolated in `src/bimspend/capture/activitywatch_derived/`.
BIMSpend proprietary code (capture controller, SQLite integration, consent
management, privacy policy enforcement) does not modify ActivityWatch covered
files. The two layers communicate through well-defined interfaces:

1. `activitywatch_derived.windows.get_current_window()` → raw window observation
2. `activitywatch_derived.privacy_filter.apply_privacy_filters()` → privacy-filtered observation
3. `capture.controller.CaptureController` → lifecycle, consent, SQLite persistence

## MPL-2.0 Obligations

- [x] MPL-2.0 license text included at `docs/open-source/LICENSE.MPL-2.0.activitywatch.txt`
- [x] All activitywatch_derived files carry MPL-2.0 headers with upstream attribution
- [x] Original copyright notices preserved in adapted files
- [x] Modifications documented in this manifest
- [ ] Source of covered modified files must be made available when distributed in executable form (MPL-2.0 §3.2) — pending legal review before any distribution
- [ ] Legal compliance review required before production release

## Limitation

The exact recursive gitlink SHA equality between the umbrella commit `9fee4702fea08dbe0149cc6e28f4ef66b49f54ec` and individual component heads was marked **NÃO VALIDADO** in the PLAN_AUDIT_REPORT.md. The aw-watcher-window commit `12000f58d16b8fc1376af42755c688b3d7157280` was inspected independently on 2026-11-05. A Phase 2 checkout must record `git submodule status --recursive` before any build.

## Blockers

None. Source provenance established for all three adapted files. MPL-2.0 obligations
documented. Legal review required before any distribution of modified MPL-2.0
covered files in executable form.
