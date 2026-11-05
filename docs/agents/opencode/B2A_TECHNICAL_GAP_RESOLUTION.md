# BIMSpend — B2-A Technical Gap Resolution Report

**Mode:** READ-ONLY RESEARCH AND DOCUMENTATION. No BIMSpend implementation, no builds, no test execution, no dependency installation, no merges.  
**Branch:** `agent/opencode-b2a-gap-resolution` (created from `main` at `eb13fc9`)  
**Repository:** https://github.com/ueiider/BIMSpend  
**Gate status:** B2-A remains BLOCKED pending explicit user approval.

---

## 1. Executive Summary

This report reconciles the two OpenCode research reports against the ChatGPT Work B2-A review package and the current planning baseline (`main` at `eb13fc9`). It resolves remaining technical uncertainties in the B2-A preparation package without implementing BIMSpend or executing Gate B2-A.

**Key finding:** Both OpenCode reports are static/planning evidence only. The Work review package independently verified upstream commit existence, corrected several command and evidence issues in the OpenCode B2-A plan, and confirmed that B2-A must not create the adapter, Revit connector, cloud ingestion, branded UI or product behavior. B2-A scope is strictly: isolated checkout at pinned revisions, recursive gitlink capture, canonical clean builds/tests, SBOM/license/NOTICE inventory, dependency/security scans, evidence, teardown and stop/go report.

**No claim is made** that builds, tests, scans or SBOMs have been executed. All commands below are **proposed, not executed**.

---

## 2. Evidence Table — Source URLs and Exact Revisions

| Component | Type | URL | Exact Revision | Branch | Verified |
|---|---|---|---|---|---|
| Miru repository | GitHub | https://github.com/saeloun/miru-web | `10e5744` | develop | Work verified commit exists; OpenCode local clone matched `10e457e1d0cd2ac782be9d1edbcbd5a1a573486a` |
| Miru pinned commit | GitHub commit | https://github.com/saeloun/miru-web/commit/10e457e1d0cd2ac782be9d1edbcbd5a1a573486a | `10e457e1d0cd2ac782be9d1edbcbd5a1a573486a` | develop | YES — OpenCode local clone matched |
| Miru MIT LICENSE | GitHub blob | https://github.com/saeloun/miru-web/blob/10e457e1d0cd2ac782be9d1edbcbd5a1a573486a/LICENSE | `10e457e1...` | develop | Listed in PLAN audit evidence index |
| Miru Gemfile | GitHub blob | https://github.com/saeloun/miru-web/blob/10e457e1d0cd2ac782be9d1edbcbd5a1a573486a/Gemfile | `10e457e1...` | develop | Listed in PLAN audit evidence index |
| Miru package.json | GitHub blob | https://github.com/saeloun/miru-web/blob/10e457e1d0cd2ac782be9d1edbcbd5a1a573486a/package.json | `10e457e1...` | develop | Listed in PLAN audit evidence index |
| Miru API routes | GitHub blob | https://github.com/saeloun/miru-web/blob/10e457e1d0cd2ac782be9d1edbcbd5a1a573486a/config/routes/api.rb | `10e457e1...` | develop | Listed in PLAN audit evidence index |
| Miru agent auth controller | GitHub blob | https://github.com/saeloun/miru-web/blob/10e457e1d0cd2ac782be9d1edbcbd5a1a573486a/app/controllers/api/v1/agent/base_controller.rb | `10e457e1...` | develop | Listed in PLAN audit evidence index |
| Miru agent timesheet controller | GitHub blob | https://github.com/saeloun/miru-web/blob/10e457e1d0cd2ac782be9d1edbcbd5a1a573486a/app/controllers/api/v1/agent/timesheet_entries_controller.rb | `10e457e1...` | develop | Listed in PLAN audit evidence index |
| Miru agent key model | GitHub blob | https://github.com/saeloun/miru-web/blob/10e457e1d0cd2ac782be9d1edbcbd5a1a573486a/app/models/agent_key.rb | `10e457e1...` | develop | Listed in PLAN audit evidence index |
| Miru timesheet model | GitHub blob | https://github.com/saeloun/miru-web/blob/10e457e1d0cd2ac782be9d1edbcbd5a1a573486a/app/models/timesheet_entry.rb | `10e457e1...` | develop | Listed in PLAN audit evidence index |
| Miru timesheet policy | GitHub blob | https://github.com/saeloun/miru-web/blob/10e457e1d0cd2ac782be9d1edbcbd5a1a573486a/app/policies/timesheet_entry_policy.rb | `10e457e1...` | develop | Listed in PLAN audit evidence index |
| Miru project policy | GitHub blob | https://github.com/saeloun/miru-web/blob/10e457e1d0cd2ac782be9d1edbcbd5a1a573486a/app/policies/project_policy.rb | `10e457e1...` | develop | Listed in PLAN audit evidence index |
| Miru rack attack | GitHub blob | https://github.com/saeloun/miru-web/blob/10e457e1d0cd2ac782be9d1edbcbd5a1a573486a/config/initializers/rack_attack.rb | `10e457e1...` | develop | Listed in PLAN audit evidence index |
| Miru Dockerfile | GitHub blob | https://github.com/saeloun/miru-web/blob/10e457e1d0cd2ac782be9d1edbcbd5a1a573486a/Dockerfile | `10e457e1...` | develop | Listed in PLAN audit evidence index |
| Miru SECURITY.md | GitHub blob | https://github.com/saeloun/miru-web/blob/10e457e1d0cd2ac782be9d1edbcbd5a1a573486a/SECURITY.md | `10e457e1...` | develop | Listed in PLAN audit evidence index |
| ActivityWatch bundle commit | GitHub commit | https://github.com/ActivityWatch/activitywatch/commit/9fee4702fea08dbe0149cc6e28f4ef66b49f54ec | `9fee4702fea08dbe0149cc6e28f4ef66b49f54ec` | master | YES — OpenCode local clone matched |
| ActivityWatch MPL-2.0 LICENSE | GitHub blob | https://github.com/ActivityWatch/activitywatch/blob/9fee4702fea08dbe0149cc6e28f4ef66b49f54ec/LICENSE.txt | `9fee4702...` | master | Listed in PLAN audit evidence index |
| ActivityWatch .gitmodules | GitHub blob | https://github.com/ActivityWatch/activitywatch/blob/9fee4702fea08dbe0149cc6e28f4ef66b49f54ec/.gitmodules | `9fee4702...` | master | Listed in PLAN audit evidence index |
| ActivityWatch Makefile | GitHub blob | https://github.com/ActivityWatch/activitywatch/blob/9fee4702fea08dbe0149cc6e28f4ef66b49f54ec/Makefile | `9fee4702...` | master | Listed in PLAN audit evidence index |
| aw-server REST API | GitHub blob | https://github.com/ActivityWatch/aw-server/blob/994ea988ca30af36e08cef71ce6046e8c3391584/aw_server/rest.py | `994ea988...` | master | Listed in PLAN audit evidence index — "head observed", NOT bundle gitlink |
| aw-server local config | GitHub blob | https://github.com/ActivityWatch/aw-server/blob/994ea988ca30af36e08cef71ce6046e8c3391584/aw_server/config.py | `994ea988...` | master | Listed in PLAN audit evidence index — "head observed", NOT bundle gitlink |
| aw-client | GitHub blob | https://github.com/ActivityWatch/aw-client/blob/c88cf12c6fb122447157c183322eb2b5c12e6266/aw_client/client.py | `c88cf12c...` | master | Listed in PLAN audit evidence index — "head observed", NOT bundle gitlink |
| aw-watcher-window | GitHub blob | https://github.com/ActivityWatch/aw-watcher-window/blob/12000f58d16b8fc1376af42755c688b3d7157280/aw_watcher_window/main.py | `12000f58...` | master | Listed in PLAN audit evidence index — "head observed", NOT bundle gitlink |
| aw-watcher-window privacy filter | GitHub blob | https://github.com/ActivityWatch/aw-watcher-window/blob/12000f58d16b8fc1376af42755c688b3d7157280/aw_watcher_window/privacy_filter.py | `12000f58...` | master | Listed in PLAN audit evidence index — "head observed", NOT bundle gitlink |
| aw-watcher-afk | GitHub blob | https://github.com/ActivityWatch/aw-watcher-afk/blob/b4839261688eb7980d1730d46dd35a36b21cfc1d/aw_watcher_afk/afk.py | `b4839261...` | master | Listed in PLAN audit evidence index — "head observed", NOT bundle gitlink |
| aw-server-rust config | GitHub blob | https://github.com/ActivityWatch/aw-server-rust/blob/10b4b7f2dde11efbf84f63a96c88088330259c97/aw-server/src/config.rs | `10b4b7f2...` | master | Listed in PLAN audit evidence index — "head observed", NOT bundle gitlink |
| aw-tauri README | GitHub blob | https://github.com/ActivityWatch/aw-tauri/blob/d3b5527ce99547159ba1f7fbda00ae9b605d5cbb/README.md | `d3b5527c...` | master | Listed in PLAN audit evidence index — "head observed", NOT bundle gitlink |
| Revit DocumentOpened | Autodesk docs | https://help.autodesk.com/cloudhelp/2026/ENU/Revit-API-MainReference/files/html/b9415c2d-442e-f61d-aafa-de31cce7959b.htm | N/A | N/A | Listed in PLAN audit evidence index |
| Revit events inventory | Autodesk docs | https://help.autodesk.com/cloudhelp/2026/ENU/Revit-API-MainReference/files/html/94db8ea8-d2c3-5e71-8030-466bcb8e4426.htm | N/A | N/A | Listed in PLAN audit evidence index |
| Revit Idling limitations | Autodesk docs | https://help.autodesk.com/cloudhelp/2026/ENU/Revit-API-MainReference/files/html/56145d84-e948-730a-dc72-2a7b88a50a99.htm | N/A | N/A | Listed in PLAN audit evidence index |
| Revit BasicFileInfo | Autodesk docs | https://help.autodesk.com/cloudhelp/2026/ENU/Revit-API-MainReference/files/html/475edc09-cee7-6ff1-a0fa-4e427a56262a.htm | N/A | N/A | Listed in PLAN audit evidence index |
| Revit .NET 8 migration | Autodesk docs | https://help.autodesk.com/cloudhelp/2026/ENU/Revit-API/files/Revit_API_Developers_Guide/...NET8_Update_html.html | N/A | N/A | Listed in PLAN audit evidence index |
| Revit signing add-in | Autodesk docs | https://help.autodesk.com/cloudhelp/2027/ENU/Revit-API/files/Revit_API_Developers_Guide/...Digitally_Signing_Your_Revit_Add_in_html.html | N/A | N/A | Listed in PLAN audit evidence index |

**ActivityWatch submodule gitlinks (bundle `9fee4702`, authoritative for reproducible checkout):**

| Submodule | Gitlink SHA | URL | Verified by Work |
|---|---|---|---|
| aw-client | `fe106969fcd413ffadbd5a9d3b75808cc636cd54` | https://github.com/ActivityWatch/aw-client.git | YES — commit existence verified |
| aw-core | `28c3acf047b225f90592e1c47c8ec2596612d70b` | https://github.com/ActivityWatch/aw-core.git | YES |
| aw-notify | `87e83cca65276b2278e4361db74087764c3ecf2c` | https://github.com/ActivityWatch/aw-notify-rs.git | YES |
| aw-qt | `bbccb715516c5c02f863f883680aee0e40c803b5` | https://github.com/ActivityWatch/aw-qt.git | YES |
| aw-server | `67cfb479a9f8511ad3a9595224cb22c35b9dbe65` | https://github.com/ActivityWatch/aw-server.git | YES |
| aw-server-rust | `fe558c4f106a70004a42bc30558c7438f8b66b4f` | https://github.com/ActivityWatch/aw-server-rust.git | YES |
| aw-tauri | `44b92d45878504fc7b9d1d9e867e8967cccd9b17` | https://github.com/activitywatch/aw-tauri | YES |
| aw-watcher-afk | `b4839261688eb7980d1730d46dd35a36b21cfc1d` | https://github.com/ActivityWatch/aw-watcher-afk.git | YES |
| aw-watcher-input | `4e6461dbf55a1c1aa8f9ece4df5f109188f56f61` | https://github.com/ActivityWatch/aw-watcher-input.git | YES |
| aw-watcher-window | `10638b2c94e46195f709abd8626cb15f911e99f8` | https://github.com/ActivityWatch/aw-watcher-window.git | YES |
| awatcher | `c32ca62c66e6ff4f2949b841ec20d30c778d11ba` | https://github.com/2e3s/awatcher | YES |

**Note:** PLAN audit §2.1 recorded component "head observed" SHAs (e.g., aw-server `994ea988`, aw-client `c88cf12c`, aw-watcher-window `12000f58`) that **differ** from the bundle gitlinks above. Work confirmed: gitlinks at the pinned umbrella commit are authoritative for reproducible checkout; differences are not contradictions. B2-A must record `git submodule status --recursive` after recursive initialization.

---

## 3. Verified Versus Unverified Claims

### 3.1 Verified claims (source or remote commit existence confirmed)

| Claim | Evidence | Source |
|---|---|---|
| Miru pinned commit `10e457e1...` exists on `develop` | OpenCode local clone matched; Work confirmed | OpenCode B2-A report §3; Work B2-A review §3 |
| ActivityWatch bundle pinned commit `9fee4702...` exists on `master` | OpenCode local clone matched; Work confirmed | OpenCode B2-A report §3; Work B2-A review §3 |
| All 11 ActivityWatch submodule gitlink commit objects exist in named remotes | Work independent existence check | Work B2-A review §3 |
| Miru exposes `POST /api/v1/agent/timesheet_entries` with AgentKey bearer auth | OpenCode read source at pinned commit | OpenCode reuse matrix §2.1; PLAN audit §1 |
| Miru `AgentKey.authenticate` / `issue_for` / `revoke!` / `digest` exist | OpenCode read `app/models/agent_key.rb` | OpenCode reuse matrix §2.1 |
| Miru `TimesheetEntry` has `bill_status` enum and `review_status` enum | OpenCode read `app/models/timesheet_entry.rb` | OpenCode reuse matrix §2.1 |
| Miru `ProfitabilityBillingRate` has `billing_method` enum (hourly/fixed_fee) | OpenCode read `app/models/profitability_billing_rate.rb` | OpenCode reuse matrix §2.1 |
| Miru uses Ruby 4.0.9, Rails ~8.1.4, PostgreSQL | OpenCode read `.ruby-version`, `Gemfile` | OpenCode B2-A report §4; reuse matrix §4 |
| ActivityWatch uses Python 3.9.13, Poetry 1.5.1, Node 16.20.2, Rust nightly | OpenCode read `.tool-versions`, `pyproject.toml` | OpenCode B2-A report §4; reuse matrix §4 |
| ActivityWatch bundle uses git submodules; 11 submodules declared | OpenCode read `.gitmodules`, `git submodule status` | OpenCode B2-A report §3; reuse matrix §2.2 |
| B2-A remains BLOCKED pending explicit user approval | `TASK_TRACKER.md` row B2-01; `AI_HANDOFF.md` | Main baseline; Work B2-A review §16 |
| No builds, tests, scans or installations performed | OpenCode reports and Work review | All three reports |

### 3.2 Unverified claims (marked NOT VERIFIED or requiring corrected evidence)

| Claim | Status | Reason |
|---|---|---|
| `bundle licenses` produces a valid SBOM/license inventory | NOT VERIFIED | Not a standard Bundler command; no supporting tool established (Work §6.1) |
| Lockfiles are a complete SBOM or license conclusion | NOT VERIFIED | Lockfiles are inputs, not SBOM/license output (Work §6.1) |
| `bundle exec rails spec` is Miru's canonical test command | NOT VERIFIED | Not established in pinned source; likely `bundle exec rspec` if confirmed by CI (Work §6.1) |
| `bundle exec rake i18n:config` is a build prerequisite | NOT VERIFIED | No evidence in pinned source (Work §6.1) |
| ActivityWatch `make` "or equivalent" is reproducible | NOT VERIFIED | "Or equivalent" is not reproducible (Work §6.1) |
| ActivityWatch aw-server REST API endpoints at `994ea988` | NOT VERIFIED AT BUNDLE GITLINK | That SHA is a "head observed" inspection, not the bundle gitlink `67cfb479`; submodules not initialized by OpenCode (OpenCode reuse matrix §2.2; Work §5.3) |
| ActivityWatch window-watcher/AFK-watcher implementation at pinned gitlinks | NOT VERIFIED | Submodule source not initialized/read by OpenCode; inferred from README only (OpenCode reuse matrix §2.2) |
| ActivityWatch port/bind defaults, privacy filters, payloads, packaging at exact gitlinks | NOT VERIFIED | Requires exact-gitlink source inspection during approved baseline (Work §5.3) |
| Clean Miru/ActivityWatch builds succeed | NOT VERIFIED | No builds executed (all reports) |
| SBOM/license/CVE scans completed | NOT VERIFIED | No scans executed (all reports) |
| `ProfitabilityBillingRate` = employer's loaded internal hourly cost | INCORRECT / NOT VERIFIED | It is billing/charge-rate evidence, not loaded-cost evidence (Work §5.3) |
| `synced_at` field = durable encrypted offline sync | INCORRECT / NOT VERIFIED | Field exists; durable queue/ack/replay/idempotent replay not proven (Work §5.3) |
| `external_run_id`/`external_session_id` = proven idempotent | INCORRECT / NOT VERIFIED | Presence of fields does not prove unique constraints or replay safety (Work §5.3) |
| Local machine Ruby/Node/Python/Rust/Docker status = execution prerequisite | INCORRECT | Transient local state; must not drive plan (Work §5.3) |
| OpenCode MASTER_PLAN §10/§11/§18 citations | INACCURATE | Main baseline MASTER_PLAN.md organized by headings, no numbered sections (Work §6.2) |
| Local clone paths (`D:\BIMSpend\Research\Repos\...`) are reproducible evidence | INCORRECT | Local clones not persistent source of truth (Work §6.3) |

---

## 4. Miru — Build, Test, Runtime Requirements

### 4.1 Canonical commands (proposed, not executed)

The OpenCode plan proposed commands that Work flagged as unverified. The corrected approach is to derive canonical commands from pinned upstream CI/build documentation, not assume them.

| Step | Proposed command source | Notes |
|---|---|---|
| Miru dependency resolution | From pinned `Gemfile` / `Gemfile.lock` and `package.json` / `pnpm-lock.yaml` | Use Bundler + pnpm at pinned versions |
| Miru asset build | From pinned upstream CI/configuration | Vite + Propshaft per `Gemfile` |
| Miru database preparation | PostgreSQL required (`gem "pg"`) | Synthetic/test database only; no production data |
| Miru canonical test suite | From pinned upstream CI (expected RSpec, not confirmed) | Do not assume `rails spec`; confirm runner from CI |
| Miru Ruby security scan | Bundler audit + Brakeman (declared in `Gemfile`) | `require: false` in Gemfile; pin tool versions |
| Miru JavaScript security scan | From `package.json` / `pnpm-lock.yaml` | Pin tool versions |

### 4.2 Runtime, dependency and database requirements

| Requirement | Version | Source |
|---|---|---|
| Ruby | 4.0.9 | `.ruby-version` |
| Bundler | From `Gemfile.lock` | `Gemfile.lock` |
| Rails | ~8.1.4 | `Gemfile` |
| Node.js | 24.22.1 | `.node-version`, `.nvmrc` |
| pnpm | From `pnpm-lock.yaml` | `pnpm-lock.yaml` |
| PostgreSQL | Required by `gem "pg"` | `Gemfile` |
| Docker (Kamal deployment) | From `Dockerfile*` | `Gemfile`, `render.yaml` |

### 4.3 Proven upstream functionality vs proposed BIMSpend extensions

| Capability | Proven in Miru at pinned commit | BIMSpend extension required |
|---|---|---|
| Companies/clients/projects/teams | YES | No (reuse candidate) |
| User authentication (Devise/JWT/MFA/passkeys) | YES | Configure/extend for BIMSpend roles |
| Agent/AgentKey timesheet ingestion | YES | Configure; idempotency/rate-limit gaps |
| Timesheet bill/review status | YES | Map to BIMSpend semantics |
| Invoices/payments | YES | Map billed-hours distinction |
| Reports/CSV-PDF export | YES | Add BIM-specific metrics |
| Dashboard | YES | Add BIM-specific metrics |
| Loaded internal labor cost | NO | NEW MODEL — `ProfitabilityBillingRate` is billing rate, not loaded cost |
| Durable offline sync | NO | NEW — `synced_at` field exists but queue/replay not proven |
| External-ID idempotency | NO — fields exist, constraints not proven | NEW — adapter-side idempotency |
| Observed vs approved vs billed separation | NO | NEW attribution layer |
| Revit connector | NO | NEW BIMSPEND development |
| BIMSpend Windows adapter | NO | NEW BIMSPEND development |

---

## 5. ActivityWatch — Pinned Bundle and Gitlinks

### 5.1 Bundle structure

The ActivityWatch bundle commit `9fee4702...` is the reproducible umbrella pin. It declares 11 submodules via `.gitmodules`. OpenCode did **not** initialize submodules (all directories empty; `git submodule status` shows `-`). Work independently verified all 11 gitlink commit objects exist in their named remotes.

### 5.2 Component classification

| Submodule | Gitlink SHA | Role | Implementation detail verified? |
|---|---|---|---|
| aw-server | `67cfb479` | Python local server (REST API, datastore, query engine) | NO — not read at this gitlink |
| aw-server-rust | `fe558c4f` | Rust local server (planned future default) | NO |
| aw-client | `fe106969` | API client wrappers | NO |
| aw-core | `28c3acf0` | Core libs (event schemas, storage base) | NO |
| aw-watcher-window | `10638b2c` | Active window + title heartbeats | NO |
| aw-watcher-afk | `b4839261` | AFK detection from keyboard/mouse | NO |
| aw-watcher-input | `4e6461db` | Keyboard/mouse input watcher | NO |
| aw-qt | `bbccb715` | Qt desktop manager | NO |
| aw-tauri | `44b92d45` | Tauri desktop shell | NO |
| aw-notify | `87e83cca` | Notifications | NO |
| awatcher | `c32ca62c` | Legacy tool | NO |

### 5.3 Window-watcher, AFK-watcher, local API and event semantics

| Aspect | README-described behavior (NOT VERIFIED from source at pinned gitlinks) |
|---|---|
| Local API | Buckets API, Events API, Heartbeat API, Query API, JSON export via `/api/0` |
| Window watcher | Emits `app` and `title` heartbeats for active window; privacy filter exists |
| AFK watcher | Emits `afk` / `not-afk` from keyboard/mouse input |
| Storage | Local timeseries in buckets; loopback default (port 5600 Python, 127.0.0.1 Rust) |
| Packaging | PyInstaller; optional Tauri; Windows registry/MSI described |
| Autostart | aw-qt described as managing watcher lifecycle |

**All ActivityWatch implementation details above are NOT VERIFIED against the pinned gitlinks.** OpenCode explicitly did not initialize submodules. Exact paths, endpoints, privacy-filter behavior, port defaults, payloads and packaging must be inspected during an approved B2-A baseline after recursive submodule initialization.

### 5.4 Licensing obligations

| Component | License | Commercial implication |
|---|---|---|
| ActivityWatch umbrella | MPL-2.0 | Commercial distribution allowed; covered modified files distributed in executable form must have corresponding source made available and notices preserved |
| Eleven submodules | Not consolidated | Recursive license/NOTICE and vendored-code inventory required at exact gitlinks |
| Miru | MIT | Commercial modification/distribution allowed with copyright and permission notice retained |

---

## 6. Windows/Linux Validation Matrix

| Aspect | Linux/container | Windows | Notes |
|---|---|---|---|
| Miru build | Supported (Ruby + Node + PostgreSQL) | Partially (Ruby on Windows via installer; PostgreSQL) | Miru targets Linux/container first via Kamal/Docker |
| Miru test suite | Expected CI-runnable | Not established | Confirm from pinned CI |
| ActivityWatch Python server | Supported | Supported (pywin32-ctypes, pefile win32 deps) | Python 3.9.x required; local machine has 3.12.10 (mismatch) |
| ActivityWatch Rust server | Supported | Supported (Rust nightly) | Rust nightly toolchain required |
| ActivityWatch watchers | Limited (no win32-specific) | Full (aw-watcher-window, aw-watcher-afk, aw-watcher-input) | Windows-specific integration risks below |
| ActivityWatch desktop shell (Tauri/aw-qt) | Supported | Supported | |
| ActivityWatch packaging (PyInstaller) | Supported | Supported | Windows MSI/registry described |
| ActivityWatch loopback bind | `localhost:5600` (Python), `127.0.0.1` (Rust) | Same | Never expose to LAN/internet |
| Revit connector | N/A | Windows only (.NET 4.8 or .NET 8) | Revit is Windows-only; version-specific signed builds |
| BIMSpend adapter | N/A | Windows | Local Windows adapter/agent |

### 6.1 Windows-specific integration risks

| Risk | Severity | Mitigation |
|---|---|---|
| Revit version fragmentation (.NET Framework 4.8 vs .NET 8) | High | Separate signed binaries per era; multi-targeting from one codebase |
| Revit UI slowdown/crash from Idling handlers | High | Read-only handlers, bounded payload, latency tests, kill switch |
| Unsigned Revit add-in trust prompts | High | Code-sign binaries and installer; trusted publisher deployment |
| Multiple Revit processes/documents double-counting | High | Adapter correlation; process/session IDs; foreground-only high confidence |
| ActivityWatch watcher restarts, sleep, RDP, lock screen, UAC | Medium | Explicit tests; do not equate window focus with productive time |
| Window titles exposing sensitive text | Critical | Local allowlist/redaction; never collect keystrokes/screenshots; minimize/hash |
| ActivityWatch exposed to LAN/internet | Critical | Bind to loopback only; never expose directly |
| Installing runtimes on user's normal workstation | Critical | Use disposable VM/container/managed runner only |

### 6.2 Supported vs unsupported environments

| Environment | Supported for B2-A? | Rationale |
|---|---|---|
| Disposable Linux/container VM | YES | Miru primary target; reproducible |
| Disposable Windows VM | YES (if in approved matrix) | Required to validate Windows packaging/watchers |
| User's normal workstation | NO | Must not install runtimes/toolchains or run watchers against real session |
| Production environment | NO | B2-A is isolated baseline only |

---

## 7. Security / SBOM Tooling Recommendations

| Category | Recommended tool | Rationale | Version policy |
|---|---|---|---|
| Ruby SBOM/license | bundler-audit (with `--update`) | Declared in Miru `Gemfile` (`require: false`) | Pin exact version; verify exists before run |
| Ruby static security | Brakeman | Declared in Miru `Gemfile` | Pin exact version |
| JavaScript/Node SBOM | From `pnpm-lock.yaml` + ecosystem scanner | Miru frontend deps | Pin exact version |
| Python SBOM/license | From `poetry.lock` + ecosystem scanner | ActivityWatch Python deps | Pin exact version |
| Rust SBOM/license | cargo audit / cargo-deny | ActivityWatch Rust deps | Pin exact version |
| Container/OS SBOM | From `Dockerfile*` base image digest | Miru Kamal/Docker deployment | Pin image digest |
| Combined SBOM format | CycloneDX or SPDX | Machine-readable, auditable | Pin format and tool |
| Vulnerability scanning | Pinned scanner per ecosystem | Do not mix "safety, bandit, cargo audit" without versions | Pin exact versions, source, invocation |
| Secret scanning | Pre-commit/secret scanner | Prevent secrets in logs/repo | Pin exact version |

**Severity thresholds and exception handling (to be defined by approver):**

| Severity | Disposition |
|---|---|
| Critical vulnerability | STOP; documented disposition required before proceeding |
| High vulnerability | STOP; documented disposition required before proceeding |
| Medium/Low vulnerability | Document; may proceed with recorded exception |
| No-fix vulnerability | Document; do not silently proceed |
| Unknown/unlicensed component | STOP; legal review required |
| MPL/GPL/AGPL conflict with commercial distribution | STOP; legal review required |

**Restriction:** Do not execute scanners. This section recommends tools and policies only.

---

## 8. Data Integrity

### 8.1 Durable offline synchronization requirements

| Requirement | Status in upstream | Gap |
|---|---|---|
| Local encrypted queue | NOT PROVEN | `synced_at` field on `DesktopCurrentTimer` exists; durable queue not demonstrated |
| Acknowledgement and replay | NOT PROVEN | Miru has `external_run_id`/`external_session_id` fields but no unique constraint or replay safety proven |
| Offline retry with bounded loss | NOT PROVEN | BIMSpend adapter must implement |
| Idempotent ingestion | NOT PROVEN | Fields exist; server uniqueness constraint and replay tests not established |

### 8.2 Idempotency requirements

| Aspect | Requirement |
|---|---|
| Server-side uniqueness | Unique constraint on `external_run_id` / `external_session_id` per agent/company |
| Replay safety | Repeated upload produces one draft entry (per PLAN audit B3-B acceptance) |
| Wrong-tenant rejection | Wrong-tenant project IDs rejected |
| Offline replay | Lossless and bounded |
| External ID binding | Bound to agent/user/company; not cross-tenant |

### 8.3 Metric separation (observed vs approved vs billed)

| Metric | Definition | Upstream evidence | BIMSpend requirement |
|---|---|---|---|
| Observed activity | Measured foreground/window attention | ActivityWatch heartbeats (NOT VERIFIED at gitlinks) | Separate record; not productive effort |
| Attributed time | Activity correlated to project via Revit/AFK/process | New correlation layer | NEW BIMSPEND development |
| Approved time | Reviewed/approved timesheet entry | Miru `review_status: approved` | Existing; configure workflow |
| Billed hours | Invoiced quantity to client | Miru `Invoice`/`TimesheetEntry.bill_status: billed` | Preserve distinction; never auto-invoice from observed |

### 8.4 Billing rate vs loaded internal labor cost

| Concept | Miru evidence | Status |
|---|---|---|
| Standard charge rate (client price) | `ProfitabilityBillingRate.hourly_rate`, `billing_method: hourly/fixed_fee` | PROVEN — billing/charge rate |
| Loaded internal labor cost (employer cost) | NOT in Miru at pinned commit | GAP — NEW protected model required; Work §5.3 |

BIMSpend must keep `standard_charge_rate` and `internal_loaded_cost_rate` as separate records. `contribution_after_labor = revenue − labor_cost` is not net profit.

---

## 9. Licensing

### 9.1 MIT and MPL-2.0 obligations

| Component | License | Key obligations |
|---|---|---|
| Miru | MIT | Commercial modification/distribution allowed; retain copyright and permission notice |
| ActivityWatch umbrella | MPL-2.0 | Commercial distribution allowed; covered modified files distributed in executable form must make corresponding source available and preserve notices |
| ActivityWatch submodules | Not consolidated | Recursive license/NOTICE inventory required at exact gitlinks |
| Third-party (Ruby/npm/Python/Rust) | Various | Each license enumerated from lockfiles; production clearance required |
| Fonts/icons/images/assets | Various | Asset provenance and redistribution review |

### 9.2 Distribution and modification boundaries

| Boundary | Guidance |
|---|---|
| Miru (MIT) | Configuring via API = no modification; forking = retain MIT notice |
| ActivityWatch (MPL-2.0) | Prefer unmodified local ActivityWatch + separate adapter; if modifying covered files and distributing, publish corresponding source |
| Combined stack | Keep MPL component separable from proprietary adapter; legal review before distribution |
| Trademarks/branding | Not granted by code licenses; separate clearance required |

### 9.3 Questions requiring legal review

- MPL-2.0 distribution obligations for ActivityWatch submodules when bundled with proprietary adapter
- GPL/AGPL dependency surprise in transitive packages
- Australian employment/privacy law for workplace monitoring
- Trademark clearance for reuse of upstream names/logos

---

## 10. Corrected B2-A Execution Prerequisites

### 10.1 Required before execution (from Work review §7)

| # | Prerequisite |
|---|---|
| 1 | Explicit user approval for Gate B2-A only |
| 2 | Approved disposable executor (Windows VM, managed runner or isolated environment) — NOT the user's normal workstation |
| 3 | Network authorization to clone upstream/submodules and download pinned dependencies/scanner databases |
| 4 | Resource budget (disk/RAM/CPU/max duration) for 11 ActivityWatch submodules + Miru assets/tests |
| 5 | Platform matrix decision (Linux/container, Windows, or both) |
| 6 | Exact canonical commands derived from pinned CI/configuration |
| 7 | Tool manifest: Docker/VM image, Git, Ruby, Bundler, Node, pnpm, PostgreSQL, Python, Poetry, Rust, all scanners |
| 8 | SBOM format: CycloneDX or SPDX per ecosystem + combined inventory |
| 9 | License policy: allowed / review-required / prohibited (include fonts, icons, assets, container layers, transitive packages) |
| 10 | Vulnerability policy: severity threshold, no-fix treatment, scanner freshness, false-positive handling |
| 11 | Evidence policy: filenames, max sizes, redaction rules, checksums, raw-log disposition |
| 12 | Secret/privacy controls: synthetic config only; scan logs before commit |
| 13 | Teardown verification |
| 14 | Branch ownership and reviewer naming |

### 10.2 Corrected commands (from Work review §6.1)

| OpenCode proposal | Work finding | Correction |
|---|---|---|
| `git submodule status --recursive` before init | Uninitialized nested submodules give incomplete status | `git submodule update --init --recursive` FIRST, then capture status |
| `bundle licenses` | Not a standard Bundler command | Select and pin an approved Ruby license/SBOM tool |
| Copy lockfiles as SBOM | Lockfiles are inputs, not SBOM | Generate CycloneDX/SPDX; preserve manifest hashes |
| `|| true` to mask failures | Conflicts with preserve-failures requirement | Capture exit code/stdout/stderr explicitly |
| `bundle exec rails spec` | Not established as Miru test runner | Derive canonical command from pinned CI (likely `bundle exec rspec` if confirmed) |
| `bundle exec rake i18n:config` | No evidence as build prerequisite | Remove unless CI/build docs require it |
| ActivityWatch `make` "or equivalent" | Not reproducible | Use exact upstream targets from pinned Makefile/CI |
| Install runtimes on user's machine | Changes user's workstation | Use disposable VM/container/managed runner |

### 10.3 Ten-stage procedure (Work review §10 — proposed, not executed)

Stages 0–6 cover approval, checkout, inventory, Miru baseline, ActivityWatch baseline, reproducibility check, evidence review and teardown. All require explicit user approval before execution.

---

## 11. Explicit Unresolved Blockers

| Blocker | Impact on B2-A |
|---|---|
| No explicit user approval for B2-A execution | MUST RESOLVE FIRST |
| No approved disposable executor/platform matrix | Cannot provision run |
| No pinned SBOM/scanner toolchain | Cannot satisfy SBOM/scan acceptance criteria |
| No explicit license and vulnerability decision policies | Cannot resolve license/CVE findings |
| ActivityWatch implementation at pinned gitlinks unverified (submodules not initialized) | Cannot confirm window/AFK/API behavior |
| Loaded internal labor cost not proven by Miru `ProfitabilityBillingRate` | Cannot claim loaded-cost tracking reuse |
| General offline sync/idempotent ingestion not proven | Cannot claim durable sync reuse |
| OpenCode MASTER_PLAN §10/§11/§18 citations inaccurate | Cannot treat as precise evidence |
| Local clone paths not reproducible evidence | Cannot depend on `D:\...` paths in future plans |
| Clean builds/tests not executed | B2-A acceptance criteria unmet |
| SBOM/license/CVE scans not executed | B2-A acceptance criteria unmet |
| Runtime builds/tests/legal conclusions NOT VALIDATED | Gate B2-A remains BLOCKED |

---

## 12. GO/BLOCKED Recommendation

**BLOCKED** — Gate B2-A remains blocked pending explicit user approval. This gap resolution report documents verified and unverified claims, corrects the OpenCode execution plan per the Work review, and defines the corrected B2-A prerequisites and ten-stage procedure. None of the procedure has been executed.

Upon explicit user approval of Gate B2-A, the executor should:
1. Resolve blockers 1–7 above (approval, executor, toolchain, policies).
2. Run the ten-stage procedure in a disposable isolated environment.
3. Capture evidence with failures preserved.
4. Produce a stop/go recommendation per Work review §12.

Passing B2-A does **not** approve B2-B, B3, production use or deployment. A separate human decision is required.

---

**END OF REPORT — B2-A REMAINS BLOCKED**
