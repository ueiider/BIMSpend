# BIMSpend — PLAN Audit Report

Date: 2026-11-05  
Mode: **PLAN ONLY**  
Scope: P1-01 through P1-07  
Decision status: **CONDITIONAL GO TO A SMALL ISOLATED PROOF OF CONCEPT — BUILD REMAINS BLOCKED**

## 1. Executive recommendation

Use a **composition architecture**, not a merged fork:

1. **Miru** as the administrative and commercial web foundation.
2. **ActivityWatch** as an optional local Windows signal collector, kept behind localhost.
3. A small **BIMSpend Windows adapter/agent** as the only cloud-ingestion client.
4. A versioned, read-only **Revit connector** that emits document/view/session identity signals to the local adapter.
5. A BIMSpend-specific attribution layer that preserves uncertainty and keeps observed activity, approved project time, billed hours, rates and cost as different records.

The strongest reuse finding is that Miru already has a dedicated agent ingestion boundary:

- `config/routes/api.rb` exposes `POST /api/v1/agent/timesheet_entries`.
- `app/controllers/api/v1/agent/base_controller.rb` authenticates a bearer `AgentKey`, binds the request to a user and company, and sets request context.
- `app/controllers/api/v1/agent/timesheet_entries_controller.rb` accepts automated duration, work date, project, proof metadata and external run/session IDs.
- `app/models/timesheet_entry.rb` records source/proof metadata, agent ownership, audit history, bill status and review status; agent-created entries default to `pending_review`.

Therefore BIMSpend should first **configure and adapt Miru's existing agent pathway**, not build a new timesheet service. ActivityWatch should remain local and supply evidence signals; it is not a cloud multi-tenant backend.

No code was cloned, built, installed, executed or vulnerability-scanned. Runtime, performance and integration claims are **NÃO VALIDADO**.

## 2. Pinned revisions and legal inventory (P1-01)

### 2.1 Pinned upstream revisions

| Component | Revision audited | Branch at audit | Evidence |
|---|---|---|---|
| Miru | `10e457e1d0cd2ac782be9d1edbcbd5a1a573486a` | `develop` (default) | GitHub commit and all Miru file links below |
| ActivityWatch bundle | `9fee4702fea08dbe0149cc6e28f4ef66b49f54ec` | `master` | GitHub commit; bundle uses git submodules |
| aw-server | `994ea988ca30af36e08cef71ce6046e8c3391584` | `master` head observed | Static component inspection |
| aw-client | `c88cf12c6fb122447157c183322eb2b5c12e6266` | `master` head observed | Static component inspection |
| aw-watcher-window | `12000f58d16b8fc1376af42755c688b3d7157280` | `master` head observed | Static component inspection |
| aw-watcher-afk | `b4839261688eb7980d1730d46dd35a36b21cfc1d` | `master` head observed | Static component inspection |
| aw-qt | `bbccb715516c5c02f863f883680aee0e40c803b5` | `master` head observed | Static component inspection |
| aw-server-rust | `10b4b7f2dde11efbf84f63a96c88088330259c97` | `master` head observed | Static component inspection |
| aw-tauri | `d3b5527ce99547159ba1f7fbda00ae9b605d5cbb` | `master` head observed | Static component inspection |
| aw-watcher-input | `dd52313b9f52e0c45528dc0639e9510344278a0c` | `master` head observed | Static component inspection |

The ActivityWatch bundle commit is the reproducible umbrella pin. Its `.gitmodules` declares eleven subprojects. Component heads above were independently inspected on 2026-11-05; exact equality between every component head and every gitlink in the umbrella commit was **NÃO VALIDADO** by the available read-only connector. A Phase 2 checkout must record `git submodule status --recursive` before any build.

### 2.2 Licenses

| Candidate | Verified top-level license | Commercial implication | Status |
|---|---|---|---|
| Miru | MIT, `LICENSE`, copyright Saeloun 2023 | Commercial modification/distribution allowed with copyright and permission notice retained | READY for legal inventory; production clearance still required |
| ActivityWatch bundle | MPL-2.0, `LICENSE.txt` | Commercial distribution allowed; covered modified files distributed in executable form must have corresponding source made available and notices preserved | CONFIGURE |
| Third-party packages/assets | Ruby, npm/pnpm, Python, Rust, fonts, icons, browser/runtime dependencies | Each license and notice must be enumerated from lockfiles and packaged output | UNKNOWN |

This report is technical planning, not legal advice. Miru branding/trademarks and ActivityWatch names/logos are not granted merely by the software licenses.

### 2.3 Dependency observations

Miru at the pinned revision is a modern Rails/React system:

- Ruby 4.0.9; Rails ~8.1.4; PostgreSQL; React 19; TypeScript; Vite; pnpm.
- Authentication/security packages include Devise, devise-security, pwned-password checks, JWT, passkeys/WebAuthn, TOTP, OAuth, Pundit, Rolify, Audited and Rack::Attack.
- Operational dependencies include Solid Queue/Cache/Cable, Redis, S3, Postmark, Stripe, Razorpay, QuickBooks and Google Calendar.
- The Dockerfile pins the base image digest and several build inputs/checksums and runs the runtime as UID/GID 1000.
- Lockfile license scan, CVE scan and runtime image scan: **NÃO VALIDADO**.

ActivityWatch is a bundle of Python and Rust components plus web UI/desktop shells. The umbrella build uses git submodules, Poetry, PyInstaller and optional Tauri/Rust paths. It packages aw-server, aw-client, aw-watcher-window, aw-watcher-afk and a desktop manager. Full transitive license/CVE/package inventory: **NÃO VALIDADO**.

## 3. Miru static audit (P1-02)

### 3.1 Existing functionality

| Capability | Evidence | Classification |
|---|---|---|
| Companies/workspaces and user employment | company-scoped models and `current_workspace` patterns | READY |
| Clients and projects | `config/routes/api.rb`; project model/policy/API | READY |
| Team and project membership | team/project-member routes and `ProjectPolicy::Scope` | READY |
| Manual timesheets | timesheet APIs, model and UI routes | READY |
| Automated agent timesheets | `api/v1/agent/*`, `Agent`, `AgentKey` | READY/CONFIGURE |
| Billable/unbilled/billed state | `TimesheetEntry.bill_status` | READY |
| Automated-entry review state | `pending_review/approved/rejected` | READY |
| Invoices/payments/collections | API routes and payment integrations | READY |
| Time and revenue reports/exports | report and internal analytics routes | READY |
| Audit history | `audited` on timesheet entries; `audit_logs` route | READY |
| Responsive web + mobile API/app work | React web and `apps/mobile` scripts/routes | CONFIGURE |
| BIM-specific observed-event storage | no dedicated raw signal/evidence schema established | BUILD |
| Actual-vs-billed-vs-loaded-cost BIM intelligence | not established as the required BIMSpend model | ADAPT/BUILD |

### 3.2 Architecture and data boundaries

- Rails JSON API plus React/Vite frontend and PostgreSQL.
- Background work through Solid Queue; cache/cable adapters are present.
- Company/workspace is the tenancy boundary used throughout the inspected policies.
- Project scope limits employees to assigned projects while owner/admin can view the company's projects.
- Timesheet scope gives owner/admin company entries and ordinary users only their own entries within the workspace.
- Timesheet changes are audited and billed entries have editing restrictions.

This is useful application-level tenancy, but it is not evidence of database row-level security. Cross-tenant security tests, hostile parameter tests, backup/restore isolation and operational tenant controls are **NÃO VALIDADO**.

### 3.3 Authentication and authorization

Verified static controls:

- Browser/API authentication through Devise/session/JWT and legacy header support.
- Passkeys, TOTP, OTP, OAuth and compromised-password support are declared.
- Pundit + Rolify implement resource-scoped roles.
- Agent ingestion uses a 32-byte random token returned once, stored as SHA-256 digest, revocable and checked against active agent/user/company employment.
- Login/signup/recovery and selected expensive endpoints have Rack::Attack limits.
- Security reporting policy exists, although its “supported version 0.20.0” is stale relative to package version 3.0.6 and should not be treated as reliable release-support evidence.

Gaps:

- No agent-route-specific throttle was found.
- Agent tokens are bearer credentials without visible scopes beyond the bound agent/user/company.
- The create endpoint does not visibly enforce an idempotency uniqueness constraint on `external_run_id` or `external_session_id`.
- Proof URL validation is length-only in the inspected model; downstream fetching behavior and SSRF exposure are **NÃO VALIDADO**.
- Full CSRF, XSS, SSRF, secret management, encryption-at-rest, session revocation, audit-log tamper resistance and dependency advisories are **NÃO VALIDADO**.

### 3.4 Multi-tenancy judgment

Miru is **ADAPT**, not production READY, for commercial multi-tenant BIMSpend.

Positive evidence:

- Company-bound agent.
- User must remain employed in that company.
- Default project must belong to the company.
- Agent ingestion resolves projects through company/user project scope.
- Timesheet model validates agent/company/user consistency.

Required validation:

1. Negative cross-company API tests for every reused endpoint.
2. Concurrency tests when one person belongs to multiple workspaces.
3. Tenant-scoped exports, background jobs, storage keys, logs and caches.
4. Database constraints for external ingestion idempotency.
5. Security review of super-admin/internal analytics surfaces.

## 4. ActivityWatch static audit (P1-03)

### 4.1 Existing reusable components

| Capability | Evidence | Classification |
|---|---|---|
| Active application/window title | aw-watcher-window emits `app` and `title` heartbeats | READY locally |
| Idle/AFK state | aw-watcher-afk emits `afk` / `not-afk` | READY locally |
| Local bucket/event API | aw-server `/api/0` endpoints; aw-client wrappers | READY locally |
| Heartbeat coalescing | client/watchers use `pulsetime` | READY |
| Local history/query/export | aw-server + web UI | READY locally |
| Privacy filtering for window events | drop/redact rules in aw-watcher-window | CONFIGURE |
| Windows startup/desktop packaging | aw-qt and aw-tauri autostart; Windows registry/MSI described | CONFIGURE; runtime NÃO VALIDADO |
| Authenticated cloud fleet ingestion | not an ActivityWatch responsibility | BUILD in BIMSpend boundary |
| Multi-tenant manager dashboard | local-first system, not established | BUILD/Reuse Miru |
| Reliable BIM project attribution | app/title alone is insufficient | BUILD small correlation layer |

### 4.2 API and security posture

The Python server defaults to `host = "localhost"`, port 5600 and empty custom CORS origins. The Rust server defaults to `127.0.0.1` and local origins. Host-header/CORS protections exist, including special browser-extension handling.

Recommendation: keep ActivityWatch bound to loopback, never expose it directly to LAN or internet, and do not send raw window titles to Miru. The BIMSpend adapter should:

1. read only required local buckets;
2. redact/minimize locally;
3. correlate with Revit signals;
4. queue encrypted summaries/evidence;
5. authenticate to Miru/BIMSpend using a revocable device/agent credential.

The local API was not penetration-tested. Whether all packaged configurations bind safely and whether other local processes can write fabricated events are **NÃO VALIDADO**. Treat ActivityWatch evidence as untrusted input.

### 4.3 Accuracy limitations

- Foreground window time is observed attention, not productive effort.
- AFK thresholds can reduce obvious idle time but cannot detect meetings, reading, phone work or passive review.
- Window titles may include model, customer, email, document or sensitive text.
- Multiple monitors do not create multiple foreground Windows applications; one foreground window remains only a proxy for attention.
- Crashes, sleep, RDP, lock screen, UAC/secure desktop and watcher restarts require explicit tests.
- The optional input watcher is not needed for the initial PoC and should be excluded to minimize surveillance.

## 5. Revit read-only connector feasibility (P1-04)

### 5.1 Official API evidence

Autodesk documentation confirms:

- `Application.DocumentOpened` fires after a document open completes and exposes status.
- `DocumentClosing/DocumentClosed`, save and reload/synchronization-related application events are available.
- `UIApplication.ViewActivated` identifies an activated view/document.
- A Revit process can have multiple documents and views open; the top-most active view determines the active document.
- `UIApplication.Idling` means the API is in a safe callable state, not that the human is inactive. It may stop firing for long periods in default mode when the user leaves; repeated mode can continue even with no user activity. It must not be used as a productivity timer.
- `BasicFileInfo` can expose worksharing state, version and central path for local/server files.
- Revit 2025+ moved to .NET 8, while older supported releases use .NET Framework 4.8; Autodesk describes multi-targeting from one codebase.
- Production add-ins should be digitally signed; otherwise Revit presents trust prompts.

### 5.2 Identity strategy

Use a hierarchy, never only the visible filename:

1. Explicit administrator mapping: BIMSpend commercial project ID ↔ approved model identity.
2. ACC/cloud model identifiers when the API provides stable cloud/project/model identity.
3. Workshared central/server identity, including normalized central path and available central GUID/episode information.
4. Local standalone file: normalized path plus file/document fingerprint; treat Save As/rename as a remapping event.
5. Unsaved/new documents: temporary session identity, never auto-post approved project time.

Hash identifiers before transmission where practical; do not transmit full local paths or usernames by default.

### 5.3 Multiple processes and documents

Each Revit process should have its own connector instance and process/session ID. It emits active-document transitions but does not calculate final time. The external adapter correlates:

- Windows foreground process/window;
- Revit process/session;
- active Revit document/view;
- AFK state;
- mapping confidence.

This prevents two open Revit processes or several open documents from double-counting. Only the foreground Revit process plus its active document can produce high-confidence observed Revit time; all ambiguity is retained for review.

### 5.4 Version and maintenance plan

- Shared source with thin version-specific build projects/manifests.
- Separate signed binaries for .NET Framework-era and .NET 8-era Revit releases.
- Read-only event subscriptions; no transactions and no document modifications.
- Minimal payload and no element-level telemetry in first PoC.
- CPU/UI latency budget tested because heavy Idling handlers can slow Revit.

Live Revit behavior, ACC identity values, multi-window behavior and compatibility across each supported release are **NÃO VALIDADO**.

## 6. Fork vs API/adapter decision (P1-05)

| Option | Reuse | Upgrade cost | License/security boundary | Recommendation |
|---|---:|---:|---|---|
| Deep Miru fork + embed ActivityWatch logic | High initially | Very high | mixes web, local collector and MPL files | NO |
| Miru fork with BIMSpend domain changes + ActivityWatch adapter | High | Medium | clear MIT web fork and separate MPL collector | CONDITIONAL later |
| Miru upstream-like deployment + extension/API layer | Highest sustainable | Low/medium | cleanest boundary; uses existing agent API | **PREFERRED FIRST** |
| Fork ActivityWatch and make it cloud multi-tenant | Misleading | Very high | conflicts with local-first assumptions | NO |
| Local ActivityWatch unmodified + BIMSpend adapter | High | Medium | keeps MPL component separable | **PREFERRED FIRST** |
| Custom window/idle collector | Low | High | proprietary but duplicates mature code | HOLD as fallback |
| Revit connector writes directly to cloud | Medium | Medium/high | credentials/network logic inside every Revit build | NO |
| Revit connector → local adapter | High | Low/medium | one secure sync boundary | **PREFERRED** |

Fork Miru only after the PoC proves which UI/data changes cannot be achieved through configuration and narrow extensions. Avoid modifying ActivityWatch covered files unless required; prefer invoking its stable local API.

## 7. Feature reuse matrix (P1-05/P1-07)

| BIMSpend capability | Status | Source / action |
|---|---|---|
| Company, client, project, team | READY | Miru |
| Roles: manager full, designer own time | CONFIGURE | Miru roles/policies; verify manager role coverage |
| Manual timesheets and corrections | READY | Miru |
| Automated draft time entry | READY/CONFIGURE | Miru agent API |
| Automated evidence/provenance | CONFIGURE | Existing metadata fields; define safe schema |
| Review/approval of automated entries | READY/ADAPT | Existing review status; UX/workflow validation |
| Invoice and billed-hour records | READY/ADAPT | Miru invoices/timesheets; preserve billed distinction |
| Standard rates and loaded internal cost | ADAPT | Miru financial model must be mapped carefully |
| Actual-vs-billed realization | ADAPT | reports/calculations required |
| Historical reports/export | READY/ADAPT | Miru reports plus BIM metrics |
| Window/AFK observation | READY locally | ActivityWatch |
| Privacy title redaction | CONFIGURE | ActivityWatch privacy filters + adapter rules |
| Secure device-to-cloud sync | BUILD | Small BIMSpend adapter boundary |
| Offline queue/retry/idempotency | BUILD/ADAPT | Adapter + server uniqueness |
| Revit document/view signals | BUILD | Small read-only connector |
| Model-to-commercial-project mapping | BUILD | Admin mapping + confidence workflow |
| Multi-process deduplication | BUILD | Adapter correlation |
| Raw event retention UI | UNKNOWN | Avoid until policy approved |
| PWA/offline manager dashboard | UNKNOWN | Responsive web exists; PWA need not be MVP |
| Enterprise SSO | CONFIGURE/UNKNOWN | Miru route exists; runtime validation required |

## 8. Threat, privacy and legal risk register (P1-06)

| Risk | Severity | Mitigation / acceptance condition |
|---|---|---|
| Employee surveillance without proper notice/authority | Critical | Australian legal/employment review; written policy, consent/notice, access transparency; pilot only with consenting synthetic/test users |
| Window titles expose customer/health/password/document data | Critical | local allowlist/redaction; never collect keystrokes/screenshots; minimize and hash; retention limits |
| Cross-tenant data leakage | Critical | negative isolation tests across API, exports, jobs, files, caches and backups |
| Agent token theft/replay | High | OS credential protection, rotation/revocation, short device identity, TLS, rate limits, anomaly logs |
| Duplicate automated entries | High | server idempotency key/unique constraint and replay tests |
| Fabricated local ActivityWatch events | High | treat as untrusted evidence; correlate Revit/AFK/process; review before approval |
| Activity equals productive/billable inference | Critical | explicit metric names and review; never auto-invoice from observed activity |
| MPL distribution non-compliance | High | preserve notices; publish covered modified source when distributed; legal sign-off |
| Upstream divergence | High | narrow patches, pinned upgrades, upstream-first contributions, quarterly rebase budget |
| Unsigned Revit add-in | High | code-sign binaries and installer; verify trusted publisher deployment |
| Revit UI slowdown/crash | High | read-only handlers, bounded payload, latency/crash tests, kill switch |
| Cloud/offline loss | High | durable local queue, encrypted storage, acknowledgement and replay |
| Excessive retention | High | tenant policy, deletion/export, minimum raw-event TTL, aggregated long-term data |
| Manager over-access | High | manager finance role; designer own-history only; audited privileged access |
| Secrets in logs/repo | High | synthetic fixtures, secret manager, log redaction, automated secret scan |
| Dependency vulnerabilities | High | SBOM, Bundler/npm/Python/Rust/container scans at every pinned release |

Legal compliance and workplace-surveillance requirements are **NÃO VALIDADO** and require qualified Australian advice before any employee pilot.

## 9. Staged proposal, tasks and estimates (P1-07)

Estimates are engineering effort ranges, not commitments, and exclude legal review, procurement and app-store/certificate lead time.

### Gate B2-A — Reproducible baselines (3–5 engineer-days)

1. Create isolated workspaces at pinned SHAs.
2. Record recursive ActivityWatch submodule SHAs.
3. Generate SBOM/license inventory.
4. Run documented Miru and ActivityWatch builds/tests.
5. Run static dependency/security scans.
6. Capture exact prerequisites, failures and clean teardown.

Acceptance:

- No user production device changes.
- All commands reproducible from a clean environment.
- Licenses/notices enumerated.
- Test and scan output attached with failures, not summarized away.
- Stop if build cannot be reproduced or license blockers appear.

### Gate B2-B — Contract-only integration design (2–4 engineer-days)

1. Define synthetic event and mapping schemas.
2. Define device/agent authentication, idempotency and retry contract.
3. Define retention/redaction defaults.
4. Map Miru agent endpoint gaps without implementing them.
5. Threat-model the data flow.

Acceptance:

- JSON schemas and sequence tests approved.
- No raw title/path leaves device in default configuration.
- Metrics are named separately: observed, attributed, approved, billed, cost.
- Cross-tenant and replay cases specified.

### Gate B3-A — Local signal PoC (5–8 engineer-days)

After separate approval:

1. Run ActivityWatch locally with window + AFK only.
2. Build minimal read-only Revit connector for one selected Revit version.
3. Correlate synthetic/test signals locally.
4. Display a local review record; no cloud upload initially.

Acceptance:

- Two Revit processes and two open documents do not double-count.
- AFK interval is excluded/flagged.
- rename/Save As creates a remapping state.
- connector performs no document transaction.
- measured Revit UI overhead meets an agreed threshold.
- failures/restarts do not silently invent time.

### Gate B3-B — Miru ingestion PoC (5–10 engineer-days)

1. Add/validate idempotent automated draft ingestion.
2. Upload only minimized synthetic summaries.
3. Verify manager vs designer visibility.
4. Verify review, correction, approval and billed separation.
5. Run tenant-negative and replay tests.

Acceptance:

- repeated upload produces one draft entry;
- wrong-tenant project IDs are rejected;
- designer cannot view another designer's records or finance;
- manager access is audited;
- approved time never automatically becomes billed;
- offline replay is lossless and bounded.

### Gate B4 — Product/security/pilot planning (8–15 engineer-days plus external review)

Only after both PoCs pass: production threat model, data protection impact assessment, Australian workplace/privacy legal review, support matrix, signing/update architecture, backup/restore and pilot plan.

## 10. Stop/go decision

**GO, after explicit user approval:** Gate B2-A only — isolated reproducible baseline and license/security inventory.

**HOLD:** coding the Windows adapter, Revit connector, Miru modifications or branded UI until B2-A and B2-B evidence is reviewed.

**NO-GO:** exposing ActivityWatch server to the internet; equating foreground time with actual/billable time; deep-merging ActivityWatch into Miru; deploying to employees; touching FBT Revit Academy.

## 11. Evidence index

### Miru pinned source

- [Pinned commit](https://github.com/saeloun/miru-web/commit/10e457e1d0cd2ac782be9d1edbcbd5a1a573486a)
- [MIT LICENSE](https://github.com/saeloun/miru-web/blob/10e457e1d0cd2ac782be9d1edbcbd5a1a573486a/LICENSE)
- [Gemfile](https://github.com/saeloun/miru-web/blob/10e457e1d0cd2ac782be9d1edbcbd5a1a573486a/Gemfile)
- [package.json](https://github.com/saeloun/miru-web/blob/10e457e1d0cd2ac782be9d1edbcbd5a1a573486a/package.json)
- [API routes](https://github.com/saeloun/miru-web/blob/10e457e1d0cd2ac782be9d1edbcbd5a1a573486a/config/routes/api.rb)
- [Agent authentication](https://github.com/saeloun/miru-web/blob/10e457e1d0cd2ac782be9d1edbcbd5a1a573486a/app/controllers/api/v1/agent/base_controller.rb)
- [Agent timesheet ingestion](https://github.com/saeloun/miru-web/blob/10e457e1d0cd2ac782be9d1edbcbd5a1a573486a/app/controllers/api/v1/agent/timesheet_entries_controller.rb)
- [Agent key model](https://github.com/saeloun/miru-web/blob/10e457e1d0cd2ac782be9d1edbcbd5a1a573486a/app/models/agent_key.rb)
- [Timesheet model](https://github.com/saeloun/miru-web/blob/10e457e1d0cd2ac782be9d1edbcbd5a1a573486a/app/models/timesheet_entry.rb)
- [Timesheet policy](https://github.com/saeloun/miru-web/blob/10e457e1d0cd2ac782be9d1edbcbd5a1a573486a/app/policies/timesheet_entry_policy.rb)
- [Project policy](https://github.com/saeloun/miru-web/blob/10e457e1d0cd2ac782be9d1edbcbd5a1a573486a/app/policies/project_policy.rb)
- [Rate limits](https://github.com/saeloun/miru-web/blob/10e457e1d0cd2ac782be9d1edbcbd5a1a573486a/config/initializers/rack_attack.rb)
- [Dockerfile](https://github.com/saeloun/miru-web/blob/10e457e1d0cd2ac782be9d1edbcbd5a1a573486a/Dockerfile)
- [Security policy](https://github.com/saeloun/miru-web/blob/10e457e1d0cd2ac782be9d1edbcbd5a1a573486a/SECURITY.md)

### ActivityWatch pinned source

- [Bundle commit](https://github.com/ActivityWatch/activitywatch/commit/9fee4702fea08dbe0149cc6e28f4ef66b49f54ec)
- [MPL-2.0 LICENSE](https://github.com/ActivityWatch/activitywatch/blob/9fee4702fea08dbe0149cc6e28f4ef66b49f54ec/LICENSE.txt)
- [Submodule inventory](https://github.com/ActivityWatch/activitywatch/blob/9fee4702fea08dbe0149cc6e28f4ef66b49f54ec/.gitmodules)
- [Bundle build](https://github.com/ActivityWatch/activitywatch/blob/9fee4702fea08dbe0149cc6e28f4ef66b49f54ec/Makefile)
- [aw-server REST API](https://github.com/ActivityWatch/aw-server/blob/994ea988ca30af36e08cef71ce6046e8c3391584/aw_server/rest.py)
- [aw-server local configuration](https://github.com/ActivityWatch/aw-server/blob/994ea988ca30af36e08cef71ce6046e8c3391584/aw_server/config.py)
- [aw-client](https://github.com/ActivityWatch/aw-client/blob/c88cf12c6fb122447157c183322eb2b5c12e6266/aw_client/client.py)
- [Window watcher](https://github.com/ActivityWatch/aw-watcher-window/blob/12000f58d16b8fc1376af42755c688b3d7157280/aw_watcher_window/main.py)
- [Window privacy filter](https://github.com/ActivityWatch/aw-watcher-window/blob/12000f58d16b8fc1376af42755c688b3d7157280/aw_watcher_window/privacy_filter.py)
- [AFK watcher](https://github.com/ActivityWatch/aw-watcher-afk/blob/b4839261688eb7980d1730d46dd35a36b21cfc1d/aw_watcher_afk/afk.py)
- [Windows/local Rust server defaults](https://github.com/ActivityWatch/aw-server-rust/blob/10b4b7f2dde11efbf84f63a96c88088330259c97/aw-server/src/config.rs)
- [Tauri desktop capabilities](https://github.com/ActivityWatch/aw-tauri/blob/d3b5527ce99547159ba1f7fbda00ae9b605d5cbb/README.md)

### Autodesk official documentation

- [DocumentOpened event](https://help.autodesk.com/cloudhelp/2026/ENU/Revit-API-MainReference/files/html/b9415c2d-442e-f61d-aafa-de31cce7959b.htm)
- [Document/Application event inventory](https://help.autodesk.com/cloudhelp/2026/ENU/Revit-API-MainReference/files/html/94db8ea8-d2c3-5e71-8030-466bcb8e4426.htm)
- [Idling event limitations](https://help.autodesk.com/cloudhelp/2026/ENU/Revit-API-MainReference/files/html/56145d84-e948-730a-dc72-2a7b88a50a99.htm)
- [BasicFileInfo](https://help.autodesk.com/cloudhelp/2026/ENU/Revit-API-MainReference/files/html/475edc09-cee7-6ff1-a0fa-4e427a56262a.htm)
- [.NET 8 migration and multi-release support](https://help.autodesk.com/cloudhelp/2026/ENU/Revit-API/files/Revit_API_Developers_Guide/Introduction/Getting_Started/Using_the_Autodesk_Revit_API/Revit_API_Revit_API_Developers_Guide_Introduction_Getting_Started_Using_the_Autodesk_Revit_API_NET8_Update_html.html)
- [Digitally signing a Revit add-in](https://help.autodesk.com/cloudhelp/2027/ENU/Revit-API/files/Revit_API_Developers_Guide/Introduction/Add_In_Integration/Revit_API_Revit_API_Developers_Guide_Introduction_Add_In_Integration_Digitally_Signing_Your_Revit_Add_in_html.html)

## 12. Validation statement

Completed: repository metadata and pinned-commit static inspection, license inspection, selected dependency/manifests, Miru agent/time/project/auth/policy paths, ActivityWatch local watcher/API/security defaults, and official Revit API feasibility research.

**NÃO VALIDADO:** clean builds, test suites, exact recursive ActivityWatch gitlinks, runtime API behavior, Windows packaging/install/update, CPU/memory accuracy, live Revit/ACC behavior, vulnerability/CVE scans, SBOM completeness, penetration testing, multi-tenant negative testing, backups, legal compliance and production readiness.

No BIMSpend product code, FBT Revit Academy content or user machine installation was changed.
