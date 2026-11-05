# BIMSpend — Reuse-First Implementation Sequence

## Phase 0 — foundation

1. **R0-01 BUILD NEW — authentication/session.** Use Miru auth/policy behaviors as reference. Remove hardcoded identity; domain tests must deny designer approval/billing.
2. **R0-02 PORT LOGIC — tenant schema.** Add company/membership/client scope using ordered migrations. Preserve legacy rows in an explicitly unresolved workspace; pass cross-tenant, reopen and rollback tests.

## Phase 1 — native capture

3. **R1-01 REQUIRES VALIDATION — MPL boundary.** Record upstream SHA/path/local path/modifications, notices and counsel-approved covered-source delivery.
4. **R1-02 ADAPT SOURCE — Windows foreground capture.** Source: aw-watcher-window `windows.py`, loop in `main.py`. Destination: `capture/windows.py`, `window_watcher.py`. Test Win32/WMI failures, elevated windows, Unicode, jitter and shutdown.
5. **R1-03 REUSE DIRECTLY or PORT LOGIC — privacy.** Source: `privacy_filter.py` and tests. Default redact/drop before DB/logs.
6. **R1-04 ADAPT SOURCE — idle.** Source: aw-watcher-afk `windows.py`, `afk.py`. Test wraparound, long uptime, threshold, lock/suspend/resume and failure safety; build missing Windows lock detection.

## Phase 2 — event engine

7. **R2-01 ADAPT/PORT — heartbeat/overlap.** Source: aw-core transforms/tests. Deterministic shuffled-input, timezone/DST and cross-source no-double-count tests.
8. **R2-02 BUILD NEW — capture repository.** Preserve BIMSpend DB; add device/batch/checksum/diagnostic/retention. Concurrent repeat import produces one event and preserves decisions.
9. **R2-03 BUILD NEW — attribution revisions.** Uncertain activity stays unassigned; corrections append history.

## Phase 3 — Revit

10. **R3-01 BUILD NEW — versioned event contract.** Process/session/document lifecycle, hashed identity, forward-compatible synthetic multi-instance tests.
11. **R3-02 BUILD NEW — read-only connector/IPC.** Version-targeted signed binaries, no transactions/network in callbacks, failure isolation. Live Revit needs separately authorized environment.

## Phase 4 — Miru-informed business completion

12. **R4-01 PORT LOGIC — company/client/project/team policies.** Reproduce selected Miru model/policy/system scenarios in Python.
13. **R4-02 PORT LOGIC — timesheet/audit hardening.** Preserve BIMSpend states; test edit→submit→approve/reject→resubmit→explicit bill and billed immutability.
14. **R4-03 BUILD NEW — effective rates/budgets.** Use Miru rate immutability concept; separate cost/billing rates, budget versions, work-date calculation.
15. **R4-04 PORT LOGIC — reports.** Reproduce Miru filtering/group/CSV scenarios with reconciled SQL totals and tenant isolation.

## Phase 5 — release

16. **R5-01 ADAPT SOURCE patterns — single Windows installer.** Use AW PyInstaller/Inno lessons. Test writable AppData DB, disabled-by-default capture, pause/uninstall, upgrade/rollback, and absence of aw-server/Miru runtime.
17. **R5-02 DEFER — optional ActivityWatch/Miru adapters.** Later explicit, idempotent, disabled-by-default compatibility.

Every phase requires locked dependencies/SBOM, license and threat deltas, deterministic synthetic tests, Windows CI, DB upgrade/rollback, privacy log inspection and verified remote commits. Static inspection alone never completes a task.
