# P0 foundation — implementation checkpoint

- Branch: `build/bimspend-p0-foundation`
- Base main: `65e344b340967108e35e54721d76ec223f8769e0`
- Status: PARTIAL. P0-001 WAL, busy timeout and short retry on write-lock acquisition; P0-002 nested transaction rollback for DB writes and synthetic batch; P0-008 adapter-independent startup. P0-003 initial schema version tracking remains incomplete.
- Files: `src/bimspend/db.py`, `src/bimspend/app/shell.py`, `tests/test_p0_sqlite_reliability.py`, `scripts/Test-BIMSpend.ps1`.
- Verification: 9 focused tests passed after transaction checkpoint, 2 GUI tests deselected. Real two-connection lock-release and forced multi-write rollback tested. Earlier: 29 domain tests passed; adapter-blocked GUI startup passed. Windows CI not yet run on this branch.
- Audit baseline: `D:/BIMSpend_Audit/10_GAP_ANALYSIS_ROADMAP/06_ENGINEERING_BACKLOG.md`, P0-001 through P0-008 verified locally.
- Remaining: P0-003 full migration transactions, P0-004 identity reconciliation before foreign key, P0-005 archived field persistence, P0-006 time-entry deduplication, P0-007 indexes; authentication scaffolding P0-009/P0-010 needs safe session design. Lock exhaustion and failure-injection tests remain for P0-001/P0-002.
- Next exact action: add an explicit DB write transaction boundary and a lock contention test, then versioned migrations against a copy of the legacy preview database.
- No real monitoring, Miru transmission or deployment authorized.
