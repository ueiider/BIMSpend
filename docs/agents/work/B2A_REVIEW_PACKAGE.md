# BIMSpend — B2-A Review Package

Date: 2026-11-05  
Authoring agent: ChatGPT Work — Lead Architect / Project Coordinator  
Mode: **B2-A PLAN CONSOLIDATION ONLY**  
Branch: `agent/work-b2a`  
Decision: **REVIEW REQUIRED — GATE B2-A IS NOT APPROVED**

## 1. Review scope and evidence chain

This package independently reviews both OpenCode research reports—the B2-A execution plan and the reuse implementation matrix—against the current planning baseline. No builds, tests, scans, installations or product changes were performed.

### BIMSpend planning baseline

The review branch was created from `main` commit:

- `eb13fc90eb768080f6790bb364b482274860688c`
- [Main baseline commit](https://github.com/ueiider/BIMSpend/commit/eb13fc90eb768080f6790bb364b482274860688c)

Documents reviewed from that baseline:

- `CONTEXT_FOR_AI.md`
- `MASTER_PLAN.md`
- `TASK_TRACKER.md`
- `AI_HANDOFF.md`
- `docs/technical-feasibility/PLAN_AUDIT_REPORT.md`

### OpenCode evidence

OpenCode branch and exact head were verified remotely:

- Branch: `agent/opencode-b2a`
- Commit: `73e54ab583d76e6f3b018aaeb5449a1c42c91b9a`
- [OpenCode commit](https://github.com/ueiider/BIMSpend/commit/73e54ab583d76e6f3b018aaeb5449a1c42c91b9a)
- [OpenCode execution plan](https://github.com/ueiider/BIMSpend/blob/agent/opencode-b2a/docs/agents/opencode/B2A_EXECUTION_PLAN.md)

The OpenCode commit changes only `docs/agents/opencode/B2A_EXECUTION_PLAN.md`. Its parent/base is the same reviewed main baseline. The OpenCode report was not modified.

The reuse-matrix branch and exact head were also verified remotely:

- Branch: `agent/opencode-reuse-matrix`
- Commit: `b26c6d1a97f270a55d6669916b1369339d1fc98d`
- [Reuse-matrix commit](https://github.com/ueiider/BIMSpend/commit/b26c6d1a97f270a55d6669916b1369339d1fc98d)
- [OpenCode reuse implementation matrix](https://github.com/ueiider/BIMSpend/blob/b26c6d1a97f270a55d6669916b1369339d1fc98d/docs/agents/opencode/REUSE_IMPLEMENTATION_MATRIX.md)

That commit changes only `docs/agents/opencode/REUSE_IMPLEMENTATION_MATRIX.md` and is also based on the reviewed `main` baseline. Neither OpenCode report was modified.

## 2. Consolidated architecture position

The OpenCode plan does not contradict the preferred product architecture because it is limited to baseline reproducibility.

The governing architecture remains:

1. Miru as the administrative/commercial web foundation.
2. ActivityWatch as an optional local-only signal collector.
3. A future BIMSpend adapter as the sole cloud sync/correlation boundary.
4. A future read-only, versioned Revit connector that reports signals to the local adapter.
5. Separate records for observed activity, attributed time, approved time, billed hours and loaded internal cost.

B2-A must not create the adapter, Revit connector, cloud ingestion, branded UI or product behavior. It only determines whether pinned upstreams can be reproduced, inventoried and assessed safely.

## 3. Verified upstream revisions

### Primary pins

| Component | Pinned revision | Evidence status |
|---|---|---|
| Miru | `10e457e1d0cd2ac782be9d1edbcbd5a1a573486a` | Verified upstream commit; pinned by PLAN audit and OpenCode |
| ActivityWatch bundle | `9fee4702fea08dbe0149cc6e28f4ef66b49f54ec` | Verified upstream commit; pinned by PLAN audit and OpenCode |

### ActivityWatch gitlinks reported by OpenCode

All listed commit objects were independently confirmed to exist in their named remote repositories:

| Submodule | Gitlink SHA | Independent existence check |
|---|---|---|
| aw-client | `fe106969fcd413ffadbd5a9d3b75808cc636cd54` | Verified |
| aw-core | `28c3acf047b225f90592e1c47c8ec2596612d70b` | Verified |
| aw-notify-rs | `87e83cca65276b2278e4361db74087764c3ecf2c` | Verified |
| aw-qt | `bbccb715516c5c02f863f883680aee0e40c803b5` | Verified |
| aw-server | `67cfb479a9f8511ad3a9595224cb22c35b9dbe65` | Verified |
| aw-server-rust | `fe558c4f106a70004a42bc30558c7438f8b66b4f` | Verified |
| aw-tauri | `44b92d45878504fc7b9d1d9e867e8967cccd9b17` | Verified |
| aw-watcher-afk | `b4839261688eb7980d1730d46dd35a36b21cfc1d` | Verified |
| aw-watcher-input | `4e6461dbf55a1c1aa8f9ece4df5f109188f56f61` | Verified |
| aw-watcher-window | `10638b2c94e46195f709abd8626cb15f911e99f8` | Verified |
| awatcher | `c32ca62c66e6ff4f2949b841ec20d30c778d11ba` | Verified |

Important distinction: the PLAN audit recorded several component **branch heads observed during static inspection**. OpenCode recorded the bundle's **gitlink revisions**. Differences are not automatically contradictions. For a reproducible ActivityWatch bundle, gitlinks at the pinned umbrella commit are authoritative. Gate B2-A still needs a clean checkout followed by recursive submodule initialization and `git submodule status --recursive` to prove the complete checkout.

## 4. OpenCode findings accepted

The following findings align with the PLAN audit:

- The primary upstream pins are correct.
- The ActivityWatch bundle is submodule-based and requires recursive evidence.
- Required runtimes/toolchains are not currently validated as available in an approved isolated executor.
- No SBOM, license scan, CVE scan, clean build or test run has occurred.
- ActivityWatch MPL-2.0 obligations remain a distribution risk requiring a complete component/license inventory.
- Gate B2-A remains blocked until explicit human approval.
- B2-A must not implement BIMSpend, B2-B or B3.
- Evidence must retain failures and must not imply production readiness.

The OpenCode report adds useful exact gitlink candidates and manifest-derived prerequisite versions, but those remain plan evidence rather than proof of a successful environment or build.

## 5. Open-Source Reuse Findings

Source: [OpenCode reuse implementation matrix at `b26c6d1a97f270a55d6669916b1369339d1fc98d`](https://github.com/ueiider/BIMSpend/blob/b26c6d1a97f270a55d6669916b1369339d1fc98d/docs/agents/opencode/REUSE_IMPLEMENTATION_MATRIX.md). These findings are consolidated with the [B2-A plan at `73e54ab583d76e6f3b018aaeb5449a1c42c91b9a`](https://github.com/ueiider/BIMSpend/blob/73e54ab583d76e6f3b018aaeb5449a1c42c91b9a/docs/agents/opencode/B2A_EXECUTION_PLAN.md).

### 5.1 Architecture implications accepted

The reuse matrix strengthens—but does not yet runtime-validate—the composition architecture:

| Boundary | Reuse conclusion | Work review |
|---|---|---|
| Miru business foundation | Strong reuse candidate for users, companies, clients, projects, roles, timesheets, invoices, reports and exports | Preserve. Treat security, tenancy and exact BIMSpend semantics as unvalidated until tested |
| Miru agent API | Best initial ingestion boundary: Agent/AgentKey, company/user binding, project scope, proof/source metadata and external run/session fields | Preserve. Idempotency uniqueness, device credential hardening and agent-specific rate limiting remain gaps |
| ActivityWatch local monitoring | Candidate for foreground-window and AFK signals through a loopback API | Preserve local-only separation. Exact pinned-gitlink implementation remains unverified |
| BIMSpend Windows adapter | No upstream equivalent; correlation, minimization, offline queue, retry and idempotency are custom | Future BUILD only; not B2-A |
| Read-only Revit connector | No upstream equivalent; versioned .NET builds and event signals are custom | Future BUILD only; not B2-A |
| Project mapping and metric separation | No upstream implementation proves model-to-commercial-project mapping or observed/approved/billed separation | Future domain design/build; not B2-A |

### 5.2 High-value Miru reuse candidates

Static source evidence supports carrying these into later validation:

- Devise/JWT/MFA/passkey authentication foundation.
- Rolify/Pundit company- and resource-scoped authorization.
- Company, client, project, user and project-membership records.
- Timesheet entries with bill and review states, audit history and automation/proof metadata.
- Agent/AgentKey ingestion boundary.
- Existing dashboards, reports, CSV/PDF export and invoice linkage.
- Desktop timer state as a reference for UI/state patterns.

These are candidates, not blanket “reuse as-is” approvals. The matrix's A/B/C labels express estimated adaptation effort; they do not prove production fitness, tenant isolation, data-model correctness or API compatibility at runtime.

### 5.3 Required corrections to reuse claims

1. **Internal loaded cost is not verified.** `ProfitabilityBillingRate` is evidence of a billing/charge rate, not proof of the employer's loaded internal hourly cost. BIMSpend must keep loaded cost separate and may require a new protected model.
2. **Offline synchronization is not established.** A `synced_at` field on the desktop timer does not demonstrate a durable encrypted queue, acknowledgements, retries or idempotent replay.
3. **External IDs are not proven idempotent.** Presence of `external_run_id` and `external_session_id` does not prove unique constraints or replay safety.
4. **Agent credentials are not yet device credentials.** AgentKey is reusable foundation, but storage, rotation, expiry, device binding, revocation propagation and rate limiting require validation/design.
5. **Approval workflow needs behavior tests.** A review-status enum does not itself prove the intended designer/manager workflow, audit requirements or separation from billing.
6. **“Unchanged upstream” is a target, not a fact.** API-first integration is preferred, but the need for narrow Miru extensions cannot be ruled out before contract and runtime tests.
7. **ActivityWatch details at bundle gitlinks remain unverified.** OpenCode explicitly did not initialize the submodules. Paths, endpoints, privacy filters, port/bind defaults, payloads and packaging behavior cited for those exact gitlinks must be inspected during an approved baseline.
8. **Local machine inventory is not an execution prerequisite.** Versions and free space observed on `D:` are transient and must not drive the plan; the approved disposable executor manifest is authoritative.
9. **Optional input monitoring should be excluded by default.** `aw-watcher-input` may be inventoried for license completeness, but its use would increase surveillance scope and is not required for the first product hypothesis.

### 5.4 Gate-scope contradiction

The reuse matrix's implementation priority list is useful for future roadmap planning, but its recommendation to prioritize items 1–8 “upon explicit approval of Gate B2-A” is out of scope. Agent setup, company/project provisioning, ActivityWatch API probing, adapter skeleton work, workflow configuration, billing mapping and dashboard adaptation are not B2-A baseline activities.

Under B2-A, permitted work remains only:

- isolated checkout at pinned revisions;
- recursive gitlink capture;
- canonical clean builds/tests;
- SBOM/license/NOTICE inventory;
- dependency and security scans;
- evidence, teardown and stop/go report.

Every integration, configuration against a running service, probe using live watchers, schema/workflow change or BIMSpend implementation requires a later, separately approved gate.

### 5.5 Reconciled reuse classification

| Capability | Consolidated status before B2-A | Reason |
|---|---|---|
| Miru company/client/project foundation | REUSE CANDIDATE — high confidence static | Direct source evidence; runtime/tenant tests outstanding |
| Miru authentication/RBAC | CONFIGURE/ADAPT | Strong components; BIMSpend roles and security tests outstanding |
| Miru agent timesheet ingestion | CONFIGURE/ADAPT | Best boundary; idempotency/rate-limit/device gaps |
| Miru timesheet review and billing linkage | CONFIGURE/ADAPT | Existing fields/models; semantics and workflow unverified |
| Miru reports/export/dashboard | CONFIGURE/ADAPT | Existing features; BIMSpend metrics are not present |
| Internal loaded cost | BUILD/UNKNOWN | Billing-rate evidence is not loaded-cost evidence |
| ActivityWatch window/AFK/API | NOT VERIFIED AT PINNED GITLINKS | Submodule source was not initialized by OpenCode |
| ActivityWatch packaging/autostart/privacy behavior | NOT VERIFIED | Requires exact-gitlink source inspection and approved runtime tests |
| Durable offline synchronization | BUILD | Neither report proves the required adapter queue/replay contract |
| Windows adapter | BUILD | No upstream equivalent |
| Read-only Revit connector | BUILD | No upstream equivalent |
| Model/project identity mapping | BUILD | BIMSpend-specific |
| Observed/attributed/approved/billed separation | BUILD/ADAPT MIRU | Domain layer absent; Miru records are downstream targets |

### 5.6 B2-A evidence added by the reuse matrix

The matrix contributes:

- more detailed Miru source paths and candidate capability mapping;
- a future reuse/adaptation roadmap;
- a clear admission that ActivityWatch submodule implementation was not read;
- environment observations that explain why a disposable, provisioned executor is required;
- confirmation that builds, scans and dependencies were not executed.

It does not close any B2-A runtime acceptance criterion. It adds no clean-build, test, SBOM, license-scan, vulnerability-scan, Windows-packaging or legal evidence.

## 6. Contradictions and corrections required

### 6.1 Command and evidence issues

| OpenCode proposal | Review finding | Required correction before execution |
|---|---|---|
| Run `git submodule status --recursive` before initialization | Uninitialized nested submodules cannot provide a complete recursive checkout/status | Initialize with the pinned umbrella checkout using `git submodule update --init --recursive`, then capture status and URLs |
| `bundle licenses` | This is not a standard Bundler command and no supporting tool was established in the reviewed plan | Select and pin an approved Ruby license/SBOM tool; verify it exists before treating output as evidence |
| Copy lockfiles/manifests as “SBOM/license inventory” | Lockfiles are inputs, not a complete SBOM or license conclusion | Generate CycloneDX/SPDX or equivalent inventories and separately preserve manifest hashes |
| Commands use `|| true` | This masks command failure and conflicts with the requirement to preserve failures | Capture exit code, stdout and stderr explicitly; never convert failed mandatory checks into success |
| `bundle exec rails spec` | The audited Miru project declares RSpec; this command is not established as its test runner | Derive the canonical command from repository CI/documentation, expected to be `bundle exec rspec` only if confirmed |
| `bundle exec rake i18n:config` | No evidence was provided that this is a build prerequisite | Remove unless the pinned repository's CI/build documentation requires it |
| ActivityWatch `make` “or equivalent” | “Or equivalent” is not reproducible | Use exact upstream targets and platform path, such as the documented target after verifying the pinned Makefile/CI |
| Security tool list says “safety, bandit, cargo audit” | Tools and versions are not pinned; installation changes the environment | Define exact scanner names, versions, source and invocation in an approved disposable executor |
| “Clean teardown: no changes to user's machine” | Installing runtimes/toolchains directly would still change the machine before teardown | Execute in disposable VM/container/managed runner or explicitly approved isolated environment; do not use the user's normal workstation |
| Commit full copied lockfiles | Duplicates upstream material and may create large/noisy evidence | Prefer SHA-256 hashes, machine-readable SBOMs and concise reports; attach raw logs only when size/privacy policy allows |

### 6.2 Source-reference issue

The OpenCode table cites numbered sections such as “MASTER_PLAN §10/§11/§18”, but the reviewed `MASTER_PLAN.md` is organized by headings and does not contain those numbered sections. The underlying constraints are broadly consistent, but those citations are inaccurate and must not be treated as precise evidence.

### 6.3 Local clone evidence

The OpenCode report cites `D:\BIMSpend\Research\Repos\...` as local verification. Those local clones are not the persistent source of truth and are not independently reproducible evidence. GitHub commits and the future clean B2-A checkout must remain authoritative. No future plan should depend on those paths.

## 7. Missing prerequisites

Before B2-A execution can begin, Claude should require explicit resolution of:

1. **Human approval:** explicit approval for Gate B2-A only.
2. **Executor selection:** disposable Windows VM, managed runner or other isolated executor; no installation on the user's normal computer.
3. **Network authorization:** permission to clone upstream repositories/submodules and download pinned dependencies/scanner databases.
4. **Resource budget:** disk, RAM, CPU and maximum run duration, especially for 11 ActivityWatch submodules and Miru assets/tests.
5. **Platform matrix:** decide whether B2-A proves Linux/container buildability, Windows packaging, or both. A Linux-only pass cannot validate Windows packaging.
6. **Exact canonical commands:** derive from pinned CI/configuration rather than guesses.
7. **Tool manifest:** pin Docker/VM image, Git, Ruby, Bundler, Node, pnpm, PostgreSQL, Python, Poetry, Rust and all scanners.
8. **SBOM formats:** CycloneDX or SPDX, per ecosystem and combined inventory.
9. **License policy:** define allowed, review-required and prohibited licenses; include fonts, icons, assets, container layers and transitive packages.
10. **Vulnerability policy:** define severity threshold, treatment of no-fix findings, accepted scanner freshness and false-positive handling.
11. **Evidence policy:** approved filenames, maximum sizes, redaction rules, checksums and whether raw logs belong in Git or release artifacts.
12. **Secret/privacy controls:** synthetic config only; scan logs before commit for paths, usernames, tokens and environment values.
13. **Teardown verification:** confirm temporary resources and credentials are removed without deleting unrelated user data.
14. **Branch ownership:** name the execution branch and reviewer; do not append execution evidence to the immutable OpenCode preparation branch unless explicitly authorized.

## 8. Dependency and licensing risks

| Risk | Status | Required evidence |
|---|---|---|
| Miru top-level MIT | Verified at pinned commit | Preserve notice; inventory third-party code/assets |
| ActivityWatch umbrella MPL-2.0 | Verified at pinned commit | Identify every covered distributed file and source-offer obligation |
| Eleven ActivityWatch submodules | Commit existence verified; licenses not consolidated | Recursive license/NOTICE and vendored-code inventory at exact gitlinks |
| npm/pnpm, Ruby, Python and Rust transitive licenses | NOT VALIDATED | Ecosystem SBOM plus license scan |
| Fonts, icons, images, browser/runtime assets | NOT VALIDATED | Asset provenance and redistribution review |
| Container/base OS packages | NOT VALIDATED | Image digest, OS package SBOM and notices |
| Scanner/tool licenses | NOT VALIDATED | Include tools used in the reproducibility environment |
| Trademark/branding rights | Not granted by code licenses | Do not reuse upstream marks without separate clearance |
| GPL/AGPL dependency surprise | NOT VALIDATED | Stop and legal review if detected in a distributed boundary |
| MPL modifications mixed into proprietary files | Architectural risk | Prefer unmodified local ActivityWatch + separate adapter; legal review before distribution |

A vulnerability is not a license blocker, and a license concern is not a CVE. Evidence and decisions must keep these categories separate.

## 9. Security and privacy constraints

B2-A may use only public upstream source and synthetic/test configuration. It must not process company spreadsheets, employee/customer identities, Revit journals or production credentials.

Mandatory controls:

- No raw secrets or environment dumps in logs.
- No telemetry upload unless explicitly identified and disabled/approved.
- Pin external actions/images/tools by immutable digest or version.
- Verify downloaded artifacts/checksums where upstream provides them.
- Restrict build runner credentials to read-only upstream access and write access only to the approved BIMSpend evidence branch.
- Scan evidence for secrets and personal paths before commit.
- Preserve all failed scan/build statuses.
- Do not expose ActivityWatch server to LAN/internet.
- Do not run ActivityWatch watchers against the user's real desktop during B2-A.
- Do not interpret any observed activity as actual, approved or billable time.
- Do not test multi-tenancy or Miru ingestion with real people/data under this gate.

Cross-tenant security, agent-token behavior, local event fabrication, Revit performance and workplace surveillance compliance remain outside B2-A and **NOT VALIDATED**.

## 10. Corrected proposed build/test procedure

This is the procedure Claude should review. It is not authorization to execute.

### Stage 0 — Approval and immutable run manifest

- Record human approval reference, executor ID/image digest, branch, operator, UTC timestamp and scope.
- Record exact upstream SHAs and tool/scanner versions.
- Confirm synthetic configuration and network/evidence policies.

### Stage 1 — Clean isolated checkout

- Create a disposable workspace.
- Clone Miru and checkout `10e457e1d0cd2ac782be9d1edbcbd5a1a573486a`.
- Clone ActivityWatch and checkout `9fee4702fea08dbe0149cc6e28f4ef66b49f54ec`.
- Initialize recursively: `git submodule update --init --recursive`.
- Capture `git status --short`, `git rev-parse HEAD`, `git submodule status --recursive`, remote URLs and file hashes.
- Stop if a gitlink cannot be fetched or differs from the pinned tree.

### Stage 2 — Pre-build inventory

- Enumerate all license/NOTICE files, vendored code and assets before installing.
- Generate source/manifest hashes.
- Generate ecosystem SBOMs with pinned tools.
- Record every external download and resolved dependency.
- Stop for an unknown/unlicensed component or prohibited license.

### Stage 3 — Miru baseline

- Use the exact runtime versions required by the pinned source in the disposable executor.
- Follow pinned upstream CI/build documentation, not assumed commands.
- Prepare only synthetic database/configuration.
- Run dependency resolution, asset build, database preparation and canonical test suites.
- Run pinned Ruby/JavaScript/container security checks.
- Capture command, duration, exit code, stdout/stderr and resulting artifact hashes.

### Stage 4 — ActivityWatch baseline

- Follow the pinned bundle's platform-specific documented build target.
- Build/test the exact recursive gitlinks, not current component branch heads.
- Run Python/Rust/JavaScript dependency, license and vulnerability checks as applicable.
- On Windows, validate packaging only if Windows is explicitly in the approved matrix.
- Do not start watchers against the real user session.
- Capture the same structured evidence as Miru.

### Stage 5 — Reproducibility check

- Repeat the agreed critical build in a second clean instance or document why reproducibility was not established.
- Compare dependency locks, SBOMs and artifact hashes where deterministic output is expected.
- Mark nondeterministic differences and root causes; do not claim reproducibility from one successful run.

### Stage 6 — Evidence review and teardown

- Redact secrets/personal paths without altering technical pass/fail results.
- Commit only approved text/machine-readable evidence and checksums to a separate execution branch.
- Verify remote commit/file list.
- Destroy the disposable environment and verify teardown.
- Produce a B2-A stop/go recommendation. Do not begin B2-B/B3.

## 11. Acceptance criteria

B2-A passes only when all mandatory criteria have evidence:

- [ ] Explicit user approval for B2-A exists.
- [ ] Approved disposable executor and immutable environment manifest exist.
- [ ] Primary and recursive SHAs are captured and match the pinned bundle.
- [ ] Canonical upstream build/test commands are identified from pinned source.
- [ ] Miru baseline build and required tests complete with recorded exit codes.
- [ ] ActivityWatch baseline build and required tests complete for the approved platform matrix.
- [ ] SBOMs cover Ruby, JavaScript, Python, Rust, OS/container packages and bundled assets as applicable.
- [ ] Licenses/notices are enumerated and reviewed against an explicit policy.
- [ ] Security scans are versioned, fresh and include failures.
- [ ] No secrets, confidential data or identifiable user activity are captured.
- [ ] Evidence is sufficient to repeat the run from a clean executor.
- [ ] A second clean-run check establishes or explicitly rejects reproducibility.
- [ ] Teardown is verified.
- [ ] No product code, FBT Revit Academy, `main`, B2-B or B3 was changed.

A partial pass must be reported as partial; it cannot be silently upgraded to GO.

## 12. Explicit stop/go criteria

### STOP immediately

- No explicit B2-A approval.
- Executor would require installing on or monitoring the user's normal workstation.
- Any pinned commit/gitlink cannot be fetched or verified.
- Canonical build/test procedure cannot be derived from the pinned source.
- Unknown, missing or prohibited license affects the intended distributed boundary.
- Critical/high vulnerability exceeds the approved policy without documented disposition.
- Build/test failure is masked, omitted or irreproducible.
- Evidence contains secrets, confidential data or real user activity.
- Scope expands into product implementation, Revit integration, B2-B or B3.

### CONDITIONAL B2-A PASS

Only if baselines run in the approved matrix, evidence is complete, and remaining findings have documented owners and do not violate the license/security policy.

### GO beyond B2-A

Not available from this package. A separate human decision is required after Claude review and completed B2-A evidence. Passing B2-A does not approve B2-B, B3, production use or deployment.

## 13. Unresolved questions for Claude

1. Does Claude agree that B2-A must run in a disposable executor and not the user's normal PC?
2. Which platform matrix is the minimum meaningful baseline: Linux/container, Windows, or both?
3. What exact upstream CI commands should be canonical at the pinned Miru and ActivityWatch revisions?
4. Which pinned SBOM/license tools should be approved for each ecosystem?
5. What license allow/review/deny policy applies to the planned commercial distribution?
6. What vulnerability severity and no-fix policy should block the gate?
7. Should raw logs be committed to Git, attached as workflow artifacts, or summarized with hashes?
8. Is a second clean run mandatory for the word “reproducible”?
9. Should optional ActivityWatch components such as `aw-watcher-input` be built/inventoried but excluded from any future product bundle?
10. Who provides final legal approval for MPL-2.0 obligations and Australian workplace/privacy compliance?
11. Should the future executor use a new branch such as `agent/executor-b2a` rather than either planning branch?
12. What exact evidence is required before changing B2-01 from BLOCKED?

## 14. Required human approvals

| Approval | Required before |
|---|---|
| User approval for Gate B2-A scope | Any checkout/build/install/scan execution |
| User approval of executor/platform and network downloads | Provisioning the run |
| Project owner approval of evidence/branch policy | Committing execution evidence |
| Qualified license/legal review | Commercial distribution decision involving MPL/transitive licenses |
| Australian employment/privacy legal review | Any real employee monitoring or pilot |
| Separate user approval | B2-B, B3, production deployment or product implementation |

## 15. Recommendation to Claude

Review this package and both unchanged OpenCode reports. Claude should return one of:

- **PLAN ACCEPTED WITH CORRECTIONS:** approve a corrected B2-A execution specification for later human approval;
- **PLAN REVISION REQUIRED:** identify exact missing commands/policies/evidence;
- **STOP:** if the isolated executor, licensing policy or evidence boundary cannot be made safe.

Claude must not approve or execute B2-A on behalf of the user. The recommended next action after Claude's review is a short, corrected B2-A runbook and an explicit user approval request for B2-A only.

## 16. Current blocker statement

B2-A remains **BLOCKED**. The immediate blockers are:

1. no explicit user approval for B2-A execution;
2. no approved disposable executor/platform matrix;
3. no pinned SBOM/scanner toolchain;
4. no explicit license and vulnerability decision policies;
5. several OpenCode commands require correction before they are reproducible;
6. ActivityWatch implementation details at the pinned gitlinks remain unverified because submodules were not initialized;
7. loaded internal cost, general offline sync and ingestion idempotency are not proven by the cited Miru fields;
8. the reuse matrix's future implementation priorities must not be executed inside B2-A;
9. runtime builds, tests, scans and legal conclusions remain **NOT VALIDATED**.

**END — STOP AFTER REVIEW PACKAGE**
