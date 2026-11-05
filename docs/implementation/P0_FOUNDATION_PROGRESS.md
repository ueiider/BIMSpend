# P0 foundation — implementation checkpoint

- Branch: `build/bimspend-p0-foundation`
- Base main: `65e344b340967108e35e54721d76ec223f8769e0`
- Status: PARTIAL. P0-001 WAL, busy timeout and short retry on write-lock acquisition; P0-002 nested transaction rollback for DB writes and synthetic batch; P0-003 ordered version 2 archive/index/idempotency migration; P0-004 user identity reconciliation (user_identity_map table, resolve/map/unmap methods); P0-005 archived state roundtrip; P0-006 unique attributed-time key; P0-007 FK query indexes; P0-008 adapter-independent startup.
- Files: `src/bimspend/db.py`, `src/bimspend/models.py`, `src/bimspend/app/shell.py`, `tests/test_p0_sqlite_reliability.py`, `scripts/Test-BIMSpend.ps1`.
- Verification: 40 domain tests passed (35 existing + 5 new P0-004 tests), 7 GUI tests deselected locally. Windows CI passed on `8156553c99673200835283f26f6dcc9b62bdfada` (run 42123517469), including the branch GUI test script; CI for the final migration change remains pending. Real two-connection lock-release, forced multi-write rollback, archive/restart, duplicate legacy migration failure, newer-schema rejection, identity map creation, user-to-team mapping, unmap, nonexistent member rejection, and migration repeatability tested.
- Audit baseline: `D:/BIMSpend_Audit/10_GAP_ANALYSIS_ROADMAP/06_ENGINEERING_BACKLOG.md`, P0-001 through P0-008 verified locally.
- Remaining: P0-009/P0-010 authentication scaffolding needs a safe session design (current_user hardcoded in shell.py). Lock exhaustion and failure-injection tests remain for P0-001/P0-002 (basic lock test exists, more coverage needed).
- Next exact action: complete authentication scaffolding (P0-009/P0-010), then run full test suite and CI validation.
- No real monitoring, Miru transmission or deployment authorized.