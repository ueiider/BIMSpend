# P0 foundation — implementation checkpoint

- Branch: `build/bimspend-p0-foundation`
- Base main: `65e344b340967108e35e54721d76ec223f8769e0`
- Status: PARTIAL. P0-001 WAL, busy timeout and short retry on write-lock acquisition; P0-002 nested transaction rollback for DB writes and synthetic batch; P0-003 ordered version 2 archive/index/idempotency migration; P0-005 archived state roundtrip; P0-006 unique attributed-time key; P0-007 FK query indexes; P0-008 adapter-independent startup.
- Files: `src/bimspend/db.py`, `src/bimspend/app/shell.py`, `tests/test_p0_sqlite_reliability.py`, `scripts/Test-BIMSpend.ps1`.
- Verification: 33 domain tests passed after schema checkpoint, 7 GUI tests deselected locally. Windows CI passed on `abfc8e217354654952d0c24d3f0ce02cdd1cd6bc` (run 42123241574), including the branch GUI test script. Later focused migration tests: 7 passed, 1 GUI deselected; CI of the latest test-only checkpoint still pending. Real two-connection lock-release, forced multi-write rollback, archive/restart, duplicate legacy migration failure and newer-schema rejection tested.
- Audit baseline: `D:/BIMSpend_Audit/10_GAP_ANALYSIS_ROADMAP/06_ENGINEERING_BACKLOG.md`, P0-001 through P0-008 verified locally.
- Remaining: P0-004 user identity reconciliation before team_members FK (existing synthetic IDs have no roster records); P0-003 migration v1 predates atomic migrations and legacy duplicates intentionally block v2 pending manual reconciliation; P0-006 needs concurrent collision and approved-state preservation tests. P0-009/P0-010 authentication scaffolding needs a safe session design. Lock exhaustion and failure-injection tests remain for P0-001/P0-002.
- Next exact action: add an explicit DB write transaction boundary and a lock contention test, then versioned migrations against a copy of the legacy preview database.
- No real monitoring, Miru transmission or deployment authorized.
