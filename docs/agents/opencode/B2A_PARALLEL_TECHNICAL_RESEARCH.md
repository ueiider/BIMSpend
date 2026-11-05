# BIMSpend — B2-A Parallel Technical Research Report

**Mode:** READ-ONLY RESEARCH AND DOCUMENTATION ONLY. No implementation, no builds, no test execution, no dependency installation, no merges, no changes to `main`.  
**Branch:** `agent/opencode-b2a-parallel-research` (created from `main` at `eb13fc9`)  
**Repository:** https://github.com/ueiider/BIMSpend  
**Gate status:** B2-A remains BLOCKED pending explicit user approval.  
**Independence:** This report is produced independently of the NVIDIA audit (`agent/claude-b2a-review`). Findings that depend on unpublished NVIDIA results are explicitly marked as pending.

---

## 1. Executive Summary

This report resolves technical questions that can be answered independently of the NVIDIA independent audit, using direct source-code inspection of the pinned upstream repositories (Miru `10e457e1...` on `develop`, ActivityWatch bundle `9fee4702...` on `master`) and the current BIMSpend planning baseline (`main` at `eb13fc9`).

**Confirmed findings (verified from source):**

| Finding | Confidence | Source |
|---|---|---|
| Miru agent timesheet `create` has NO idempotency check on `external_run_id`/`external_session_id` | VERIFIED | `app/controllers/api/v1/agent/timesheet_entries_controller.rb` lines 4-23 |
| Miru `DesktopCurrentTimer` model has no `synced_at` attribute validation; `synced_at` exists only in controller DEFAULT_TIMER hash | VERIFIED | `app/models/desktop_current_timer.rb` lines 1-9; controller lines 6-16, 78 |
| Miru `rack_attack.rb` has NO throttle for `/api/v1/agent/*` routes | VERIFIED | `config/initializers/rack_attack.rb` lines 13-65 |
| Miru `ProfitabilityBillingRate` is a client billing/charge rate, NOT internal loaded labor cost | VERIFIED | `app/models/profitability_billing_rate.rb` lines 3-18 |
| Miru agent capabilities endpoint exposes exactly one command: "time create" | VERIFIED | `app/controllers/api/v1/agent/capabilities_controller.rb` lines 4-22 |
| Miru `AgentKey`: 32-byte token, SHA-256 digest, `revoked_at`, `last_used_at`, no expiry/rotation/device binding | VERIFIED | `app/models/agent_key.rb` lines 3-40 |
| ActivityWatch bundle is a git-submodule meta-package; 11 submodules, all uninitialized (empty dirs) | VERIFIED | `.gitmodules`, `git submodule status` |
| ActivityWatch has two servers: aw-server (Python, current default) and aw-server-rust (Rust, planned future) | VERIFIED | `README.md` lines 255-260, 214-216 |
| ActivityWatch REST API: Buckets, Events, Heartbeat, Query, Export (JSON) via `/api/0` | VERIFIED (README-described) | `README.md` lines 262-269 |
| Miru canonical CI commands identified from `.github/workflows/validations.yml` | VERIFIED | `.github/workflows/validations.yml` |
| Miru Dockerfile uses pinned Ruby 4.0.9-slim (sha256), Node 24.22.1 (commit+sha256), pnpm 9.15.9, runs as UID/GID 1000 | VERIFIED | `Dockerfile` lines 10-11, 78-80, 89, 179-181 |

**Critical gaps requiring custom BIMSpend development (NEW DEVELOPMENT):**

1. Durable offline encrypted sync — Miru has no durable queue/ack/replay; only a `synced_at` timestamp in a JSON blob
2. Idempotent ingestion — Miru agent endpoint has no uniqueness constraint on `external_run_id`/`external_session_id`
3. Loaded internal labor cost model — Miru `ProfitabilityBillingRate` is billing rate only
4. Observed vs approved vs billed separation layer — BIMSpend-specific attribution
5. BIMSpend Windows adapter — integration layer (no upstream equivalent)
6. Read-only Revit connector — no upstream Revit integration

**Findings pending NVIDIA audit:**
- All ActivityWatch submodule implementation details at exact gitlinks (submodules uninitialized)
- Recursive submodule SHA equality vs PLAN audit "head observed" SHAs
- ActivityWatch port/bind defaults, privacy filters, payloads, packaging at exact gitlinks
- Clean Miru/ActivityWatch build success
- SBOM/license/CVE scan results

---

## 2. Investigated Questions and Resolved Issues

### 2.1 Miru agent timesheet idempotency (RESOLVED — gap confirmed)

**Question:** Does Miru's agent ingestion endpoint enforce idempotency on `external_run_id`/`external_session_id`?

**Investigation:** Read `app/controllers/api/v1/agent/timesheet_entries_controller.rb` (full, 47 lines) and `app/models/timesheet_entry.rb` (full, 241 lines).

**Finding:** CONFIRMED GAP. The `create` action (lines 4-23):
- Instantiates a new `timesheet_entry` with `external_run_id` and `external_session_id` from params
- Calls `timesheet_entry.save!` directly
- No `find_by`, `find_or_create_by`, or uniqueness check
- No uniqueness validation on `external_run_id` or `external_session_id` in the model (validations are: duration, work_date, bill_status, review_status, source, proof_url length, plus custom `validate_billable_project`, `validate_agent_belongs_to_workspace`)

**Verification procedure (proposed, not executed):**
```
git checkout 10e457e1d0cd2ac782be9d1edbcbd5a1a573486a
# Inspect:
cat app/controllers/api/v1/agent/timesheet_entries_controller.rb
cat app/models/timesheet_entry.rb | grep -n "external_run_id\|external_session_id\|uniqueness\|validates"
# Expected: no uniqueness validation on external_run_id/external_session_id
```

### 2.2 Miru offline synchronization (RESOLVED — gap confirmed)

**Question:** Does Miru have durable offline sync for desktop timer data?

**Investigation:** Read `app/models/desktop_current_timer.rb` (full, 9 lines) and `app/controllers/api/v1/desktop/current_timers_controller.rb` (full, 130 lines).

**Finding:** CONFIRMED LIMITED. The `DesktopCurrentTimer` model:
- `belongs_to :company`, `belongs_to :user`
- `validates :current_timer, presence: true`
- `validates :user_id, uniqueness: { scope: :company_id }`
- No `synced_at` attribute in model validations (it appears only in the controller's `DEFAULT_TIMER` hash and is set via `parsed_started_at` or `Time.current.iso8601(3)` on update)
- No durable queue, acknowledgement, replay, or encrypted storage
- `synced_at` is just a timestamp field in the persisted JSON blob, not a sync protocol

**Verification procedure (proposed, not executed):**
```
cat app/models/desktop_current_timer.rb
# Expected: no synced_at attribute, no sync protocol methods
```

### 2.3 Miru agent route rate limiting (RESOLVED — gap confirmed)

**Question:** Does Miru apply rate limiting to agent ingestion routes?

**Investigation:** Read `config/initializers/rack_attack.rb` (full, 79 lines).

**Finding:** CONFIRMED GAP. Rack::Attack throttles exist for:
- `auth/login/ip`, `auth/signup/ip`, `auth/native/google/ip`, `documents/review/ip`, `analytics/pdf/ip`, `reports/pdf/ip`, `invitations/resend/ip`, `invoice/checkout/ip`, `webhooks/paypal/ip`, `auth/recovery/ip`, `auth/otp/ip`

**No throttle exists for `/api/v1/agent/*` routes** (the agent timesheet ingestion endpoint). Agent keys are bearer tokens with no per-route rate limit.

**Verification procedure (proposed, not executed):**
```
cat config/initializers/rack_attack.rb | grep -n "agent"
# Expected: no matches for agent throttle
```

### 2.4 Miru billing rate vs loaded internal labor cost (RESOLVED — gap confirmed)

**Question:** Does Miru `ProfitabilityBillingRate` represent employer's loaded internal labor cost?

**Investigation:** Read `app/models/profitability_billing_rate.rb` (full, 20 lines).

**Finding:** CONFIRMED — it is a client billing/charge rate, NOT internal loaded cost:
- `billing_method: inclusion %w[hourly fixed_fee]`
- `hourly_rate` — client-facing charge rate
- `currency`, `effective_on`
- Validates user belongs to project workspace (`Employment.exists?`)
- No fields for employer overhead, benefits, payroll tax, or loaded cost calculation

**BIMSpend implication:** A new protected model for `internal_loaded_cost_rate` is required, separate from `standard_charge_rate`.

### 2.5 Miru agent capabilities scope (RESOLVED)

**Question:** What commands does Miru's agent capability endpoint expose?

**Investigation:** Read `app/controllers/api/v1/agent/capabilities_controller.rb` (full, 23 lines).

**Finding:** Exactly one command:
```json
{
  "name": "time create",
  "description": "Create a reviewable agent timesheet entry for the authenticated agent key",
  "requires_review": true,
  "supports_source_metadata": true,
  "supports_proof_metadata": true
}
```
No "time read", "time update", "project list", or "invoice" commands. Agent ingestion is write-only (timesheet_entries `create` only — routes line 154: `resources :timesheet_entries, only: [:create]`).

### 2.6 Miru agent key security (RESOLVED)

**Question:** What security properties does Miru's `AgentKey` have?

**Investigation:** Read `app/models/agent_key.rb` (full, 41 lines).

**Finding:**
- Token: `SecureRandom.hex(32)` (32 bytes, 64 hex chars)
- Storage: SHA-256 digest (`token_digest`), uniqueness validated
- Revocation: `revoked_at` timestamp, `active` scope filters `revoked_at: nil`
- Usage tracking: `last_used_at` updated on `authenticate`
- **No expiry**, **no rotation**, **no device binding**, **no scopes beyond agent/user/company**
- `authenticate` also checks `key.agent.backing_user_active_for_company?` (user must be employed at company)

### 2.7 Miru canonical CI/build commands (RESOLVED)

**Question:** What are Miru's canonical build/test/scan commands?

**Investigation:** Read `.github/workflows/validations.yml` (full, 299 lines) and `Dockerfile` (full, 195 lines).

**Finding — Canonical commands from pinned CI:**

| Stage | Command | Source |
|---|---|---|
| Ruby setup | `ruby-version: '4.0.9'`, `bundler: latest` | validations.yml lines 51-54 |
| Node setup | `node-version-file: .node-version` (24.22.1) | validations.yml lines 58-59 |
| pnpm setup | `pnpm/action-setup` v5, `run_install: false` | validations.yml lines 61-64 |
| pnpm install | `PUPPETEER_SKIP_DOWNLOAD=true pnpm install --frozen-lockfile` | validations.yml line 93 |
| Vite build | `timeout 180 bin/vite build` | validations.yml line 99 |
| Rubocop | `bundle exec rubocop` | validations.yml line 102 |
| Test DB setup | `bundle exec rake "parallel:create[2]" "parallel:load_schema[2]"` | validations.yml line 112 |
| CLI request specs | `bundle exec rspec spec/requests/api/v1/cli` | validations.yml line 116 |
| Parallel tests | `bin/parallel_test -n 2 --exclude-system` (PARALLEL_TEST_PROCESSORS: 2) | validations.yml lines 119-125 |
| System specs | `bundle exec rspec spec/system/responsive spec/system/expenses/crud_spec.rb spec/system/auth/two_factor_spec.rb` | validations.yml line 236 |
| bundler-audit | `bundle exec bundler-audit check --update` | validations.yml line 267 |
| Dependency audit | `node --test scripts/ci/dependency_security_test.mjs scripts/ci/dependency_audit_test.mjs` | validations.yml line 278 |
| Dependency audit (web/docs/mobile) | `node scripts/ci/dependency_audit.mjs` | validations.yml line 282 |
| ruby-audit | `bundle exec ruby-audit check` | validations.yml line 294 |
| brakeman | `bundle exec brakeman -q -w2` | validations.yml line 298 |
| DB | PostgreSQL 16 (docker image) | validations.yml lines 33-39 |

**Dockerfile:** Ruby 4.0.9-slim (`sha256:88f0d8f1f2f7829c8c85c5cfee774f7ac936a7ba460e904e8c873b6a7f96c311`), Node 24.22.1 (commit `9a3d479...`, sha256 `ff474d5...`), pnpm 9.15.9, runs as UID/GID 1000, `BUNDLE_WITHOUT="development:test"`, runtime image verified by `scripts/ci/verify_runtime_image.rb`.

### 2.8 ActivityWatch bundle structure and build (RESOLVED from README + Makefile)

**Question:** What is ActivityWatch's bundle structure and how is it built?

**Investigation:** Read `README.md` (full, 304 lines), `Makefile` (full, 360 lines), `pyproject.toml` (full, 38 lines), `.tool-versions` (full, 4 lines).

**Finding:**
- Bundle is a meta-package managed with `git submodule`; 11 submodules declared
- Two server implementations: `aw-server` (Python, current default) and `aw-server-rust` (Rust, planned future default)
- REST API (from README): Buckets API, Events API, Heartbeat API, Query API, Export (JSON) — all via `/api/0`
- Watchers: `aw-watcher-afk` (keyboard/mouse AFK), `aw-watcher-window` (active app + window title)
- Management: `aw-qt` (Qt) or `aw-tauri` (Tauri) manages `aw-server`; `aw-notify` queries server; `aw-sync` handles sync folder
- Frontend: `aw-webui` (separate project, NOT in submodules)
- Libraries: `aw-core` (core lib), `aw-client` (client wrappers)

**Makefile canonical targets:**
- `build`: iterates submodules, builds each (`make --directory=$module build`), builds aw-client, builds aw-core, verifies `aw_server.__version__`
- `test`: iterates testable submodules (`poetry run make test` or `make test`)
- `test-integration`: `pytest ./scripts/tests/integration_tests.py ./aw-server/tests/ -v`
- `test-query-parity`: `python3 -m pytest scripts/tests/query_parity -q -rfX -p no:cacheprovider`
- `lint`: iterates lintable submodules
- `typecheck`: iterates typecheckable submodules
- `package`: PyInstaller (`pyinstaller --clean --noconfirm aw.spec`) for non-Tauri; Tauri build script for Tauri
- `update`: `git submodule update --init --recursive` then `make build`
- `%/.git` target: `git submodule update --init --recursive`

**Prerequisites (`.tool-versions` + `pyproject.toml`):**
- Python 3.9.13, Poetry 1.5.1, Node.js 16.20.2, Rust nightly
- Dev deps: mypy, pytest, pytest-cov, pytest-benchmark, psutil, pywin32-ctypes (win32), pefile (win32)
- pyinstaller (*), pyinstaller-hooks-contrib (git master), setuptools >=78.1.1,<81

**IMPORTANT:** All ActivityWatch implementation details at exact gitlinks are NOT VERIFIED because submodules were not initialized (empty directories). The above is from README/Makefile/pyproject.toml at the bundle root only.

---

## 3. Architecture Boundary Confirmations

### 3.1 Miru as business/time-entry foundation (UNCHANGED)

Miru remains the system of record for companies, clients, projects, users, roles, timesheets, invoices, billing rates, reports, and export. BIMSpend integrates through Miru's existing API — no forking.

**Confirmed integration points (from source):**
- `POST /api/v1/agent/timesheet_entries` — agent ingestion (AgentKey bearer auth)
- `GET/POST /api/v1/timesheet_entry` — UI/API timesheet CRUD (policy-scoped)
- `GET/POST /api/v1/invoices` — invoicing with line items, taxes, payments
- `GET /api/v1/dashboard` — dashboard presenter
- `GET/POST /api/v1/reports/time_entries` (+ download CSV/PDF) — reporting
- `GET /api/v1/desktop/current_timers` (show/update) — current timer state
- `GET /api/v1/agent/capabilities` — agent capability negotiation
- `namespace :mcp` — Model Context Protocol endpoint
- `namespace :internal_api/v1` — canonical analytics backend

**Boundaries NOT to cross (B2-A scope):**
- No Miru source code modification
- No new Miru endpoints
- No database migration
- Integration via API configuration only

### 3.2 ActivityWatch as local collector (UNCHANGED)

ActivityWatch remains local-only, bound to loopback (port 5600 Python / 127.0.0.1 Rust). BIMSpend reads through the REST API via an adapter.

**Confirmed integration points (from README):**
- `aw-server /api/0` — Buckets, Events, Heartbeat, Query, Export APIs
- `aw-watcher-window` — active application + window title heartbeats
- `aw-watcher-afk` — active/inactive from keyboard/mouse input
- JSON export via web interface or REST API

**Boundaries NOT to cross (B2-A scope):**
- No ActivityWatch source modification
- No cloud exposure of aw-server
- No running watchers against real user session

### 3.3 BIMSpend Windows adapter (NEW DEVELOPMENT)

No upstream equivalent. Required capabilities:
- Read ActivityWatch local buckets (via REST API)
- Read Revit connector signals
- Correlate: Windows foreground + Revit process + active document + AFK state + mapping confidence
- Queue encrypted summaries/evidence
- Authenticate to Miru using revocable device/agent credential
- Implement offline queue/retry/idempotency
- Prevent double-counting across multiple Revit processes/documents

### 3.4 Revit connector (NEW DEVELOPMENT)

No upstream equivalent. Read-only, versioned (.NET 4.8 vs .NET 8), digitally signed.

**Confirmed Autodesk API events (from documentation):**
- `Application.DocumentOpened` — after document open completes
- `DocumentClosing/DocumentClosed`, save, reload/synchronization events
- `UIApplication.ViewActivated` — activated view/document
- `UIApplication.Idling` — safe callable state (NOT a productivity timer)
- `BasicFileInfo` — worksharing state, version, central path

---

## 4. Data Integrity — Confirmed Requirements

### 4.1 Idempotency requirements (gap confirmed)

| Requirement | Miru evidence | Status |
|---|---|---|
| Server-side uniqueness on external IDs | `external_run_id`/`external_session_id` fields exist on `TimesheetEntry`, but NO uniqueness validation | GAP — adapter must enforce |
| Replay safety | `save!` called directly, no find-or-create | GAP — adapter must enforce |
| Wrong-tenant rejection | `ProjectPolicy::Scope` resolves by company/user scope | PARTIAL — exists at API level |
| External ID binding | `agent_id`, `user_id`, `company` (through project/client) | PARTIAL — exists at model level |

### 4.2 Offline sync requirements (gap confirmed)

| Requirement | Miru evidence | Status |
|---|---|---|
| Durable local queue | `synced_at` exists only in controller DEFAULT_TIMER hash, not model attribute | GAP |
| Acknowledgement and replay | No sync protocol in `DesktopCurrentTimer` | GAP |
| Offline retry with bounded loss | Not present | GAP — adapter must implement |
| Encrypted local storage | Not present | GAP — adapter must implement |

### 4.3 Metric separation (observed vs approved vs billed)

| Metric | Definition | Upstream evidence | BIMSpend requirement |
|---|---|---|---|
| Observed activity | Measured foreground/window attention | ActivityWatch heartbeats (NOT VERIFIED at gitlinks) | Separate record; not productive effort |
| Attributed time | Activity correlated to project via Revit/AFK/process | New correlation layer | NEW BIMSPEND development |
| Approved time | Reviewed/approved timesheet entry | Miru `review_status: approved` | Existing; configure workflow |
| Billed hours | Invoiced quantity to client | Miru `Invoice`/`TimesheetEntry.bill_status: billed` | Preserve distinction; never auto-invoice from observed |

### 4.4 Billing rate vs loaded internal labor cost

| Concept | Miru evidence | Status |
|---|---|---|
| Standard charge rate (client price) | `ProfitabilityBillingRate.hourly_rate`, `billing_method: hourly/fixed_fee` | VERIFIED — billing/charge rate |
| Loaded internal labor cost (employer cost) | NOT present in Miru | GAP — new protected model required |

---

## 5. Licensing and Distribution Boundaries

| Component | License | Commercial implication | Status |
|---|---|---|---|
| Miru | MIT (Copyright Saeloun 2023) | Commercial modification/distribution allowed; retain copyright and permission notice | VERIFIED |
| ActivityWatch umbrella | MPL-2.0 | Commercial distribution allowed; covered modified files distributed in executable form must have corresponding source made available and notices preserved | VERIFIED |
| ActivityWatch submodules | Not consolidated | Recursive license/NOTICE and vendored-code inventory required at exact gitlinks | NOT VERIFIED (submodules uninitialized) |
| Miru third-party | Ruby gems, npm/pnpm packages | Each license enumerated from lockfiles; production clearance required | UNKNOWN |
| ActivityWatch third-party | Python, Python/Rust packages | Each license enumerated; MPL distribution obligations apply to covered files | UNKNOWN |
| Fonts/icons/images/assets | Various | Asset provenance and redistribution review | UNKNOWN |

**Distribution boundary guidance:**
- Miru (MIT): Configuring via API = no modification; forking = retain MIT notice
- ActivityWatch (MPL-2.0): Prefer unmodified local ActivityWatch + separate adapter; if modifying covered files and distributing, publish corresponding source
- Combined stack: Keep MPL component separable from proprietary adapter; legal review before distribution
- Trademarks/branding: Not granted by code licenses; separate clearance required

**Questions requiring legal review:**
- MPL-2.0 distribution obligations for ActivityWatch submodules bundled with proprietary adapter
- GPL/AGPL dependency surprise in transitive packages
- Australian employment/privacy law for workplace monitoring
- Trademark clearance for reuse of upstream names/logos

---

## 6. Security Findings (source-confirmed)

| Finding | Severity | Evidence |
|---|---|---|
| No agent-route rate limiting | High | `rack_attack.rb` — no throttle for `/api/v1/agent/*` |
| Agent token: bearer, no expiry, no rotation, no device binding | High | `agent_key.rb` — 32-byte token, SHA-256 digest, `revoked_at`, `last_used_at` only |
| No agent-specific scope beyond agent/user/company | High | `agent_key.rb` — `active` scope checks `revoked_at: nil` and employed user |
| No idempotency constraint on external IDs | High | `timesheet_entries_controller.rb` — `save!` directly, no uniqueness check |
| Proof URL validation length-only | Medium | `timesheet_entry.rb` — `validates :proof_url, length: { maximum: 2000 }`, SSRF exposure NOT VERIFIED |
| Application-level tenancy only (not row-level) | High | PLAN audit §3.2 — cross-tenant security tests NOT VERIFIED |
| ActivityWatch evidence treated as untrusted | High | PLAN audit §4.2 — local API not penetration-tested |
| Raw window titles may contain sensitive text | Critical | PLAN audit §4.3 — model, customer, email, document text possible |

**Required controls (proposed, not executed):**
- OS credential protection, rotation/revocation, short device identity, TLS, rate limits, anomaly logs
- Server idempotency key/unique constraint and replay tests
- Treat ActivityWatch events as untrusted; correlate Revit/AFK/process; review before approval
- Local allowlist/redaction; never collect keystrokes/screenshots; minimize and hash; retention limits
- Secret scanning before commit; synthetic fixtures only

---

## 7. Reproducibility and SBOM/License Tooling (proposed, not executed)

| Category | Recommended tool | Version policy | Source |
|---|---|---|---|
| Ruby SBOM/license | bundler-audit | Pin exact version; verify exists before run | Declared in Gemfile (`require: false`) |
| Ruby static security | Brakeman | Pin exact version | Declared in Gemfile (`require: false`) |
| Ruby CVE audit | ruby-audit | Pin exact version | Declared in Gemfile (`require: false`) |
| JavaScript/Node SBOM | From pnpm-lock.yaml + ecosystem scanner | Pin exact version | Miru frontend deps |
| Python SBOM/license | From poetry.lock + ecosystem scanner | Pin exact version | ActivityWatch Python deps |
| Rust SBOM/license | cargo audit / cargo-deny | Pin exact version | ActivityWatch Rust deps |
| Container/OS SBOM | From Dockerfile base image digest | Pin image digest | `sha256:88f0d8f...` |
| Combined SBOM format | CycloneDX or SPDX | Pin format and tool | Machine-readable, auditable |
| Secret scanning | Pre-commit/secret scanner | Pin exact version | Prevent secrets in logs/repo |

**Corrections to OpenCode plan (per Work review):**
- `bundle licenses` is NOT a standard Bundler command — select and pin an approved Ruby license/SBOM tool
- Lockfiles are INPUTS, not SBOM/license output — generate CycloneDX/SPDX, preserve manifest hashes
- `|| true` masks failures — capture exit code/stdout/stderr explicitly
- `bundle exec rails spec` not established as Miru test runner — CI uses `bin/parallel_test -n 2 --exclude-system` and `bundle exec rspec spec/requests/api/v1/cli`
- ActivityWatch `make` "or equivalent" not reproducible — use exact upstream targets from pinned Makefile
- Install runtimes in disposable VM/container/managed runner — NOT on user's normal workstation

---

## 8. Windows/Linux Validation Matrix

| Aspect | Linux/container | Windows | Notes |
|---|---|---|---|
| Miru build | Supported (Ruby + Node + PostgreSQL) | Partially (Ruby on Windows via installer; PostgreSQL) | Miru targets Linux/container via Kamal/Docker |
| Miru test suite | CI-runnable (ubuntu-latest) | Not established | Confirm from pinned CI |
| ActivityWatch Python server | Supported | Supported (pywin32-ctypes, pefile win32 deps) | Python 3.9.x required |
| ActivityWatch Rust server | Supported | Supported (Rust nightly) | Rust nightly toolchain required |
| ActivityWatch watchers | Limited (no win32-specific) | Full (window, AFK, input) | Windows-specific integration risks |
| ActivityWatch packaging (PyInstaller) | Supported | Supported | Windows MSI/registry described |
| ActivityWatch loopback bind | localhost:5600 / 127.0.0.1 | Same | Never expose to LAN/internet |
| Revit connector | N/A | Windows only (.NET 4.8 or .NET 8) | Revit is Windows-only; version-specific signed builds |
| BIMSpend adapter | N/A | Windows | Local Windows adapter/agent |

**Supported environments for B2-A:**
- Disposable Linux/container VM — YES (Miru primary target; reproducible)
- Disposable Windows VM — YES (if in approved matrix; required to validate Windows packaging/watchers)
- User's normal workstation — NO (must not install runtimes/toolchains or run watchers against real session)
- Production environment — NO (B2-A is isolated baseline only)

**Windows-specific integration risks:**
| Risk | Severity | Mitigation |
|---|---|---|
| Revit version fragmentation (.NET 4.8 vs .NET 8) | High | Separate signed binaries per era; multi-targeting |
| Revit UI slowdown/crash from Idling handlers | High | Read-only handlers, bounded payload, latency tests, kill switch |
| Unsigned Revit add-in trust prompts | High | Code-sign binaries and installer; trusted publisher |
| Multiple Revit processes/documents double-counting | High | Adapter correlation; process/session IDs; foreground-only |
| Watcher restarts, sleep, RDP, lock screen, UAC | Medium | Explicit tests; window focus != productive time |
| Window titles exposing sensitive text | Critical | Local allowlist/redaction; no keystrokes/screenshots |
| ActivityWatch exposed to LAN/internet | Critical | Loopback bind only |
| Installing on user's workstation | Critical | Disposable VM/container/managed runner only |

---

## 9. Corrected B2-A Execution Procedure (proposed, not executed)

**Stage 0 — Approval and immutable run manifest:**
- Record human approval reference, executor ID/image digest, branch, operator, UTC timestamp, scope
- Record exact upstream SHAs and tool/scanner versions
- Confirm synthetic configuration and network/evidence policies

**Stage 1 — Clean isolated checkout (disposable workspace):**
```
git clone https://github.com/saeloun/miru-web.git b2a-miru
cd b2a-miru
git checkout 10e457e1d0cd2ac782be9d1edbcbd5a1a573486a

git clone https://github.com/ActivityWatch/activitywatch.git b2a-activitywatch
cd b2a-activitywatch
git checkout 9fee4702fea08dbe0149cc6e28f4ef66b49f54ec
git submodule update --init --recursive
git status --short
git rev-parse HEAD
git submodule status --recursive
```

**Stage 2 — Pre-build inventory (before installing):**
- Enumerate all license/NOTICE files, vendored code, assets
- Generate source/manifest hashes
- Generate ecosystem SBOMs with pinned tools
- Record every external download and resolved dependency
- STOP for unknown/unlicensed component or prohibited license

**Stage 3 — Miru baseline (disposable executor, not user's machine):**
- Use exact runtime versions from pinned source (Ruby 4.0.9, Node 24.22.1, pnpm)
- Follow pinned upstream CI/build documentation (`.github/workflows/validations.yml`)
- Prepare only synthetic database/configuration (PostgreSQL 16)
- Run dependency resolution, asset build, database preparation, canonical test suites
- Run pinned Ruby/JavaScript/container security checks
- Capture command, duration, exit code, stdout/stderr, artifact hashes

**Stage 4 — ActivityWatch baseline:**
- Follow pinned bundle's platform-specific documented build target (Makefile)
- Build/test exact recursive gitlinks (not current component branch heads)
- Run Python/Rust/JavaScript dependency, license, vulnerability checks
- On Windows, validate packaging only if Windows explicitly in approved matrix
- Do NOT start watchers against real user session
- Capture same structured evidence as Miru

**Stage 5 — Reproducibility check:**
- Repeat critical build in second clean instance OR document why not established
- Compare dependency locks, SBOMs, artifact hashes where deterministic
- Mark nondeterministic differences and root causes

**Stage 6 — Evidence review and teardown:**
- Redact secrets/personal paths without altering pass/fail results
- Commit only approved text/machine-readable evidence and checksums to separate execution branch
- Verify remote commit/file list
- Destroy disposable environment; verify teardown
- Produce B2-A stop/go recommendation

---

## 10. Verified Facts vs Assumptions vs Unresolved Questions

### 10.1 Verified facts (source-confirmed)

| Fact | Source |
|---|---|
| Miru pinned commit `10e457e1...` exists on `develop` | Local clone + Work review |
| ActivityWatch bundle pinned commit `9fee4702...` exists on `master` | Local clone + Work review |
| All 11 ActivityWatch submodule gitlink commit objects exist in remotes | Work review independent check |
| Miru agent endpoint has NO idempotency check on external IDs | Source read: `timesheet_entries_controller.rb` |
| Miru `DesktopCurrentTimer` has no `synced_at` model attribute | Source read: `desktop_current_timer.rb` |
| Miru `rack_attack.rb` has NO agent-route throttle | Source read: `rack_attack.rb` |
| Miru `ProfitabilityBillingRate` is billing rate only | Source read: `profitability_billing_rate.rb` |
| Miru agent capabilities = one command ("time create") | Source read: `capabilities_controller.rb` |
| Miru `AgentKey` = 32-byte token, SHA-256, revoked_at, no expiry | Source read: `agent_key.rb` |
| ActivityWatch bundle = 11 submodules, uninitialized | Source read: `.gitmodules`, `git submodule status` |
| ActivityWatch two servers (Python default, Rust planned) | Source read: `README.md` |
| Miru CI commands from validations.yml | Source read: `.github/workflows/validations.yml` |
| Miru Dockerfile pinned images + UID/GID 1000 | Source read: `Dockerfile` |

### 10.2 Assumptions (reasoned but not source-confirmed)

| Assumption | Basis | Risk if wrong |
|---|---|---|
| ActivityWatch local API endpoints at bundle gitlinks match README description | README describes API conceptually | Endpoints may differ at exact gitlinks |
| ActivityWatch Python server binds to localhost:5600 | README states this | May differ at exact gitlinks/submodules |
| Miru can build on disposable Linux/container | CI runs on ubuntu-latest | Environment-specific failures possible |
| ActivityWatch can build with pinned Python 3.9.13/Poetry 1.5.1 | `.tool-versions` specifies these | Version conflicts possible |

### 10.3 Unresolved questions (pending NVIDIA audit or B2-A execution)

| Question | Why unresolved | Pending on |
|---|---|---|
| ActivityWatch submodule implementation at exact gitlinks | Submodules not initialized (empty dirs) | B2-A execution (recursive init) |
| Recursive submodule SHA equality vs PLAN audit "head observed" | Not validated | B2-A execution |
| ActivityWatch port/bind defaults, privacy filters, payloads, packaging at gitlinks | Requires source inspection | B2-A execution |
| Clean Miru/ActivityWatch build success | No builds executed | B2-A execution |
| SBOM/license/CVE scan results | No scans executed | B2-A execution |
| ActivityWatch window/AFK implementation at exact gitlinks | Requires source inspection | B2-A execution / NVIDIA audit |
| Cross-tenant security at runtime | Not tested | B3-B / NVIDIA audit |
| Agent token behavior under attack | Not tested | B3-B / NVIDIA audit |
| Loaded internal labor cost model design | Not in Miru | BIMSpend domain design (post-B2-A) |

---

## 11. Recommendations and Acceptance Criteria

### 11.1 Technical recommendations (prioritized)

| Priority | Recommendation | Rationale |
|---|---|---|
| 1 | Configure Miru agent + AgentKey through API (no Miru code changes) | Strongest reuse; existing ingestion boundary |
| 2 | Implement BIMSpend adapter with idempotency on `external_run_id`/`external_session_id` | Confirmed gap in Miru |
| 3 | Implement durable offline encrypted sync in adapter | Confirmed gap in Miru |
| 4 | Add agent-route rate limiting (adapter or Miru config) | Confirmed gap in rack_attack |
| 5 | Separate `internal_loaded_cost_rate` model from `standard_charge_rate` | Confirmed gap in ProfitabilityBillingRate |
| 6 | Keep ActivityWatch local-only, loopback bind, redact titles locally | Confirmed architecture boundary |
| 7 | Read-only Revit connector, versioned (.NET 4.8/.NET 8), digitally signed | No upstream equivalent |
| 8 | CycloneDX/SPDX SBOM + license inventory at B2-A | Required for MPL-2.0 compliance |

### 11.2 B2-A acceptance criteria (from PLAN audit §9, corrected)

- [ ] Explicit user approval for B2-A exists
- [ ] Approved disposable executor and immutable environment manifest exist
- [ ] Primary and recursive SHAs captured and match pinned bundle
- [ ] Canonical upstream build/test commands identified from pinned source (validations.yml + Makefile)
- [ ] Miru baseline build and required tests complete with recorded exit codes
- [ ] ActivityWatch baseline build and required tests complete for approved platform matrix
- [ ] SBOMs cover Ruby, JavaScript, Python, Rust, OS/container packages, bundled assets
- [ ] Licenses/notices enumerated and reviewed against explicit policy
- [ ] Security scans versioned, fresh, include failures (bundler-audit, brakeman, ruby-audit, dependency audit)
- [ ] No secrets, confidential data, or identifiable user activity captured
- [ ] Evidence sufficient to repeat run from clean executor
- [ ] Second clean-run check establishes or explicitly rejects reproducibility
- [ ] Teardown verified
- [ ] No product code, FBT Revit Academy, `main`, B2-B, or B3 changed

**A partial pass must be reported as partial; it cannot be silently upgraded to GO.**

---

## 12. GO/BLOCKED Recommendation

**BLOCKED** — Gate B2-A remains blocked pending explicit user approval. This parallel research report confirms and narrows the technical gaps identified in prior reports using direct source-code inspection, but no builds, tests, scans, or installations have been executed.

**Immediate unblockers (require human decision):**
1. Explicit user approval for Gate B2-A execution
2. Approved disposable executor/platform matrix (Linux/container, Windows, or both)
3. Pinned SBOM/scanner toolchain with license and vulnerability decision policies
4. Resolution of ActivityWatch submodule implementation uncertainty (requires B2-A execution)

**Passing B2-A does NOT approve B2-B, B3, production use, or deployment.** A separate human decision is required after completed B2-A evidence.

---

**END OF REPORT — B2-A REMAINS BLOCKED**
