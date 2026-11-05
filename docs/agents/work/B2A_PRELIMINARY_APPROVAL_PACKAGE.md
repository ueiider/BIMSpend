# BIMSpend B2-A — Preliminary Approval Package

**Decision state:** PRELIMINARY.  
**Gate state:** **BLOCKED — awaiting independent audit, technical reconciliation, and explicit human approval.**  
**Execution:** Not authorized. No build, test, scan, dependency installation, or runbook step was performed in this consolidation.

## 1. Executive position

The available planning evidence supports a separated architecture proposal: Miru as business foundation; ActivityWatch as local monitoring; a new BIMSpend Windows Adapter; and a separate read-only Revit Connector. Existing evidence does not establish runtime build/test success, full ActivityWatch implementation at exact submodule gitlinks, durable encrypted offline sync, idempotent ingestion, loaded internal labor cost reuse, or completed licensing/security inventories.

Two expected parallel reports were not present in GitHub branch search at the time checked:
- Claude/NVIDIA audit: expected branch `agent/claude-b2a-review`.
- OpenCode research: expected branch `agent/opencode-b2a-parallel-research`.

Therefore, this is not a final approval recommendation. Final reconciliation is dependent on both published reports and project-owner decisions.

## 2. Scope and exclusions

**Planning scope:** architecture, evidence reconciliation, risks, decisions, prerequisites, acceptance criteria, and future verification readiness.

**Explicit exclusions:** product code, adapter or connector implementation, B2-A builds/tests/scans, installation on a user workstation, deployment/production, merge to main, B2-B/B3 authorization, and FBT Revit Academy.

Pinned upstream references remain:
- Miru `10e457e1d0cd2ac782be9d1edbcbd5a1a573486a`
- ActivityWatch `9fee4702fea08dbe0149cc6e28f4ef66b49f54ec`

## 3. Source evidence register

| Evidence source | Exact revision | Key evidence | Limitation |
|---|---|---|---|
| Main planning baseline | `eb13fc90eb768080f6790bb364b482274860688c` | Context, master plan, task tracker, handoff, feasibility audit | Planning documents; not execution results |
| Work B2-A Review Package | `fac85d23e10e4c70ee06d89a87ceb789fe592f4d` | Corrected unsupported runbook claims, risks, prerequisites | No builds/tests/scans executed |
| OpenCode execution plan | `73e54ab583d76e6f3b018aaeb5449a1c42c91b9a` | Proposed B2-A baseline procedure and upstream pins | Draft commands include issues corrected by Work |
| OpenCode reuse matrix | `b26c6d1a97f270a55d6669916b1369339d1fc98d` | Miru source-level reuse candidates and ActivityWatch submodule inventory | ActivityWatch submodules not initialized/read |
| Work coordination plan | `c90a510a83a892bf3476d8395eca46fd09f01b60` | Roles, handoffs, approval prerequisites | Planning only |
| OpenCode technical gap resolution | `0982411fc0d7ae0bb43508d086d71a088a575c7a` | Verified/unverified claims, corrected prerequisites, continued blocked status | Proposals only; commands not executed |
| Claude/NVIDIA independent audit | Not published / no branch found | None available | PENDING |
| OpenCode parallel technical research | Not published / no branch found | None available | PENDING |

### Upstream references and caveats

The gap report says Miru’s pinned commit and ActivityWatch umbrella commit were matched to upstream repositories. It reports all 11 ActivityWatch gitlink commit objects exist. Those checks do not prove implementation behavior. ActivityWatch submodule APIs, payloads, bind defaults, privacy filtering, lifecycle, and packaging at exact gitlinks remain **NOT VERIFIED**. Umbrella MPL-2.0 and Miru MIT are reported; recursive submodule/transitive license inventory and legal distribution assessment remain incomplete.

## 4. Preliminary architecture baseline

1. Miru owns canonical business entities and approved/reviewed timesheet, billing and reporting workflows where source-level fit is confirmed.
2. ActivityWatch is a local event source, not the authority for project identity, productive work, timesheet approval, or billing.
3. A future Windows Adapter locally minimizes/normalizes events, proposes attribution, owns queue/retry/idempotency and sends authenticated records.
4. A future read-only Revit Connector emits minimal session/document context; no model modifications and no blocking network work inside Revit callbacks.
5. Observed activity, attributed time, submitted time, approved time, billed time, client billing rate, and internal loaded labor cost remain distinct.

These are proposed boundaries. They are not implemented or approved.

## 5. Readiness matrix

| Requirement | State | Evidence / next condition |
|---|---|---|
| Exact main planning baseline identified | READY | Main commit fixed above |
| Existing Work/OpenCode report provenance verified | READY | Exact commits and paths listed |
| Miru business reuse candidates identified | PROPOSED | Source reports; independent audit pending |
| ActivityWatch umbrella pin identified | READY | Pin fixed; exact submodule behavior not validated |
| ActivityWatch submodule behavior | BLOCKED | Initialize/read exact gitlinks in approved process; reports pending |
| Adapter/Connector component separation | PROPOSED | Architecture recommendation; owner/audit review needed |
| Loaded labor cost semantics | BLOCKED | Define source, formula, effective date, permissions |
| Offline encrypted queue | BLOCKED | Design and threat model absent; upstream support not proven |
| Idempotent, tenant-scoped synchronization | BLOCKED | API/schema uniqueness and replay behavior unproven |
| Privacy/retention/notice | REQUIRES HUMAN APPROVAL | Define purpose, collection, access, retention, deletion |
| Revit version/runtime and metadata scope | REQUIRES HUMAN APPROVAL | Choose supported matrix and permitted identifiers |
| License and dependency clearance | BLOCKED | Recursive license/SBOM and legal review not complete |
| SBOM/scanner toolchain and severity policy | REQUIRES HUMAN APPROVAL | Select format/tools/versions, thresholds and exceptions |
| Canonical build/test commands | BLOCKED | Derive from pinned CI/build files; no execution |
| Disposable execution environment | REQUIRES HUMAN APPROVAL | Identify isolation, platform, network and resource budget |
| Independent Claude/NVIDIA audit | PENDING EXTERNAL AGENT | Publish report with exact commit |
| OpenCode parallel technical research | PENDING EXTERNAL AGENT | Publish report with exact commit |
| B2-A execution | BLOCKED | Requires final reconciliation and separate explicit authorization |

## 6. Technical risk register

| Risk | Level | Current position | Required control / owner |
|---|---|---|---|
| ActivityWatch behavior inferred from README rather than exact gitlinks | High | NOT VERIFIED | OpenCode research + approved exact-source review |
| Sensitive window/document metadata collected or exposed | Critical | Collection policy unresolved | Project owner + privacy/legal review; minimize/local filter |
| Local ActivityWatch service exposed beyond loopback | Critical | Exact bind behavior unverified | Verify pinned implementation; enforce local boundary |
| Revit API callback blocks/crashes or changes model | High | No connector exists | Read-only contract, bounded callbacks, isolation, later tests |
| Multiple sessions misattributed/double counted | High | Mapping design unresolved | Session correlation, foreground policy, user confirmation |
| Duplicate/lost time records on offline replay | High | No queue/idempotency proof | Server uniqueness, encrypted queue, failure tests |
| Internal cost confused with billing price | High | Upstream charge rate is not loaded cost | Separate data models and permissions |
| Tenant/auth credential leakage | High | AgentKey found; desktop lifecycle unresolved | Scoped credentials, OS secret storage, rotation, tenant tests |
| MPL/transitive license obligations missed | High | Recursive inventory absent | SBOM/license report and legal review |
| Unrepeatable or misleading verification | High | Draft commands had unsupported/masked steps | Canonical source-derived commands; preserve exit codes |
| User workstation altered by tool installation | Critical | No execution allowed | Disposable approved executor only |

## 7. Dependencies and handoff map

- **Claude/NVIDIA → Work:** independent challenge report, exact commit, claim-by-claim evidence, security/privacy findings. Only after remote verification can assessment be recorded.
- **OpenCode parallel research → Work:** exact source research on unresolved APIs, ActivityWatch gitlinks, commands/toolchain, platform constraints and licenses. Only after remote verification can it be reconciled.
- **Work → Project owner:** consolidated findings, disagreements, readiness, choices and explicit stop/go criteria.
- **Project owner → execution owner:** explicit written approval of B2-A scope, executor, policies, evidence handling and execution start.
- No agent report by itself authorizes execution.

## 8. Acceptance criteria for a future B2-A baseline

These are proposed criteria, pending audit and owner approval:
1. Clean isolated checkout records the exact Miru and ActivityWatch pins and recursively initialized gitlink SHAs.
2. All inspected components have path/revision provenance; no unverified source-level claims are promoted.
3. Canonical build/test commands are sourced from exact pinned upstream CI/build instructions, with tool versions and exit codes preserved.
4. Selected build/test runs complete in approved disposable environments; failures and skips are explicit.
5. SPDX/CycloneDX SBOM and recursive license/NOTICE inventory cover dependencies and assets in agreed scope.
6. Security scans use approved pinned tools and database timestamps; severity exceptions are reviewed and recorded.
7. Logs/evidence are redacted, checksummed and retained per approved policy; teardown is verified.
8. Results produce a stop/go report with unresolved items and no claim beyond evidence.

These criteria do not include implementing an Adapter, Revit Connector, cloud ingestion, branded product UI, or production behavior.

## 9. Verification readiness checklist — NOT EXECUTED

Before any future run:
- [ ] Claude report and OpenCode parallel report are published, exact commits verified, fully reviewed.
- [ ] Findings reconciled, conflicts explicit, material blockers resolved or accepted by owner.
- [ ] Project owner approves disposable executor, platform matrix, network/resource budget.
- [ ] Project owner approves privacy, retention, license policy, scanner toolchain and severity thresholds.
- [ ] Canonical command manifest comes from pinned source/CI; no ambiguous “or equivalent” and no failure masking.
- [ ] Evidence naming, redaction, retention, secrets handling and teardown criteria are approved.
- [ ] Owner explicitly authorizes B2-A execution.

## 10. Pending agent work and human approval checklist

### Pending external agents
- Claude/NVIDIA: independent technical/security audit.
- OpenCode: parallel technical research / gap resolution.

### Human decisions required
- Approve or reject Miru and ActivityWatch as reuse candidates.
- Approve monitoring purpose, event categories, user notice, retention, access and deletion.
- Select Revit versions and Windows/Linux verification scope.
- Select disposable executor, network permissions, resource limits and evidence destination.
- Define loaded labor cost, currency, effective dating and access policy.
- Choose offline encryption/key management and acceptable sync loss/duplicate bounds.
- Approve license policy, distribution model and required legal review.
- Choose SBOM format, tools/versions, vulnerability severity thresholds, exceptions and evidence retention.
- Approve final corrected runbook.
- Separately authorize B2-A execution after the above review.

## 11. Stop/go rule

**Current result: STOP / BLOCKED.** Do not execute B2-A until both agent reports are published and reconciled, required owner decisions are recorded, and the owner explicitly authorizes the exact run. A later successful B2-A baseline would not approve B2-B, B3, production deployment, or product implementation.
