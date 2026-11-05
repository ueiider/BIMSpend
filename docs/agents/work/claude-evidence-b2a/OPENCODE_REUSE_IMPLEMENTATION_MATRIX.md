# BIMSpend — Reuse Implementation Matrix

**Mode:** READ-ONLY RESEARCH. No application code changes, no builds, no dependency installation.  
**Branch:** `agent/opencode-reuse-matrix` (created from `main` at `eb13fc9`)  
**Repository:** https://github.com/ueiider/BIMSpend  
**Pinned upstream revisions verified against local clones:**

| Component | Pinned SHA | Branch | Local clone path | Verified |
|---|---|---|---|---|
| Miru | `10e457e1d0cd2ac782be9d1edbcbd5a1a573486a` | `develop` | `D:\BIMSpend\Research\Repos\miru-web` | YES |
| ActivityWatch bundle | `9fee4702fea08dbe0149cc6e28f4ef66b49f54ec` | `master` | `D:\BIMSpend\Research\Repos\activitywatch` | YES |

**Important limitation:** ActivityWatch submodules are **not initialized** (all 11 submodule directories empty on disk; `git submodule status` shows `-` prefix). ActivityWatch source files (aw-server, aw-watcher-window, aw-watcher-afk, aw-client, etc.) could **not** be read directly. ActivityWatch findings below are inferred from the root `README.md` architecture section and submodule names/gitlinks only, and are marked **NOT VERIFIED** where implementation detail is asserted.

**Gate status:** B2-A remains BLOCKED pending explicit user approval. This report is research only; no implementation approved.

---

## 1. Executive Summary

BIMSpend's recommended architecture is **composition, not merger**: Miru as the business/time-entry foundation, ActivityWatch as a local Windows activity collector behind localhost, a small BIMSpend Windows adapter as the integration layer, and a read-only Revit connector emitting document/session signals.

This matrix classifies every BIMSpend capability against Miru and ActivityWatch source inspected at the pinned commits. The strongest reuse finding is Miru's dedicated **agent ingestion boundary** (`POST /api/v1/agent/timesheet_entries`, `AgentKey` bearer auth, company-scoped tenancy), which BIMSpend should configure and adapt rather than rebuild. ActivityWatch provides local window/AFK heartbeats via its local REST API but its source code was not directly inspectable (submodules uninitialized). The Revit connector and BIMSpend adapter have **no upstream equivalent** and require new BIMSpend development.

**Highest-value reuse opportunities:**
1. Miru agent timesheet ingestion API — automated draft time entry with proof metadata and external run/session IDs.
2. Miru company/project/timesheet tenancy — company-scoped access control with Pundit + Rolify policies.
3. Miru invoice + profitability billing rate models — standard rate and labor cost tracking.
4. ActivityWatch local window + AFK heartbeats — observed attention signals (local API only).
5. Miru CSV/PDF time-entry export — data export pathway.

**Critical gaps requiring custom code (NEW BIMSPEND DEVELOPMENT):**
1. BIMSpend Windows adapter/agent — integration layer between ActivityWatch, Revit connector, and Miru.
2. Read-only Revit connector — document/view/session identity signals.
3. Model-to-commercial-project mapping — admin mapping + confidence workflow.
4. Observed-activity vs approved-time vs billed-hours separation layer.
5. Revit version-specific builds (.NET Framework 4.8 vs .NET 8).

---

## 2. Verified Evidence (source inspected at pinned commits)

### 2.1 Miru — source files read directly

All paths below were read from `D:\BIMSpend\Research\Repos\miru-web` at commit `10e457e1d0cd2ac782be9d1edbcbd5a1a573486a`.

| Capability | File path | Key classes / functions | Existing behavior |
|---|---|---|---|
| User authentication | `app/models/user.rb` | `User` (Devise, JTIMatcher, TOTP, passkeys, WebAuthn, pwned_password) | Devise session/JWT auth, MFA, OAuth, compromised-password checks |
| | `app/controllers/api/v1/users/sessions_controller.rb` | `login`, `logout`, `_me` | Session create/destroy, current user |
| | `app/controllers/api/v1/users/registrations_controller.rb` | `signup` | User registration |
| | `app/controllers/api/v1/users/passwords_controller.rb` | `forgot_password`, `reset_password` | Password reset |
| | `app/controllers/api/v1/users/otps_controller.rb` | `request`, `verify` | OTP request/verify |
| | `app/controllers/api/v1/users/passkeys_controller.rb` | passkey CRUD | WebAuthn passkey management |
| | `app/controllers/api/v1/users/totp_controller.rb` | TOTP setup/confirm/authenticate | TOTP management |
| Agent/device credentials | `app/models/agent_key.rb` | `AgentKey.authenticate`, `issue_for`, `revoke!`, `digest` | 32-byte random token, SHA-256 digest, revocable, bound to agent/user/company |
| | `app/models/agent.rb` | `Agent` (providers: custom/claude/codex/openclaw), `backing_user_active_for_company?` | Agent bound to company+user, default project, active scope |
| | `app/controllers/api/v1/agent/base_controller.rb` | `authenticate_agent_key!`, `set_agent_current_details!`, `bearer_token` | Bearer AgentKey auth, signs in bound user, sets company context |
| | `app/controllers/api/v1/agent/capabilities_controller.rb` | capabilities endpoint | Agent capability negotiation |
| Timesheet ingestion (agent) | `app/controllers/api/v1/agent/timesheet_entries_controller.rb` | `create`, `project`, `agent_timesheet_entry_params` | Creates draft timesheet_entry with `source: "automation"`, `external_run_id`, `external_session_id`, `proof_url`, `source_metadata`, `proof_metadata`; binds to agent's company/project/user |
| Timesheet model | `app/models/timesheet_entry.rb` | `TimesheetEntry` (bill_status enum: non_billable/unbilled/billed; review_status enum: not_required/pending_review/approved/rejected; SOURCES: manual/cli/mcp/automation/import) | Audited duration/work_date/note/bill_status/review_status/project_id/user_id/agent_id/source/proof fields; `has_one :invoice_line_item`; `belongs_to :user, :project, :agent` |
| Timesheet policy | `app/policies/timesheet_entry_policy.rb` | `TimesheetEntryPolicy` (show/index/create/update/destroy, Scope) | Owner/admin/employee can view/create; update blocked if billed or stale; privileged roles can update any |
| Companies/tenancy | `app/models/company.rb` | `Company` (employments, users through employments, clients, projects, timesheet_entries through clients, invoices) | Multi-tenancy via company; audited financial fields; subscription/trial fields |
| | `app/controllers/api/v1/companies_controller.rb` | `CompaniesController` | Company CRUD |
| | `app/policies/company_policy.rb` | `CompanyPolicy` | Company access control |
| Projects | `app/models/project.rb` | `Project` (belongs_to client, has_one company through client, timesheet_entries, project_members, profitability_billing_rates, expenses; billable boolean) | Project scoped to client/company; searchable; audited |
| | `app/controllers/api/v1/projects_controller.rb` | `ProjectsController` | Project CRUD |
| | `app/policies/project_policy.rb` | `ProjectPolicy` (Scope resolves projects by company or user membership) | Owner/admin see all company projects; employees see assigned projects |
| | `app/models/project_member.rb` | `ProjectMember` | User-project membership |
| Roles/Permissions | `app/models/role.rb` | `Role` (Rolify scopify, polymorphic resource, has_and_belongs_to_many users via users_roles) | Role-based access control |
| | `app/policies/application_policy.rb` | `ApplicationPolicy` | Base Pundit policy |
| | `app/policies/*` (40+ policy files) | Per-resource policies (timesheet_entry, project, invoice, dashboard, report, etc.) | Granular authorization |
| Time tracking (desktop) | `app/controllers/api/v1/desktop/current_timers_controller.rb` | `DesktopCurrentTimersController` (show/update; DEFAULT_TIMER schema; synced_at field) | Per-user/current-company current timer record with elapsed_ms, running, project_name, task_name, source, synced_at |
| | `app/models/desktop_current_timer.rb` | `DesktopCurrentTimer` (belongs_to company/user; current_timer attribute; uniqueness user_id scoped to company_id) | Persisted current timer state |
| | `app/controllers/api/v1/time_tracking_controller.rb` | `TimeTrackingController` (index with date range; set_user by role) | Time tracking index view (clients, employees, entries, projects, holidays) |
| Timesheet entry (UI/API) | `app/controllers/api/v1/timesheet_entry_controller.rb` | `index`, `create`, `update`, `destroy` | Policy-scoped timesheet entry CRUD; owner/admin can select any user |
| Reports | `app/controllers/api/v1/reports/time_entries_controller.rb` | `index`, `download` (CSV/PDF) | Time-entry report service; CSV/PDF export |
| | `app/controllers/api/v1/reports/client_revenues_controller.rb` | client revenues report | Revenue by client |
| | `app/controllers/api/v1/reports/accounts_aging_controller.rb` | accounts aging | Aging report |
| | `app/controllers/api/v1/reports/payments_controller.rb` | payments report | Payment report |
| | `app/controllers/api/v1/reports/outstanding_overdue_invoices_controller.rb` | outstanding/overdue | Overdue invoice report |
| | `app/policies/dashboard_policy.rb`, `app/policies/report_policy.rb` | Dashboard/Report policies | Dashboard/report authorization |
| Dashboard | `app/controllers/api/v1/dashboard_controller.rb` | `DashboardController` (index with timeframe; DashboardPresenter) | Dashboard presenter with stats, currency meta |
| Billing/labor costs | `app/models/invoice.rb` | `Invoice` (status: draft/sent/viewed/paid/declined/overdue/sending/waived; amount, base_currency_amount, exchange_rate, currency, amount_paid, amount_due; invoice_line_items, invoice_taxes, payments) | Invoicing with audit, Stripe/Razorpay/PayPal payment infos |
| | `app/models/profitability_billing_rate.rb` | `ProfitabilityBillingRate` (billing_method: hourly/fixed_fee; hourly_rate; currency; effective_on; belongs_to project/user) | Per-project/user billing rate with validation |
| | `app/models/invoice_line_item.rb` | `InvoiceLineItem` | Invoice line items |
| | `app/models/invoice_line_item_time_entry.rb` | `InvoiceLineItemTimeEntry` | Links line items to time entries |
| | `app/models/expense.rb` | `Expense` (status: submitted/approved/rejected/paid; expense_type: personal/business; receipts) | Expense approval workflow |
| | `app/policies/invoice_policy.rb`, `app/policies/expense_policy.rb` | Invoice/Expense policies | Billing authorization |
| API integration | `config/routes/api.rb` | `namespace :api, namespace :v1` | Versioned JSON API; agent namespace, desktop namespace, CLI namespace, mobile namespace, reports, invoices, projects, clients, users |
| | `app/controllers/api/v1/mcp_controller.rb` | `McpController` | Model Context Protocol endpoint |
| | `app/controllers/api/v1/integrations/quickbooks_controller.rb` | QuickBooks integration | External accounting integration |
| Offline sync | `app/models/desktop_current_timer.rb` | `synced_at` field | Timer sync timestamp |
| | `app/controllers/api/v1/desktop/current_timers_controller.rb` | `update` (sanitized_current_timer) | Timer update with sync fields |
| Data export | `app/controllers/api/v1/reports/time_entries_controller.rb` | `download` (CSV/PDF) | CSV and PDF export of time entries |
| | `app/controllers/internal_api/v1/analytics_exports_controller.rb` | analytics exports | Internal analytics export |
| | `app/controllers/api/v1/invoices/bulk_download_controller.rb` | bulk download | Bulk invoice download |

**Gemfile dependencies observed** (`Gemfile` at pinned commit): Ruby 4.0.9, Rails ~8.1.4, PostgreSQL (`pg`), Puma/Falcon, Devise + Devise Security + Devise Pwned Password + Devise JWT + Devise Invitable, WebAuthn, ROTP, Rolify (implied by `Rolify.resource_types` in role.rb), Pundit (implied by policies), Audited (`audited` on models), Money (`money`), Ahoy (`ahoy_matey`), Brakeman, Solid Cache/Cable, Vite, Propshaft, Kamal, Docker.

### 2.2 ActivityWatch — source NOT directly readable (submodules uninitialized)

ActivityWatch submodule directories are empty on disk. The following is inferred from `README.md` architecture section and `.gitmodules` only, marked **NOT VERIFIED** for implementation detail.

| Capability | Inferred source (submodule) | Key components | Existing behavior (README-described, NOT VERIFIED from source) |
|---|---|---|---|
| Activity monitoring | `aw-server` (Python, gitlink `67cfb479`) or `aw-server-rust` (Rust, gitlink `fe558c4f`) | REST API, datastore, query engine, buckets, events | Local-first event storage; Buckets/Events/Heartbeat/Query/Export API |
| | `aw-client` (gitlink `fe106969`) | API client wrappers | Client library to query aw-server |
| Windows app detection | `aw-watcher-window` (gitlink `10638b2c`) | `aw_watcher_window/main.py`, `privacy_filter.py` | Emits `app` and `title` heartbeats for active window |
| Idle/AFK detection | `aw-watcher-afk` (gitlink `b4839261`) | `aw_watcher_afk/afk.py` | Emits `afk` / `not-afk` from keyboard/mouse input |
| | `aw-watcher-input` (gitlink `4e6461db`) | input watcher | Keyboard/mouse activity (underlies AFK) |
| Local API | `aw-server` / `aw-server-rust` | `/api/0` endpoints | Buckets API, Events API, Heartbeat API, Query API, JSON export |
| Storage | `aw-core` (gitlink `28c3acf0`) | buckets, events | Local timeseries storage organized in buckets |
| Desktop manager | `aw-qt` (gitlink `bbccb715`) | Qt manager | Starts/stops aw-server, aw-notify, watchers |
| Desktop shell | `aw-tauri` (gitlink `44b92d45`) | Tauri app | Desktop application shell |
| Sync | `aw-sync` (in aw-server-rust) | sync folder | Push/pull sync folder |
| Notify | `aw-notify` (gitlink `87e83cca`) | notifications | Notification subsystem |
| Legacy | `awatcher` (gitlink `c32ca62c`) | legacy tool | Unverified |

**Prerequisites observed** (`.tool-versions`, `pyproject.toml`): Python 3.9.13, Poetry 1.5.1, Node.js 16.20.2, Rust nightly, PyInstaller, pywin32-ctypes/pefile (win32), setuptools >=78.1.1,<81.

---

## 3. Environment Inventory

### 3.1 Local machine prerequisites (read-only inspection, not installed)

| Prerequisite | Required by | Observed version | Status |
|---|---|---|---|
| Ruby | Miru | Not installed | MISSING |
| Bundler | Miru | Not installed | MISSING |
| Node.js | Miru + ActivityWatch | v24.22.1 | INSTALLED |
| npm | Miru + ActivityWatch | 11.19.1 | INSTALLED |
| pnpm | Miru | Not installed | MISSING |
| PostgreSQL | Miru | Not installed (`psql` not found) | MISSING |
| Python | ActivityWatch | 3.12.10 | INSTALLED (version mismatch: needs 3.9.x) |
| Poetry | ActivityWatch | Not installed | MISSING |
| Rust / Cargo | ActivityWatch | 1.97.0 | INSTALLED (needs nightly) |
| Docker | Miru (Kamal) | Not installed | MISSING |
| Disk space (D:) | Both | ~1.95 TB free | SUFFICIENT |

### 3.2 Upstream prerequisite versions (from pinned source files)

| Component | Ruby | Node | Python | Rust | Database | Package managers |
|---|---|---|---|---|---|---|
| Miru | 4.0.9 (`.ruby-version`) | 24.22.1 (`.node-version`, `.nvmrc`) | N/A | N/A | PostgreSQL | Bundler, pnpm |
| ActivityWatch | N/A | 16.20.2 (`.tool-versions`) | 3.9.13 (`.tool-versions`) | nightly (`.tool-versions`) | N/A (SQLite/JSON buckets) | Poetry, PyInstaller |

---

## 4. Missing Prerequisites

| Prerequisite | Needed for | Status | Action (not executed per B2-A rules) |
|---|---|---|---|
| Ruby 4.0.9 + Bundler | Miru build/test | NOT INSTALLED | Install via RVM/rbenv + bundler gem |
| Node.js 24.22.1 + pnpm | Miru frontend | pnpm NOT INSTALLED | Install pnpm via npm/corepack |
| PostgreSQL server | Miru database | NOT INSTALLED | Install PostgreSQL, create database |
| Python 3.9.x + Poetry | ActivityWatch | Poetry NOT INSTALLED; Python 3.12.10 (version mismatch) | Install Poetry; consider Python 3.9 via pyenv |
| Rust nightly toolchain | ActivityWatch (Rust server) | Rust 1.97.0 stable (nightly needed) | Install rustup nightly |
| Docker | Miru Kamal deployment | NOT INSTALLED | Install Docker Desktop |
| ActivityWatch submodules | ActivityWatch source | NOT INITIALIZED (empty dirs) | `git submodule update --init --recursive` |

---

## 5. Reuse Classification Matrix

Classification scale:
- **A = REUSE AS-IS** — upstream capability satisfies BIMSneed with minimal or no changes
- **B = REUSE WITH CONFIGURATION** — upstream capability needs configuration/data mapping but not code changes
- **C = EXTEND EXISTING CODE** — upstream code is the base; BIMSpend adds fields/endpoints/logic
- **D = NEW BIMSPEND DEVELOPMENT** — no upstream equivalent; BIMSpend builds it
- **E = NOT VERIFIED** — cannot confirm from inspected source

| # | BIMSpend capability | Classification | Miru evidence | ActivityWatch evidence | Confidence |
|---|---|---|---|---|---|
| 1 | User authentication | C (Extend) | `app/models/user.rb` (Devise+JWT+passkeys+TOTP+WebAuthn), `app/controllers/api/v1/users/*`, `Gemfile` (devise, devise-jwt, webauthn, rotp) | N/A | High |
| 2 | Agent/device credentials | C (Extend) | `app/models/agent_key.rb` (issue_for/authenticate/revoke, SHA-256 digest), `app/models/agent.rb`, `app/controllers/api/v1/agent/base_controller.rb` | N/A | High |
| 3 | Roles and permissions | B (Configure) | `app/models/role.rb` (Rolify), `app/policies/*` (40+ Pundit policies), `app/policies/application_policy.rb` | N/A | High |
| 4 | Companies and organizations | A (As-Is) | `app/models/company.rb` (employments, users through employments, clients, projects, invoices), `app/controllers/api/v1/companies_controller.rb` | N/A | High |
| 5 | Project management | A (As-Is) | `app/models/project.rb` (client, company, timesheet_entries, project_members, profitability_billing_rates, billable flag), `app/controllers/api/v1/projects_controller.rb`, `app/policies/project_policy.rb` | N/A | High |
| 6 | Timesheet management | C (Extend) | `app/models/timesheet_entry.rb` (bill_status, review_status, source/proof metadata, agent_id, invoice_line_item), `app/controllers/api/v1/timesheet_entry_controller.rb`, `app/policies/timesheet_entry_policy.rb` | N/A | High |
| 7 | Approval workflows | B (Configure) | `app/models/expense.rb` (status: submitted/approved/rejected/paid), `app/policies/expense_policy.rb`; `TimesheetEntry.review_status` (pending_review/approved/rejected) | N/A | Medium |
| 8 | Time tracking | C (Extend) | `app/controllers/api/v1/desktop/current_timers_controller.rb` (elapsed_ms, running, synced_at), `app/models/desktop_current_timer.rb`, `app/controllers/api/v1/time_tracking_controller.rb` | N/A | High |
| 9 | Activity monitoring | C (Extend) | N/A | `aw-server` local API (buckets/events/heartbeat), `aw-client` wrappers | Medium (NOT VERIFIED from source) |
| 10 | Windows application detection | C (Extend) | N/A | `aw-watcher-window` (app + title heartbeats, privacy_filter.py) | Medium (NOT VERIFIED from source) |
| 11 | Idle/AFK detection | C (Extend) | N/A | `aw-watcher-afk` (afk/not-afk from keyboard/mouse), `aw-watcher-input` | Medium (NOT VERIFIED from source) |
| 12 | Reports and dashboards | B (Configure) | `app/controllers/api/v1/dashboard_controller.rb` (DashboardPresenter), `app/controllers/api/v1/reports/*` (time_entries, client_revenues, accounts_aging, payments, overdue), CSV/PDF export | N/A | High |
| 13 | Billing and labor costs | C (Extend) | `app/models/invoice.rb` (status, amount, currency, line_items, taxes, payments), `app/models/profitability_billing_rate.rb` (hourly/fixed_fee, hourly_rate, currency), `app/models/invoice_line_item_time_entry.rb` | N/A | High |
| 14 | API integration | A (As-Is) | `config/routes/api.rb` (versioned v1 API; agent, desktop, cli, mobile, reports, invoices, projects, clients, users namespaces), `app/controllers/api/v1/mcp_controller.rb` | N/A | High |
| 15 | Offline synchronization | C (Extend) | `app/models/desktop_current_timer.rb` (synced_at), `app/controllers/api/v1/desktop/current_timers_controller.rb` (update with sync fields) | N/A | Medium |
| 16 | Data export | A (As-Is) | `app/controllers/api/v1/reports/time_entries_controller.rb` (download CSV/PDF), `app/controllers/internal_api/v1/analytics_exports_controller.rb`, `app/controllers/api/v1/invoices/bulk_download_controller.rb` | N/A | High |
| 17 | Revit connector | D (New Build) | N/A | N/A | N/A |
| 18 | BIMSpend adapter/agent | D (New Build) | N/A | N/A | N/A |
| 19 | Model-to-commercial-project mapping | D (New Build) | N/A | N/A | N/A |
| 20 | Observed vs approved vs billed separation | D (New Build) | N/A | N/A | N/A |

---

## 6. Architecture Boundaries

Preserve the following boundaries. BIMSpend integrates **through existing APIs** rather than modifying upstream implementations.

### 6.1 Miru — business/time-entry foundation (unchanged upstream)
- Miru remains the system of record for companies, clients, projects, users, roles, timesheets, invoices, billing rates, reports, and export.
- BIMSpend uses Miru's **existing agent API** (`POST /api/v1/agent/timesheet_entries`) as the ingestion boundary — not a new timesheet service.
- BIMSpend does **not** fork or modify Miru source; it configures agents, AgentKeys, projects, and users through the API.
- Tenancy: company-scoped (Pundit + Rolify). BIMSpend respects existing policies; does not bypass them.

### 6.2 ActivityWatch — local activity collector (unchanged upstream)
- ActivityWatch remains **local-only**, bound to localhost (default port 5600), never exposed to LAN/internet.
- BIMSpend reads only required local buckets through the aw-server REST API (Buckets/Events/Heartbeat/Query/Export).
- BIMSpend does **not** fork or modify ActivityWatch source; it invokes the local API via an adapter.
- Raw window titles are redacted/minimized locally before any transmission; never sent raw to Miru.

### 6.3 Revit connector — read-only (new BIMSPEND development)
- Read-only event subscriptions only; no transactions, no document modifications.
- Emits document/view/session identity signals to the local BIMSpend adapter.
- Version-specific builds (.NET Framework 4.8 for older Revit, .NET 8 for Revit 2025+).
- Digitally signed binaries for trusted publisher deployment.

### 6.4 BIMSpend adapter — integration layer (new BIMSPEND development)
- Small Windows adapter/agent as the only cloud-ingestion client.
- Reads ActivityWatch local buckets + Revit connector signals; correlates Windows foreground + Revit process + active document + AFK state + mapping confidence.
- Queues encrypted summaries/evidence; authenticates to Miru using revocable device/agent credential.
- Implements offline queue/retry/idempotency; prevents double-counting across multiple Revit processes/documents.

---

## 7. Prioritization (recommended implementation order)

Order maximizes code reuse and minimizes custom code, token usage, maintenance burden, security exposure, and upstream merge conflicts.

| Priority | Task | Reuse basis | Est. effort | Rationale |
|---|---|---|---|---|
| 1 | Miru agent/device credential setup (AgentKey, Agent, default project) | Miru `AgentKey`, `Agent`, `base_controller.rb` — existing API | Low | Foundation for all automated ingestion; no code changes to Miru |
| 2 | Miru company/project/user provisioning through API | Miru `Company`, `Project`, `User`, policies — existing API | Low | Establishes tenancy for BIMSpend data; uses existing models |
| 3 | ActivityWatch local API probe (buckets, events, heartbeat) | ActivityWatch REST API — existing local API | Low | Validates local signal collection before adapter build |
| 4 | BIMSpend adapter skeleton (local queue, encrypted summaries) | New build; invokes Miru agent API + ActivityWatch API | Medium | Core integration layer; minimal custom code |
| 5 | Timesheet entry mapping (observed → draft entry with proof metadata) | Miru `TimesheetEntry` (source: automation, source_metadata, proof_url, external_run/session IDs) | Medium | Uses existing metadata fields; no schema changes |
| 6 | Bill status + review status workflow | Miru `bill_status` (non_billable/unbilled/billed), `review_status` (pending_review/approved/rejected) | Low | Existing enums; configure for BIMSpend semantics |
| 7 | Billing/labor cost tracking | Miru `Invoice`, `ProfitabilityBillingRate`, `invoice_line_item_time_entry` | Medium | Existing models; map loaded cost rate separately |
| 8 | Reports/dashboard reuse | Miru `DashboardController`, `Reports::TimeEntries`, CSV/PDF export | Low | Existing reports; add BIM-specific metrics as needed |
| 9 | Revit connector (read-only, one version) | New build; Autodesk Revit API events | High | No upstream equivalent; highest custom code |
| 10 | Model-to-commercial-project mapping | New build; admin mapping + confidence workflow | Medium | No upstream equivalent; required for attribution |
| 11 | Observed vs approved vs billed separation layer | New build; BIMSpend-specific attribution | Medium | Keeps metrics distinct; required for realization calc |
| 12 | Offline sync + idempotency | Miru `synced_at`, `external_run_id`/`external_session_id` | Medium | Uses existing fields; adapter implements queue/retry |

---

## 8. Critical Gaps Requiring Custom Code (NEW BIMSPEND DEVELOPMENT)

| Gap | Why upstream doesn't cover it | Classification |
|---|---|---|
| BIMSpend Windows adapter/agent | No upstream integration layer between ActivityWatch + Revit + Miru | D |
| Read-only Revit connector | Neither Miru nor ActivityWatch integrates with Autodesk Revit | D |
| Model-to-commercial-project mapping | Miru maps project→client manually; ActivityWatch uses hostname metadata only; no BIM model identity | D |
| Observed vs approved vs billed separation | Miru tracks timesheet entries with bill_status but no observed-activity signal | D |
| Revit version-specific builds (.NET 4.8 vs .NET 8) | No upstream Revit support at all | D |
| Offline sync + idempotency at adapter level | Miru has `synced_at`/`external_run_id` fields but no adapter-side queue | C (Extend) |

---

## 9. License Considerations

| Component | License | Commercial implication |
|---|---|---|
| Miru | MIT (Copyright Saeloun 2023) | Commercial modification/distribution allowed with copyright and permission notice retained |
| ActivityWatch | MPL-2.0 | Commercial distribution allowed; covered modified files distributed in executable form must have corresponding source made available and notices preserved |
| Miru third-party | Ruby gems, npm/pnpm packages | Each license must be enumerated from lockfiles; production clearance required |
| ActivityWatch third-party | Python, Python/Rust packages | Each license must be enumerated; MPL distribution obligations apply to covered files |

**Note:** This is technical planning, not legal advice. Miru/ActivityWatch trademarks and branding are not granted by software licenses. Legal review required before any distribution.

---

## 10. GO/BLOCKED Recommendation

**BLOCKED** — Gate B2-A remains blocked pending explicit user approval (per `TASK_TRACKER.md` row B2-01 and `AI_HANDOFF.md`).

This reuse matrix is research only. No implementation is approved. Upon explicit user approval of Gate B2-A, the executor should:
1. Prioritize items 1–8 above (maximum reuse, minimum custom code).
2. Treat items 9–11 as new BIMSPEND development requiring separate approval.
3. Record all findings as hypotheses until validated by clean builds/tests (currently **NÃO VALIDADO**).

---

**END OF REPORT**
