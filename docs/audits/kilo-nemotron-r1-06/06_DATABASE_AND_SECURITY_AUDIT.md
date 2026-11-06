# Database & Security Audit — BIMSpend R1-06

**Baseline**: `4e83d9b41533423f50c1f8042a2a2ef79445f0a4`
**Files Audited**:
- `src/bimspend/db.py` (1385 lines)
- `src/bimspend/auth.py` (303 lines)
- `src/bimspend/identity.py` (199 lines)
- `src/bimspend/models.py` (444 lines)

---

## SQLite Schema Analysis (Migrations v1-v9)

### Schema Evolution

| Version | Tables Added/Modified | Purpose |
|---------|----------------------|---------|
| v1 | projects, activity_events, attributed_time, time_entries, time_entry_audit, team_members, project_assignments | Build 01 core |
| v2 | is_archived on attributed_time/time_entries, UNIQUE idx on time_entries(attributed_time_id), query indexes | Archive, dedup, perf |
| v3 | user_identity_map | Historical user_id → team_member mapping |
| v4 | companies, company_members, user_credentials, sessions | Auth & multi-tenant |
| v5 | companies.is_active, time_entries.company_id | Security hardening |
| v6 | activity_events.company_id + indexes | Tenant isolation for capture |
| v7 | revit_sessions, revit_documents, revit_document_mappings, revit_correlation_evidence | Revit integration |
| v8 | time_entry_suggestions | Automatic timesheet suggestions |
| v9 | suggestion_decisions | Suggestion audit trail |

### Table Definitions & Constraints

#### projects
```sql
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    client TEXT NOT NULL,
    standard_rate REAL NOT NULL,
    loaded_cost_rate REAL NOT NULL,
    is_billable INTEGER NOT NULL DEFAULT 1,
    is_archived INTEGER NOT NULL DEFAULT 0,
    budget_aud REAL,
    created_at TEXT NOT NULL
);
```
- ✅ Rates validated non-negative finite in `upsert_project()`

#### activity_events
```sql
CREATE TABLE activity_events (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    app_name TEXT NOT NULL,
    window_title TEXT NOT NULL,  -- ALWAYS hashed
    started_at TEXT NOT NULL,
    ended_at TEXT NOT NULL,
    duration_minutes REAL NOT NULL,
    is_afk INTEGER NOT NULL DEFAULT 0,
    event_type TEXT NOT NULL,
    raw_payload TEXT,  -- NULL — never stored
    title_redacted INTEGER NOT NULL DEFAULT 1,
    company_id TEXT REFERENCES companies(id),  -- v6
    UNIQUE(source, external_id)  -- Idempotent ingestion
);
```
- ✅ `UNIQUE(source, external_id)` prevents duplicates
- ✅ `window_title` always hashed (`[HASH:...]`)
- ✅ `raw_payload` always NULL
- ✅ `company_id` FK to companies (v6)

#### attributed_time
```sql
CREATE TABLE attributed_time (
    id TEXT PRIMARY KEY,
    activity_event_id TEXT NOT NULL REFERENCES activity_events(id),
    project_id TEXT REFERENCES projects(id),  -- NULLABLE for unassigned
    attributed_minutes REAL NOT NULL,
    confidence REAL NOT NULL,
    correlation_method TEXT NOT NULL,
    created_at TEXT NOT NULL,
    is_archived INTEGER NOT NULL DEFAULT 0  -- v2
);
```
- ✅ `project_id` NULLABLE — unassigned events allowed
- ✅ FK to `activity_events(id)` — referential integrity
- ⚠️ No FK enforcement in SQLite unless `PRAGMA foreign_keys=ON` (set in `__init__`)

#### time_entries
```sql
CREATE TABLE time_entries (
    id TEXT PRIMARY KEY,
    attributed_time_id TEXT NOT NULL REFERENCES attributed_time(id),
    project_id TEXT NOT NULL REFERENCES projects(id),
    user_id TEXT NOT NULL,
    minutes REAL NOT NULL,
    state TEXT NOT NULL DEFAULT 'pending_review',
    standard_rate REAL NOT NULL,
    loaded_cost_rate REAL NOT NULL,
    billed_minutes REAL NOT NULL DEFAULT 0,
    review_notes TEXT,
    reviewed_by TEXT,
    reviewed_at TEXT,
    submitted_by TEXT,  -- v2
    submitted_at TEXT,  -- v2
    created_at TEXT NOT NULL,
    is_archived INTEGER NOT NULL DEFAULT 0,  -- v2
    company_id TEXT REFERENCES companies(id)  -- v5
);
```
- ✅ `attributed_time_id` FK — but **unique index only in v2 migration** (not in base DDL)
- ✅ `company_id` FK for tenant isolation (v5)
- ✅ Rate snapshots at creation
- ✅ `billed_minutes` separate from `minutes`

#### time_entry_suggestions (v8)
```sql
CREATE TABLE time_entry_suggestions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    company_id TEXT REFERENCES companies(id),
    project_id TEXT REFERENCES projects(id),
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    suggested_minutes REAL NOT NULL,
    confidence TEXT NOT NULL CHECK(confidence IN ('CONFIRMED','HIGH','MEDIUM','LOW','UNASSIGNED')),
    evidence_ids TEXT NOT NULL DEFAULT '[]',  -- JSON array
    state TEXT NOT NULL DEFAULT 'pending_review',
    edited_minutes REAL,
    edited_project_id TEXT REFERENCES projects(id),
    review_notes TEXT,
    submitted_by TEXT,
    submitted_at TEXT,
    reviewed_by TEXT,
    reviewed_at TEXT,
    time_entry_id TEXT REFERENCES time_entries(id),
    created_at TEXT NOT NULL
);
```
- ✅ `CHECK` constraint on confidence values
- ✅ `evidence_ids` stored as JSON
- ✅ `time_entry_id` FK to time_entries

#### suggestion_decisions (v9)
```sql
CREATE TABLE suggestion_decisions (
    id TEXT PRIMARY KEY,
    suggestion_id TEXT NOT NULL REFERENCES time_entry_suggestions(id),
    actor_id TEXT NOT NULL,
    actor_company_id TEXT NOT NULL,
    action TEXT NOT NULL CHECK(action IN ('submit','approve','reject','return_for_correction','split','merge')),
    previous_state TEXT,
    new_state TEXT NOT NULL,
    previous_minutes REAL,
    new_minutes REAL,
    notes TEXT,
    recorded_at TEXT NOT NULL
);
```
- ✅ Comprehensive audit trail
- ✅ `CHECK` constraint on action values

---

## Migration Safety Analysis

### Destructive Migrations
| Migration | Destructive Operation | Risk |
|-----------|----------------------|------|
| v2 | `CREATE UNIQUE INDEX ux_time_entries_attribution` | Fails if duplicate `attributed_time_id` exist (checked at line 268-271) |
| v3 | Populates `user_identity_map` for all existing `user_id` values | Safe — insert-only |
| v4 | Creates new auth tables | Safe — new tables |
| v5 | Adds `company_id` to `time_entries` (nullable) | Safe — nullable |
| v6 | Adds `company_id` to `activity_events` (nullable) | Safe — nullable |
| v7 | Creates Revit tables | Safe — new tables |
| v8 | Creates `time_entry_suggestions` | Safe — new table |
| v9 | Creates `suggestion_decisions` | Safe — new table |

### Rollback Procedures
**NO ROLLBACK PROCEDURES DOCUMENTED** — All migrations are forward-only. If a migration fails mid-way:
- SQLite transaction rolls back DDL within that migration
- But partial state across migrations not recoverable
- **Recommendation**: Document rollback SQL for each migration

### Schema Version Validation
```python
# db.py:90-94
if self.conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_version'").fetchone():
    version = self.conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
    if version is not None and version > 9:
        self.conn.close()
        raise RuntimeError(f"Database schema version {version} is newer than supported version 9")
```
- ✅ Rejects newer schema versions (fail-fast)
- ❌ No migration from older versions if gaps exist (but v1 always inserted)

---

## Foreign Key Integrity

### Current State
```python
# db.py:88
self.conn.execute("PRAGMA foreign_keys = ON")
```

### FK Constraints Defined
| Table | FK Column | References | Enforced |
|-------|-----------|------------|----------|
| attributed_time | activity_event_id | activity_events(id) | ✅ |
| attributed_time | project_id | projects(id) | ✅ (nullable) |
| time_entries | attributed_time_id | attributed_time(id) | ⚠️ Index only in v2 |
| time_entries | project_id | projects(id) | ✅ |
| time_entries | company_id | companies(id) | ✅ (v5) |
| activity_events | company_id | companies(id) | ✅ (v6) |
| revit_sessions | company_id | companies(id) | ✅ (v7) |
| revit_documents | company_id | companies(id) | ✅ (v7) |
| revit_document_mappings | document_guid | revit_documents(document_guid) | ✅ (v7) |
| revit_document_mappings | project_id | projects(id) | ✅ (v7) |
| revit_correlation_evidence | session_id | revit_sessions(id) | ✅ (v7) |
| revit_correlation_evidence | document_guid | revit_documents(document_guid) | ✅ (v7) |
| revit_correlation_evidence | activity_event_id | activity_events(id) | ✅ (v7, nullable) |
| company_members | company_id | companies(id) | ✅ (v4) |
| company_members | member_id | team_members(id) | ✅ (v4) |
| user_credentials | member_id | team_members(id) | ✅ (v4) |
| sessions | member_id | team_members(id) | ✅ (v4) |
| sessions | company_id | companies(id) | ✅ (v4) |
| user_identity_map | mapped_member_id | team_members(id) | ✅ (v3) |
| time_entry_suggestions | company_id | companies(id) | ✅ (v8) |
| time_entry_suggestions | project_id | projects(id) | ✅ (v8) |
| time_entry_suggestions | time_entry_id | time_entries(id) | ✅ (v8) |
| suggestion_decisions | suggestion_id | time_entry_suggestions(id) | ✅ (v9) |

### Critical FK Gap
**`time_entries.attributed_time_id` FK only has unique index in v2 migration, not in base DDL**:
```sql
-- Base DDL (v1): No FK declared for attributed_time_id
-- v2 migration: CREATE UNIQUE INDEX ux_time_entries_attribution ON time_entries(attributed_time_id)
```
- If DB created at v1 and never migrated to v2 → no FK enforcement
- **Risk**: Orphaned TimeEntries referencing deleted AttributedTime

---

## Transaction Handling

### Database.transaction() Context Manager
```python
@contextmanager
def transaction(self):
    outer = self._write_depth == 0
    if outer:
        for attempt in range(3):
            try:
                self.conn.execute("BEGIN IMMEDIATE")
                break
            except sqlite3.OperationalError as exc:
                if "locked" not in str(exc).lower() or attempt == 2:
                    raise
                time.sleep(0.05 * (attempt + 1))
    self._write_depth += 1
    try:
        yield
        if outer:
            self.conn.commit()
    except Exception:
        if outer:
            self.conn.rollback()
        raise
    finally:
        self._write_depth -= 1
```

### Properties
- ✅ `BEGIN IMMEDIATE` — reserves write lock upfront
- ✅ Retry on lock (3 attempts, exponential backoff)
- ✅ Nested transaction support (`_write_depth` counter)
- ✅ Automatic rollback on exception
- ✅ `PRAGMA busy_timeout = 5000` — 5s wait for lock

### Concurrency
- **WAL mode enabled** (`PRAGMA journal_mode = WAL`) — allows concurrent readers + single writer
- **Single writer limitation** — SQLite serializes writes
- **No connection pooling** — each `Database` instance = one connection
- **Risk**: Under high concurrent write load, writers queue on `BEGIN IMMEDIATE`

---

## Authentication & Authorization

### Password Hashing (`auth.py`)
```python
PBKDF2_ITERATIONS = 210_000  # OWASP 2024 baseline
PBKDF2_SALT_BYTES = 16
PBKDF2_HASH_ALGORITHM = "sha256"

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(PBKDF2_SALT_BYTES)
    dk = hashlib.pbkdf2_hmac(PBKDF2_HASH_ALGORITHM, password.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"

def verify_password(password: str, stored_hash: str) -> bool:
    # Constant-time comparison via secrets.compare_digest
```

### Assessment
| Aspect | Status | Notes |
|--------|--------|-------|
| Algorithm | ✅ PBKDF2-HMAC-SHA256 | Industry standard, FIPS-compliant |
| Iterations | ✅ 210,000 | Meets OWASP 2024 baseline |
| Salt | ✅ 16 random bytes | Unique per password |
| Constant-time compare | ✅ `secrets.compare_digest` | Prevents timing attacks |
| Upgrade path | ✅ Rehash on login if iterations < policy | One-way upgrade |
| Algorithm agility | ⚠️ Hardcoded SHA256 | Not Argon2id (dependency concern noted) |

### Session Management
```python
# SessionContext (identity.py) - fail-closed validation
@property
def actor(self) -> Actor | None:
    if self._actor is None: return None
    if self._db is not None:
        # Validates: session exists, not revoked, not expired, member active, company active
        # Re-derives role from company_members (authoritative)
```

### Authorization Gates
| Layer | Mechanism |
|-------|-----------|
| Route/Screen | Not implemented (Tkinter has no routing) |
| Domain Service | `require_actor(role, owner_id, company_id)` in every mutating method |
| Database | `company_id` on records + query filtering (partial) |
| Session | Validated on every `current_auth.actor` access |

---

## Tenant Isolation Analysis

### Company Scoping Enforcement

| Database Method | company_id Param | Enforces in Query |
|-----------------|------------------|-------------------|
| `list_projects()` | ❌ | ❌ — returns ALL projects |
| `get_project()` | ❌ | ❌ — no company filter |
| `list_events()` | ❌ | ❌ — filters by user_id only |
| `list_attributed_time()` | ❌ | ❌ — no company filter |
| `list_time_entries()` | ❌ | ❌ — no company filter |
| `list_time_entries_by_user()` | ❌ | ❌ — filters by user_id only |
| `list_suggestions()` | ❌ | ❌ — filters by user_id only |
| `upsert_project()` | ❌ | ❌ — no company association |
| `upsert_member()` | ❌ | ❌ — team_members not company-scoped |
| `assign_member()` | ❌ | ❌ — project_assignments not company-scoped |

### Critical Gap
**Most `list_*` and `get_*` methods do NOT enforce `company_id`** — they rely on callers to filter. Only auth-protected domain services enforce company scoping.

### Direct Database Access Risk
```python
# Any code with Database instance can bypass auth:
db = Database("bimspend.db")
all_projects = db.list_projects()  # Returns ALL companies' projects
all_entries = db.list_time_entries()  # Returns ALL companies' entries
```

### Mitigation
- Domain services (`review.py`, `suggestion_domain.py`) use `require_actor()` which validates company
- But raw `Database` access is unrestricted

---

## Privacy Audit

### Data Minimization
| Data Type | Stored | Protection |
|-----------|--------|------------|
| Window titles | ❌ Never | Hashed at capture: `[HASH:sha256[:8]]` |
| Raw payloads | ❌ Never | `raw_payload=NULL` in `ingest_event()` |
| Keystrokes | ❌ Never | Not captured |
| Screenshots | ❌ Never | Not captured |
| Clipboard | ❌ Never | Not captured |
| Revit document paths | ❌ Never | Hashed: `path_hash`, `central_path_hash` |
| Revit document titles | ❌ Never | Hashed: `title_hash` |

### Consent Enforcement
- ✅ Capture disabled by default (`consent_required=True`)
- ✅ Explicit `grant_consent()` required
- ✅ `revoke_consent()` stops capture
- ❌ **Bypass**: `Database.ingest_event()` accepts events without consent check

### Access Restrictions on Evidence
- `activity_events` table: `window_title` hashed, `raw_payload` NULL
- `revit_correlation_evidence`: Only metadata (duration, AFK, lock, confidence)
- `time_entry_suggestions`: `evidence_ids` only (FK to activity_events)
- **Gap**: No row-level security on evidence tables — any authenticated user in company can query

---

## Security Findings

| ID | Severity | Category | Finding |
|----|----------|----------|---------|
| DB-001 | CRITICAL | FK | `time_entries.attributed_time_id` FK not enforced in base DDL (only v2 unique index) |
| DB-002 | HIGH | Tenant | Most `list_*`/`get_*` methods lack `company_id` filtering — cross-tenant leakage via direct DB access |
| DB-003 | HIGH | Consent | `Database.ingest_event()` bypasses consent — direct DB calls can record events without user consent |
| DB-004 | HIGH | Migration | No rollback procedures documented for any migration |
| DB-005 | MEDIUM | Concurrency | Single SQLite connection, no pooling — writer contention under load |
| DB-006 | MEDIUM | Migration | v2 unique index creation fails if duplicates exist — no automated resolution |
| DB-007 | MEDIUM | Schema | `evidence_ids` stored as JSON TEXT — not queryable, no FK to activity_events |
| DB-008 | MEDIUM | Auth | Module-level `current_auth` global — not thread-safe for background workers |
| DB-009 | MEDIUM | Password | PBKDF2-SHA256 acceptable but not Argon2id (perf/dependency tradeoff documented) |
| DB-010 | LOW | Indexes | Missing composite indexes for common query patterns (user+company+state) |
| DB-011 | LOW | Constraints | No CHECK constraint on `time_entries.state` values |
| DB-012 | LOW | Constraints | No CHECK constraint on `billed_minutes <= minutes * policy_max` |
| DB-013 | LOW | Auditing | `time_entry_audit.actor_id` can be "unspecified_demo" — weak accountability |
| DB-014 | LOW | Privacy | Evidence tables (`revit_correlation_evidence`) lack row-level security |

---

## Recommendations

### P0 — Immediate
1. **Add FK to base DDL**: `attributed_time_id TEXT NOT NULL REFERENCES attributed_time(id)` in `time_entries` CREATE TABLE
2. **Enforce consent in `ingest_event()`**: Check `CaptureController.consent.granted` or require consent token
3. **Add `company_id` enforcement to ALL `list_*`/`get_*` methods** — default to authenticated actor's company

### P1 — Short-term
4. **Document migration rollback procedures** — SQL for each version
5. **Add connection pooling or async SQLite** — For concurrent writer support
6. **Add composite indexes**: `(user_id, company_id, state)` on time_entries, suggestions
7. **Replace module-level `current_auth` with per-request `SessionContext`** — Thread-safe

### P2 — Medium-term
8. **Row-level security via views** — Company-scoped views for all tables
9. **Financial audit table** — Separate from time_entry_audit
10. **Automated migration testing** — Test upgrade from each version to current

### P3 — Long-term
11. **PostgreSQL migration path** — For production multi-user concurrency
12. **Argon2id adoption** — When dependency constraints allow
13. **Zero-trust database access** — All queries via authenticated service layer