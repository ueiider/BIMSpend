# BIMSpend B2-A — Parallel Agent Integration Matrix

**As of:** 2026-11-05  
**Purpose:** Coordinate independent work and evidence reconciliation. No unpublished report is represented as reviewed.

## Verified remote source baseline

| Source | Exact commit | Document | Availability |
|---|---|---|---|
| Main baseline | `eb13fc90eb768080f6790bb364b482274860688c` | `CONTEXT_FOR_AI.md`, `MASTER_PLAN.md`, `TASK_TRACKER.md`, `AI_HANDOFF.md`, `docs/technical-feasibility/PLAN_AUDIT_REPORT.md` | Verified at pinned main |
| Work review | `fac85d23e10e4c70ee06d89a87ceb789fe592f4d` | `docs/agents/work/B2A_REVIEW_PACKAGE.md` | Verified |
| OpenCode execution plan | `73e54ab583d76e6f3b018aaeb5449a1c42c91b9a` | `docs/agents/opencode/B2A_EXECUTION_PLAN.md` | Verified |
| OpenCode reuse matrix | `b26c6d1a97f270a55d6669916b1369339d1fc98d` | `docs/agents/opencode/REUSE_IMPLEMENTATION_MATRIX.md` | Verified |
| Work coordination | `c90a510a83a892bf3476d8395eca46fd09f01b60` | `docs/agents/work/B2A_COORDINATION_AND_APPROVAL_PLAN.md` | Verified |
| OpenCode gap resolution | `0982411fc0d7ae0bb43508d086d71a088a575c7a` | `docs/agents/opencode/B2A_TECHNICAL_GAP_RESOLUTION.md` | Verified and read completely |

## Parallel report availability

As of this review, GitHub branch searches returned no branch for either expected in-progress deliverable:
- Claude/NVIDIA: `agent/claude-b2a-review`, expected `docs/agents/claude/B2A_INDEPENDENT_TECHNICAL_AUDIT.md` — **PENDING / NOT PUBLISHED**.
- OpenCode: `agent/opencode-b2a-parallel-research`, expected `docs/agents/opencode/B2A_PARALLEL_TECHNICAL_RESEARCH.md` — **PENDING / NOT PUBLISHED**.

No commits or findings for those reports are available to reconcile. This is a point-in-time remote observation, not a claim about local progress.

## Findings reconciliation matrix

| Topic | Current Work findings | Existing OpenCode findings | Claude/NVIDIA dependency | OpenCode parallel dependency | Confidence now | Open question | Reconciliation action |
|---|---|---|---|---|---|---|---|
| Miru role | Candidate business foundation; distinct from local collectors and Revit | Source reports describe business, time, invoicing and agent API reuse | Independent source/architecture challenge | Check fit, missing capabilities, canonical test/build procedures | Medium-high for reported source claims; no runtime validation | Is Miru suitable as the long-term BIMSpend system of record? | Compare source evidence, list gaps, keep decision proposed |
| ActivityWatch role | Local capture only behind Adapter; exact submodule code unverified | Umbrella and 11 gitlinks identified; implementation at gitlinks not read | Validate trust/privacy boundary | Inspect submodule APIs, events, bind settings, lifecycle and platform support | High on gitlink existence; low on behavior | Can the pinned modules provide safe minimal events? | Verify exact gitlinks, then reconcile field/API claims |
| Windows Adapter | New BIMSpend component; owns local normalization, attribution proposal, queue/retry | Identified as new integration layer; durable sync not proven upstream | Challenge failure/security boundaries | Detail viable APIs/IPC and platform process design | Medium as proposed architecture | What deployment and IPC are appropriate? | Record interface and threat model; defer implementation |
| Revit Connector | Separate read-only add-in; bounded callbacks, no model writes/network in callback | Revit integration is new; Autodesk references listed | Independent API and privacy challenge | Resolve Revit version/runtime, multiple sessions, metadata contract | Medium for boundary; low for version details | Which Revit versions and permitted metadata? | Confirm against Autodesk docs/source and human policy |
| Labor cost vs billing | Separate internal loaded cost from client charge rate | Gap report explicitly says Miru billing rate is not loaded cost | Audit semantics and financial risk | Identify schema or source evidence; no assumption of reuse | High that distinction is required by evidence | Definition, source, effective dating and permissions? | Finance decision required; do not equate fields |
| Offline sync/idempotency | New requirement; no proven upstream durable queue | Fields exist but do not establish replay safety/unique constraints | Challenge data-loss and tenant risks | Confirm server schema/API support and gap | High confidence the current evidence is insufficient | Delivery semantics and storage/key policy? | Keep blocked until API/DB evidence + owner decision |
| Project identity | Explicit mapping and user confirmation proposed | Attribution layer is new | Review privacy and misattribution risk | Identify viable mapping signals and API shape | Medium-low | Which stable project identifier is allowed? | Define ambiguity/error workflow and owner choice |
| Privacy/retention | Minimize raw telemetry; no keystrokes/screenshots; local filters | ActivityWatch privacy behavior at exact gitlinks unverified | Independent privacy assessment | Inspect exact privacy filters, event schema, ports | Medium on risk, low on implementation | Which collection and retention policy is lawful/acceptable? | Hold human decision; document data inventory |
| Auth/secrets/tenancy | Scoped credentials, TLS, server-side authorization proposed | Miru AgentKey bearer auth reported; no full desktop lifecycle proof | Audit credential threat model | Resolve enrollment, rotation, revoke, tenant scoping | Medium | How does device enrollment and recovery work? | Confirm API source and threat model; owner approves policy |
| Licenses | Miru MIT, ActivityWatch MPL-2.0 reported; transitive inventory missing | Exact umbrella license and submodule/license caveats | Audit distribution boundary | Recursive license/NOTICE and compatibility research | Medium for umbrella licenses; low for transitive obligations | Which licensing policy is acceptable for commercial distribution? | Create exact recursive inventory; counsel review |
| SBOM/scanners | No scans or SBOM run; toolchain/policy unresolved | Work corrected unsupported commands; no scans run | Challenge proposed controls | Specify ecosystem tools, versions, commands | High on not executed | Format/tool versions and severity threshold? | Owner selects policy before any execution |
| Verification platform/runbook | Must use disposable environment; commands sourced from pinned CI | Draft had commands needing correction; no execution | Audit completeness and risks | Resolve canonical commands/platform matrix | High on prerequisite need | Windows/Linux scope, resources, retention? | Reconcile source-backed runbook before approval |

## Work ownership and handoffs

| Owner | Independent work | Deliverable/handoff condition |
|---|---|---|
| ChatGPT Work | Maintain architecture boundaries, decision register, source provenance, unresolved items, merge findings only after reports are remotely verified | This preliminary package; final reconciliation update after both reports available |
| Claude Code + FCC/NVIDIA NIM | Independent technical/security/architecture audit; no dependence on Work's proposed conclusions | Publish expected audit on named branch with exact commit; identify evidence and confidence per claim |
| OpenCode | Additional technical research and implementation-question resolution | Publish expected research report on named branch with exact commit and source references |
| Project owner | Decide privacy, platform, tools, license and risk policies; authorize or reject B2-A | Explicit written decisions and separate explicit execution authorization |

## INDEPENDENT WORK

Can proceed immediately without external reports:
- Document evidence already present in verified reports.
- Maintain proposed component boundaries and label them unapproved.
- Identify known gaps and correct unsupported conclusions.
- Draft decision criteria, acceptance criteria, and dependency map.
- Prepare reconciliation template and stop/go conditions.

## DEPENDENT WORK

Requires remote publication and verification first:
- Assess Claude/NVIDIA conclusions or claim independent agreement.
- Resolve conflicts between Claude and OpenCode research.
- Finalize exact ActivityWatch submodule behavior, API, privacy filters, ports, packaging.
- Finalize build/test commands, toolchain, vulnerability/SBOM procedure, and platform matrix.
- Produce final approval package and readiness recommendation.

## HUMAN DECISIONS

Require explicit project owner decision:
- Whether to use workplace activity monitoring and which signals to collect.
- Data retention, access, deletion and notice/consent policy.
- Supported Revit/Windows/Linux platform scope and disposable executor.
- Internal loaded labor cost definition and who may see/edit it.
- License policy and commercial distribution boundary.
- SBOM format/scanners, vulnerability severity and exceptions.
- Offline encryption/key recovery and sync-loss/duplication tolerance.
- Whether to authorize B2-A execution after all prerequisites are resolved.

## Reconciliation record template

For every agent claim, record:
`ID | topic | source commit/path/line | original claim | Claude assessment | OpenCode response | Work decision | evidence confidence | status | risk | owner | human decision`.

Rules:
1. Preserve disagreements; do not average incompatible claims.
2. Cite exact commit, path, and source lines/files where available.
3. Mark unavailable, inferred, or unexecuted claims **NOT VERIFIED**.
4. Separate source-level facts from runtime validation and policy decisions.
5. Only mark a conclusion VERIFIED when its evidence is independently inspectable and supports the exact wording.
6. A source report's assertion that a test passed is not runtime evidence unless logs/artifacts are supplied and verified.
