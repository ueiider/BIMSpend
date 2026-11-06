# Windows Capture Audit — BIMSpend R1-06

**Baseline**: `4e83d9b41533423f50c1f8042a2a2ef79445f0a4`
**Files Audited**:
- `src/bimspend/capture/controller.py` (311 lines)
- `src/bimspend/capture/activitywatch_derived/watcher_main.py` (236 lines)
- `src/bimspend/capture/activitywatch_derived/windows.py` (226 lines)
- `src/bimspend/capture/activitywatch_derived/privacy_filter.py` (151 lines)
- `src/bimspend/capture/afk_detector.py` (109 lines)
- `src/bimspend/capture/session_lock.py` (695 lines)
- `src/bimspend/capture/heartbeat.py` (204 lines)

---

## ActivityWatch Integration

### Source Provenance
| Component | Upstream | Commit | License |
|-----------|----------|--------|---------|
| aw-watcher-window/main.py | ActivityWatch/aw-watcher-window | `12000f58d16b8fc1376af42755c688b3d7157280` | MPL-2.0 |
| aw-watcher-window/windows.py | ActivityWatch/aw-watcher-window | `12000f58d16b8fc1376af42755c688b3d7157280` | MPL-2.0 |
| aw-watcher-window/privacy_filter.py | ActivityWatch/aw-watcher-window | `12000f58d16b8fc1376af42755c688b3d7157280` | MPL-2.0 |

### Modifications from Upstream
| File | Key Changes |
|------|-------------|
| `watcher_main.py` | Removed aw-client, multiprocessing, macOS/Linux, heartbeat queuing; added privacy filter, consent, company_id, lifecycle states |
| `windows.py` | Kept core APIs; added `get_current_window()` dict abstraction; WMI fallback for elevated processes; graceful error handling |
| `privacy_filter.py` | Simplified config (list of dicts vs TOML); added `hash_title()`; added default rules for banking/password managers |

### MPL-2.0 Compliance
- ✅ License headers preserved on all three files
- ✅ Original copyright notices retained
- ✅ Modifications documented in `ACTIVITYWATCH_SOURCE_MANIFEST.md`
- ✅ License text included at `docs/open-source/LICENSE.MPL-2.0.activitywatch.txt`
- ⚠️ Source distribution obligation (MPL-2.0 §3.2) — pending legal review before executable distribution

---

## Capture Lifecycle

### State Machine (CaptureController)
```
STOPPED → RUNNING → PAUSED → RUNNING
    ↑         │         │
    │         ▼         ▼
    └───── ERROR ◄──────┘
    │
    └───── (revoke_consent)
```

### Consent Model
- **Default**: Capture DISABLED (`consent_required=True`)
- **Grant**: Explicit `grant_consent(granted_by)` required
- **Revoke**: `revoke_consent()` stops capture immediately
- **Validation**: `_validate_auth()` requires authenticated session with `company_id`

### Event Flow
```
HeartbeatLoop (poll_time=5s default)
    │
    ├─ get_current_window() → win32gui.GetForegroundWindow()
    │    ├─ Get window title (GetWindowText)
    │    ├─ Get app name/path (win32process + WMI fallback)
    │    └─ Handle UWP ApplicationFrameHost
    │
    ├─ transform_window() → privacy_filter.apply_privacy_filters()
    │    ├─ Drop: private browsing, password managers
    │    └─ Redact: banking/finance domains
    │
    ├─ HeartbeatManager.observe() → interval management
    │    ├─ Close interval on: app change, title change, AFK change, gap > 2×poll_time
    │    └─ Generate HeartbeatEvent with duration
    │
    └─ CaptureController._persist_event() → Database.ingest_event()
         ├─ external_id = "aw:{app}:{title_hash}:{start_time}"
         ├─ title ALWAYS hashed: "[HASH:{sha256[:8]}]"
         ├─ raw_payload = None (never stored)
         ├─ title_redacted = True
         └─ company_id from authenticated session
```

---

## AFK Detection

### Implementation (`afk_detector.py`)
```python
def _get_idle_seconds(self) -> float:
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
        last_input_tick = lii.dwTime
        current_tick = ctypes.windll.kernel32.GetTickCount64()
        # Handle 49.7-day wraparound
        diff_ms = current_tick - last_input_tick if current_tick >= last_input_tick else (2**32 - last_input_tick) + current_tick
        return diff_ms / 1000.0
    return 0.0
```

### Critical Limitation
**`GetLastInputInfo` returns SYSTEM-WIDE last input time**, not per-session.
- On multi-user Windows (Terminal Services, fast user switching), returns last input across ALL sessions
- Cannot distinguish between "user is AFK" and "another user is active"
- **Impact**: False AFK negatives (user marked active when actually AFK) or false positives

### Configuration
- Default threshold: 5 minutes (configurable via `set_threshold_minutes`)
- State transitions logged at INFO level

---

## Session Lock Detection

### Implementation (`session_lock.py`)
Two detection methods:

1. **Primary**: `WTSRegisterSessionNotification` + message-only window
   - Receives `WM_WTSSESSION_CHANGE` with `WTS_SESSION_LOCK` (0x7) / `WTS_SESSION_UNLOCK` (0x8)
   - Event-driven, immediate detection

2. **Fallback**: Polling `WTSQuerySessionInformation` every 10 seconds
   - Queries `WTSConnectState` (WTSActive=0, WTSConnected=1 → UNLOCKED; else LOCKED)
   - 10-second detection latency

### Critical Issues
| Issue | Severity | Evidence |
|-------|----------|----------|
| WTSAPI32 may not be available | HIGH | `_HAS_WTSAPI` flag; on failure, detector returns `UNKNOWN` always |
| Polling interval 10s | MEDIUM | Misses lock/unlock events between polls |
| No per-session tracking | HIGH | Uses current process session ID; doesn't track specific user session |
| Message pump thread | MEDIUM | `GetMessageW` blocks; `PostQuitMessage` used for shutdown |

### Integration with Capture
- `CaptureController` does NOT directly integrate with `SessionLockDetector`
- `HeartbeatManager.observe()` accepts `is_locked` parameter but nothing passes it
- `controller.py` has no reference to `SessionLockDetector`
- **Gap**: Lock state never fed into capture pipeline

---

## Heartbeat & Interval Management

### HeartbeatManager (`heartbeat.py`)
Manages continuous intervals to avoid duplicate events:
- **Interval closed when**: app changes, title hash changes, AFK state changes, gap > 2×poll_time (default 10s)
- **External ID**: `source:app:title_hash:start_time` — enables idempotent ingestion
- **Duration**: Computed from ISO timestamps on interval close
- **Thread-safe**: Uses `threading.Lock`

### Idempotency
- `Database.ingest_event()` uses `UNIQUE(source, external_id)` constraint
- Duplicate events (same source, app, title, start time) silently ignored
- **Correct**: Prevents double-counting on restart/retry

---

## Privacy Filtering

### Default Rules (`privacy_filter.py:143-151`)
```python
DEFAULT_PRIVACY_RULES = [
    {"pattern": r"(?i)private browsing|incognito", "action": "drop"},
    {"pattern": r"(?i)bank", "action": "redact", "replacement": "[REDACTED]"},
    {"pattern": r"(?i)paypal", "action": "redact", "replacement": "[REDACTED]"},
    {"pattern": r"(?i)1password|lastpass|bitwarden|keepass", "action": "drop"},
]
```

### Application Order
1. **Privacy filter** (first) — drops/redacts sensitive events
2. **App exclusion** — drops entire apps matching regex
3. **Title exclusion** — replaces title with "excluded"
4. **Global title exclusion** — replaces all titles with "excluded"

### Title Hashing
- Always applied in `_persist_event()`: `title_hash = "[HASH:{sha256(title)[:8]}]"`
- Raw title NEVER stored in database
- Hash allows grouping similar titles without exposing content

---

## Runtime Behavior Gaps

| Scenario | Current Behavior | Risk |
|----------|------------------|------|
| Application switching | Interval closed, new interval started | Correct |
| Multiple windows same app | Title hash change closes interval | May over-fragment |
| Rapid foreground changes | Poll interval (5s) limits resolution | Misses sub-5s interactions |
| Process termination | `process_terminated=True` in window dict | Handled gracefully |
| Windows sleep/resume | Parent death detection (`os.getppid()==1`) | Stops capture loop |
| Tracking pause/resume | `CaptureController.pause()/resume()` | Works at controller level |
| Missing dependencies | `_require_win32()` raises clear ImportError | Fail-fast |
| Unexpected crashes | HeartbeatLoop catches exceptions, backs off | Loop continues |

---

## Critical Unvalidated Assumptions

1. **No real Windows testing** — All capture code tested only with synthetic fixtures
2. **AFK detection is per-system, not per-session** — Invalid on multi-user Windows
3. **Session lock detection may be unavailable** — WTSAPI32 not guaranteed
4. **Lock state not integrated into capture** — `SessionLockDetector` unused by `CaptureController`
5. **UWP handling incomplete** — Only checks `ApplicationFrameHost`; other UWP hosts not handled
6. **Elevated process access** — WMI fallback works but adds latency
7. **No capture quality metrics** — No visibility into missed events, false positives

---

## Findings

| ID | Severity | Category | Finding |
|----|----------|----------|---------|
| WC-001 | CRITICAL | Consent | `Database.ingest_event()` bypasses consent check — direct DB calls can record events without user consent |
| WC-002 | HIGH | AFK | `GetLastInputInfo` returns system-wide idle time — incorrect on multi-session Windows |
| WC-003 | HIGH | Lock | `SessionLockDetector` not integrated into capture pipeline — lock state never suppresses attribution |
| WC-004 | HIGH | Lock | WTSAPI32 may be unavailable — detector returns `UNKNOWN`, capture continues unattributed |
| WC-005 | MEDIUM | Polling | 5s poll interval misses sub-5s window interactions |
| WC-006 | MEDIUM | UWP | Only `ApplicationFrameHost` handled; other UWP frame hosts not detected |
| WC-007 | MEDIUM | Privacy | Default privacy rules minimal — no coverage for healthcare, legal, govt sensitive apps |
| WC-008 | MEDIUM | Idempotency | `external_id` includes start_time — clock skew could cause duplicates |
| WC-009 | LOW | Backoff | Error backoff uses exponential delay but no maximum retry limit |
| WC-010 | LOW | Logging | No structured capture quality metrics (events/sec, drop rate, error rate) |
| WC-011 | LOW | Config | Hardcoded defaults (poll_time=5s, afk_threshold=5min) not externalized |
| WC-012 | LOW | Testing | No integration tests for capture→DB pipeline with real Windows APIs |

---

## Recommendations

### P0 — Immediate
1. **Move consent check into `Database.ingest_event()`** — Prevent bypass via direct DB calls
2. **Integrate `SessionLockDetector` into `CaptureController`** — Pass `is_locked` to `HeartbeatManager`
3. **Add per-session AFK detection** — Use `WTSQuerySessionInformation` with session ID

### P1 — Short-term
4. **Externalize capture config** — Poll time, AFK threshold, privacy rules via config file
5. **Add capture health metrics** — Events captured, dropped, errors, last successful poll
6. **Expand default privacy rules** — Add patterns for RDP, VPN, credential managers, healthcare apps

### P2 — Medium-term
7. **Implement per-session idle detection** — Track input per Windows session ID
8. **Add capture quality dashboard** — Real-time visibility into capture completeness
9. **Support configurable poll intervals per app** — Lower frequency for stable apps

### P3 — Long-term
10. **Consider Event Tracing for Windows (ETW)** — More reliable than polling for window focus
11. **Add capture replay/verification mode** — Compare captured events with ground truth