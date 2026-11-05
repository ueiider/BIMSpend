# BIMSpend — B2-A Coordination and Approval Plan

Date: 2026-11-05  
Owner: ChatGPT Work — Lead Architect and Project Coordinator  
Mode: **PLANNING AND COORDINATION ONLY**  
Branch: `agent/work-b2a-coordination`  
Gate status: **B2-A BLOCKED — NO EXECUTION AUTHORIZED**

## 1. Purpose

Coordinate the next B2-A planning cycle across Work, OpenCode, Claude and the human project owner without running builds, installing dependencies, scanning software, changing application code or advancing to B2-B/B3.

GitHub is the only persistent source of truth. Agent statements are evidence only when tied to an exact remote commit and independently checked where required.

## 2. Verified planning baseline

### 2.1 Main baseline

Latest verified `main` head:

- Commit: `eb13fc90eb768080f6790bb364b482274860688c`
- [Main baseline](https://github.com/ueiider/BIMSpend/commit/eb13fc90eb768080f6790bb364b482274860688c)

Baseline documents read completely:

- `CONTEXT_FOR_AI.md`
- `MASTER_PLAN.md`
- `TASK_TRACKER.md`
- `AI_HANDOFF.md`
- `docs/technical-feasibility/PLAN_AUDIT_REPORT.md`

The main tracker keeps B2-01 blocked pending explicit approval. No agent branch changes that state.

### 2.2 Work consolidated review

- Branch: `agent/work-b2a`
- Commit: `fac85d23e10e4c70ee06d89a87ceb789fe592f4d`
- [Work review package](https://github.com/ueiider/BIMSpend/blob/fac85d23e10e4c70ee06d89a87ceb789fe592f4d/docs/agents/work/B2A_REVIEW_PACKAGE.md)

Verified conclusions:

- preferred composition architecture preserved;
- ActivityWatch pinned-gitlink implementation remains unverified;
- OpenCode run commands require corrections;
- loaded internal cost, general offline sync and ingestion idempotency are not proven;
- future implementation priorities do not belong inside B2-A;
- B2-A needs an isolated executor, fixed tools/policies and human approval.

### 2.3 OpenCode execution plan

- Branch: `agent/opencode-b2a`
- Commit: `73e54ab583d76e6f3b018aaeb5449a1c42c91b9a`
- [B2-A execution plan](https://github.com/ueiider/BIMSpend/blob/73e54ab583d76e6f3b018aaeb5449a1c42c91b9a/docs/agents/opencode/B2A_EXECUTION_PLAN.md)

Accepted as preparation evidence, not an executable approved runbook. Corrections required include recursive initialization before complete submodule capture, canonical test commands, real SBOM generation, explicit exit-code preservation and removal of failure-masking patterns.

### 2.4 OpenCode reuse matrix

- Branch: `agent/opencode-reuse-matrix`
- Commit: `b26c6d1a97f270a55d6669916b1369339d1fc98d`
- [Reuse implementation matrix](https://github.com/ueiider/BIMSpend/blob/b26c6d1a97f270a55d6669916b1369339d1fc98d/docs/agents/opencode/REUSE_IMPLEMENTATION_MATRIX.md)

Accepted as static reuse research. Its Miru evidence is useful. Its ActivityWatch implementation claims are explicitly not verified at the pinned gitlinks because submodules were not initialized. Its future implementation ordering is outside B2-A.

## 3. Architecture boundary to preserve

| Component | Responsibility | Boundary |
|---|---|---|
| Miru | Business system of record: company, client, project, users, timesheets, review, invoices, reports | API/configuration first; narrow extension only if later evidence proves necessary |
| ActivityWatch | Local observed-window and AFK signal candidate | Loopback only; no direct cloud exposure; exact pinned implementation must be validated |
| BIMSpend Windows adapter | Future correlation, minimization, durable local queue, retry, idempotency and cloud ingestion | New BIMSpend code; not authorized in B2-A |
| Revit connector | Future read-only document/view/session identity signals | New versioned/signed code; no document transactions; not authorized in B2-A |
| BIMSpend domain layer | Future mapping and separation of observed, attributed, approved, billed and cost metrics | Must never infer billable time directly from foreground activity |

B2-A evaluates reproducibility, dependencies, licenses and security posture. It does not integrate these components.

## 4. State model: do not collapse these statuses

| State | Meaning | Current status |
|---|---|---|
| Research completed | An agent documented findings with source pointers | YES for PLAN audit, OpenCode plan/matrix and Work review |
| Claim independently verified | A second party checked the exact source/commit or reproduced the evidence | PARTIAL; SHAs and selected static claims verified, runtime claims not verified |
| Planning approved | Human accepted the corrected scope/runbook and policies | NO |
| Execution authorized | Human explicitly authorized B2-A in an approved executor | NO |
| Execution completed | Approved commands ran with evidence and teardown | NO |
| Gate passed | Human accepted completed evidence against criteria | NO |
| Later gate authorized | B2-B/B3 explicitly approved separately | NO |

“GO” inside an agent report never means execution authorization or gate passage.

## 5. Cross-agent ownership plan

### 5.1 Work — coordination and reconciliation owner

Work owns:

- verified source/commit registry;
- architecture boundary and gate-scope enforcement;
- cross-agent finding reconciliation;
- approval-evidence checklist;
- final corrected runbook structure;
- blocker and decision register;
- preparation of a human-readable approval request;
- remote verification of Work documentation branches.

Work must not perform OpenCode's technical research or pre-empt Claude's independent judgment. Work cannot approve execution.

### 5.2 OpenCode — technical gap research owner

OpenCode owns read-only investigation of:

1. canonical build/test commands at the pinned Miru revision;
2. canonical ActivityWatch bundle/submodule build and test targets;
3. exact recursive gitlink tree and nested submodules;
4. proposed pinned SBOM/license/security tools for Ruby, JavaScript, Python, Rust and container/OS layers;
5. exact prerequisite/runtime matrix;
6. CI definitions and platform-specific build requirements;
7. evidence/log formats and failure exit-code handling;
8. license/NOTICE file inventory candidates;
9. corrections to commands flagged in the Work review.

OpenCode deliverables must use a new branch and exact commit. Research may describe commands but must not execute builds, install dependencies or modify application code unless a future task explicitly authorizes it.

### 5.3 Claude — independent audit owner

Claude owns an independent audit, not a summary of Work/OpenCode:

- verify whether the corrected scope actually satisfies B2-A;
- challenge architecture, license, security and privacy assumptions;
- review proposed toolchain/scanner choices and evidence sufficiency;
- identify unsafe or non-reproducible commands;
- determine whether the platform matrix is adequate;
- assess whether the acceptance/stop criteria are falsifiable;
- explicitly flag unresolved legal/human decisions;
- classify the plan as:
  - `PLAN ACCEPTED WITH CORRECTIONS`,
  - `PLAN REVISION REQUIRED`, or
  - `STOP`.

Claude does not approve or execute B2-A on behalf of the user.

### 5.4 Human project owner

Only the human project owner can:

- approve the final B2-A scope;
- approve the executor/platform/network and evidence policy;
- accept license/vulnerability thresholds;
- authorize downloads, installations/builds/scans in the approved environment;
- accept completed B2-A evidence;
- authorize any subsequent gate.

Qualified legal review remains required for commercial licensing/distribution and any future employee monitoring/pilot.

## 6. Dependencies and handoff conditions

| From | To | Required handoff |
|---|---|---|
| Work baseline | OpenCode | Exact source SHAs, current blockers, questions and prohibited scope |
| Work baseline | Claude | Exact links to all three verified reports plus main baseline |
| OpenCode | Work | Remote branch/SHA, full technical-gap report, source paths, exact commands/tools, explicit unknowns |
| OpenCode | Claude | Same immutable report; no private/local-only evidence |
| Claude | Work | Remote branch/SHA, independent verdict, findings with severity/evidence, required corrections |
| Work | Human | Reconciled decision register, conflict resolution, corrected runbook, evidence checklist and residual risks |
| Human | Executor | Explicit approval statement naming scope, branch/runbook revision, executor and limits |
| Executor | Work/Claude/Human | Immutable evidence branch, logs/results/checksums, teardown proof and stop/go recommendation |

A downstream handoff is blocked when its required remote SHA/file is missing, inaccessible or changed without re-review.

## 7. Evidence required before human approval of B2-A

Human approval should not be requested until the planning package contains:

### 7.1 Immutable scope evidence

- exact main baseline;
- exact Miru and ActivityWatch bundle SHAs;
- complete recursive ActivityWatch gitlink manifest;
- explicit in-scope/out-of-scope table;
- statement that B2-B/B3/product implementation remain blocked.

### 7.2 Corrected runbook evidence

- canonical commands traced to pinned upstream CI/docs/config;
- exact command order and working directories;
- expected exit codes and stop behavior;
- no `|| true` or equivalent failure masking for mandatory checks;
- synthetic configuration and fixture plan;
- second-clean-run reproducibility method;
- safe teardown procedure.

### 7.3 Executor evidence

- disposable executor type and immutable image/version manifest;
- Windows/Linux platform matrix and what each platform proves;
- CPU/RAM/disk/time budget;
- network/download policy;
- least-privilege GitHub credentials and branch restrictions;
- confirmation that no monitoring occurs on the user's live desktop.

### 7.4 Dependency/license/security evidence plan

- pinned SBOM tools and CycloneDX/SPDX outputs;
- pinned vulnerability and secret scanners;
- license allow/review/deny policy;
- vulnerability severity/no-fix policy;
- asset/font/icon/container/OS coverage;
- MPL-2.0 review boundary and source-offer plan;
- log redaction and artifact-retention rules.

### 7.5 Independent review evidence

- OpenCode technical-gap report at an immutable commit;
- Claude independent audit at an immutable commit;
- Work reconciliation resolving every conflict;
- explicit list of residual unknowns and named human owners.

These are planning artifacts. Actual build/test/SBOM/scan results are evidence for completing B2-A, not prerequisites for authorizing its execution.

## 8. Decisions blocked until Claude audit

Do not finalize the following before Claude publishes an independent remote audit:

1. whether the B2-A scope is complete and internally consistent;
2. minimum platform matrix;
3. acceptable disposable executor;
4. canonical command set;
5. SBOM/scanner selections;
6. evidence storage approach: Git text, workflow artifact, release asset or hashes;
7. mandatory second clean run;
8. vulnerability thresholds and exception process;
9. license policy sufficiency;
10. whether optional ActivityWatch components are inventoried only or built;
11. whether the corrected runbook is ready for human approval;
12. whether any blocker is severe enough for `STOP`.

No architecture or product decision beyond baseline audit may be inferred from Claude accepting a B2-A runbook.

## 9. Reconciliation template

Use one row per atomic finding. Never merge unlike issues.

| ID | Topic | OpenCode claim/evidence | Claude finding/evidence | Work baseline | Agreement state | Severity | Resolution/owner | Status |
|---|---|---|---|---|---|---|---|---|
| R-001 | Example: Miru test command | Commit/path/line and proposed command | Independent confirmation or correction | Work review §6 | AGREE / PARTIAL / CONFLICT / UNKNOWN | Critical/High/Medium/Low | Exact action + owner | OPEN/CLOSED/BLOCKED |

Required rules:

- `AGREE`: same fact and implication independently supported.
- `PARTIAL`: same direction, but scope/evidence differs.
- `CONFLICT`: claims cannot both be accepted.
- `UNKNOWN`: neither side has sufficient evidence.
- Every `CONFLICT` and Critical/High item must be closed or explicitly accepted by the human before authorization.
- “Not tested” remains `UNKNOWN`, never a pass.
- Local paths and screenshots are not durable evidence without a GitHub-hosted report/checksum.
- A newer upstream branch head does not replace a pinned bundle gitlink.

### Decision register template

| Decision ID | Decision required | Options | OpenCode recommendation | Claude recommendation | Work recommendation | Human decision | Evidence SHA |
|---|---|---|---|---|---|---|---|
| D-001 | Executor platform | Windows / Linux / both | Pending | Pending | Pending audit | BLOCKED | — |

## 10. Corrected runbook structure — not executable yet

The final runbook should use this structure:

### 0. Authorization header

- human approval reference;
- exact runbook commit;
- executor identity/image;
- operator, timestamp, time/resource limits;
- permitted network and GitHub access;
- explicit prohibited actions.

### 1. Preflight and fail-closed checks

- clean disposable environment;
- tool version verification;
- credentials and destination branch validation;
- disk/resource checks;
- synthetic-data confirmation;
- immediate stop conditions.

### 2. Immutable checkouts

- Miru pinned checkout;
- ActivityWatch pinned umbrella checkout;
- recursive submodule initialization;
- exact recursive SHA/URL/status capture;
- clean-tree verification.

### 3. Source and license inventory

- manifest and source hashes;
- license/NOTICE/vendor/assets inventory;
- ecosystem and OS/container SBOM generation;
- unknown/prohibited-license stop.

### 4. Miru baseline

- exact pinned runtime;
- canonical dependency install/build/database/test commands;
- synthetic database/config;
- Ruby/JavaScript/container scans;
- structured exit codes/logs/checksums.

### 5. ActivityWatch baseline

- exact recursive gitlinks;
- canonical platform-specific builds/tests;
- Python/Rust/JavaScript/packaging scans;
- no watcher use against live user activity;
- structured evidence.

### 6. Reproducibility repeat

- second clean instance;
- compare resolved dependencies, SBOMs and deterministic artifacts;
- explain nondeterminism;
- no single-run reproducibility claim.

### 7. Evidence sanitization and publication

- secret/PII/path scan;
- preserve failures and exit codes;
- approved raw-log storage;
- checksums and concise summary;
- commit only to the authorized execution branch.

### 8. Teardown and verification

- destroy disposable environment;
- revoke temporary credentials;
- verify no changes to main, user device, FBT Revit Academy or other agents' branches;
- remote verification of evidence commit/file list.

### 9. B2-A evaluation

- criterion-by-criterion PASS/FAIL/PARTIAL/NOT TESTED;
- license and vulnerability disposition;
- residual risks;
- recommendation only;
- separate human gate decision.

The runbook must contain no adapter, Revit connector, Miru feature modification, live user monitoring, B2-B or B3 task.

## 11. Coordination cycle

1. Work publishes this coordination baseline.
2. OpenCode publishes technical gap research on a new branch.
3. Claude reads immutable Work/OpenCode evidence and publishes an independent audit on its own branch.
4. Work verifies both remote commits and populates the reconciliation/decision registers.
5. Any unresolved conflict is returned to the responsible agent or human owner.
6. Work publishes a corrected final runbook proposal.
7. Human reviews scope, executor, policies and residual risk.
8. Only explicit human authorization can start B2-A.
9. Completed execution evidence returns for independent review before any gate-pass decision.

## 12. Current blockers

| Blocker | Owner | Release condition |
|---|---|---|
| OpenCode technical-gap cycle not yet published for this coordination round | OpenCode | Verified remote branch/SHA/report |
| Claude independent audit not yet published | Claude | Verified remote branch/SHA/report and verdict |
| Corrected canonical commands incomplete | OpenCode + Claude | Reconciled, source-backed command set |
| ActivityWatch exact pinned implementation unverified | OpenCode/B2-A executor | Recursive source inspection; runtime only after approval |
| Executor/platform matrix undecided | Human after Claude audit | Explicit selection |
| SBOM/scanner toolchain undecided | Human after agent recommendations | Explicit accepted versions |
| License/vulnerability policies undecided | Human/legal as applicable | Written thresholds and exception process |
| Evidence storage/retention undecided | Human | Approved artifact policy |
| B2-A execution not authorized | Human | Explicit approval tied to final runbook SHA |

## 13. Next required human decision

No execution decision is requested yet.

The next human decision occurs **after** OpenCode publishes the technical-gap report, Claude publishes the independent audit, and Work reconciles them. The human will then decide whether to:

- approve the corrected B2-A runbook and named disposable executor;
- request revisions; or
- stop the gate.

Until that decision is recorded against an exact GitHub commit:

**GATE B2-A REMAINS BLOCKED.**
