# BIMSpend B2-A — Architecture Decision Register

**Status convention:** VERIFIED = supported by cited evidence as a factual property; PROPOSED = recommendation awaiting approval; BLOCKED = evidence or required decision is missing. A VERIFIED status does not imply the proposed architecture is approved.

## Decision index

| ID | Topic | Status | Human approval |
|---|---|---|---|
| ADR-B2A-01 | Miru reuse strategy | PROPOSED | Yes |
| ADR-B2A-02 | ActivityWatch integration | PROPOSED | Yes |
| ADR-B2A-03 | Windows Adapter boundaries | PROPOSED | Yes |
| ADR-B2A-04 | Revit Connector isolation | PROPOSED | Yes |
| ADR-B2A-05 | Labor cost vs billing rate | PROPOSED | Yes |
| ADR-B2A-06 | Offline encrypted persistence | BLOCKED | Yes |
| ADR-B2A-07 | Synchronization/idempotency | BLOCKED | Yes |
| ADR-B2A-08 | Project identity reconciliation | BLOCKED | Yes |
| ADR-B2A-09 | Privacy and retention | BLOCKED | Yes |
| ADR-B2A-10 | Authentication and secrets | BLOCKED | Yes |
| ADR-B2A-11 | Open-source license compliance | BLOCKED | Yes |
| ADR-B2A-12 | SBOM and vulnerability scanning | BLOCKED | Yes |
| ADR-B2A-13 | Windows/Linux verification | BLOCKED | Yes |
| ADR-B2A-14 | Canonical verification commands | BLOCKED | Yes |

## ADR-B2A-01 — Miru reuse strategy

- **Problem:** Select what business functionality BIMSpend should reuse.
- **Evidence:** Main PLAN audit and OpenCode reuse matrix/gap resolution identify Miru at `10e457e1d0cd2ac782be9d1edbcbd5a1a573486a`, MIT, with company/client/project, time entry, invoice/reporting, and AgentKey/timesheet functionality. Runtime/build verification was not performed.
- **Proposed decision:** Treat Miru as candidate business foundation; reuse/configure existing workflows where fit is proven. Put BIM-specific attribution, cost semantics, and local integration in separate components.
- **Alternatives:** Build a new business backend; fork Miru broadly; use Miru as a thin API only.
- **Trade-offs:** Reuse reduces custom business code; upstream stack/version and product fit, maintenance, and MIT notice obligations remain.
- **Status:** PROPOSED.
- **Dependencies:** Independent audit; B2-A baseline; fit-gap and license/dependency review.
- **Human approval:** Approve Miru as foundation and acceptable fork/configuration boundary.
- **Acceptance:** Source-level entity/API mapping, exact pinned build/test evidence, and documented no-go gaps; preserve upstream notices.

## ADR-B2A-02 — ActivityWatch integration

- **Problem:** Decide whether local monitoring can provide minimum viable activity signals.
- **Evidence:** ActivityWatch umbrella pin `9fee4702fea08dbe0149cc6e28f4ef66b49f54ec`, MPL-2.0, 11 submodule gitlinks; exact implementation at gitlinks is NOT VERIFIED.
- **Proposed decision:** Keep ActivityWatch local and separate; integrate through a narrow Adapter contract only after inspecting exact gitlinks, privacy behavior, API, ports, and packaging.
- **Alternatives:** Build a minimal native watcher; use only Revit foreground/session signals; do not collect desktop activity.
- **Trade-offs:** Reuse may reduce capture work but adds submodule, platform, privacy, MPL, and lifecycle complexity.
- **Status:** PROPOSED.
- **Dependencies:** OpenCode parallel research, Claude audit, exact submodule source review, privacy/legal decisions.
- **Human approval:** Approve collection purposes/categories and whether ActivityWatch is included.
- **Acceptance:** Exact gitlink evidence; local-only/bind and privacy controls verified; data minimization and retention approved.

## ADR-B2A-03 — Windows Adapter boundaries

- **Problem:** Define local integration and sync responsibilities.
- **Evidence:** Work review and gap resolution classify Adapter as new BIMSpend work; Miru `synced_at` does not prove durable offline queue/replay.
- **Proposed decision:** Adapter owns normalization, minimization, attribution proposals, queue/retry, provenance, and API communication; it cannot approve or invoice time.
- **Alternatives:** Put integration in Miru; embed all logic in Revit add-in; direct ActivityWatch-to-server connection.
- **Trade-offs:** Clear isolation supports failure containment; introduces a new component and lifecycle/security surface.
- **Status:** PROPOSED.
- **Dependencies:** ADR-02, ADR-06, ADR-07, interface/API design.
- **Human approval:** Approve desktop agent deployment and lifecycle.
- **Acceptance:** Documented data contract, threat model, bounded retry and pause controls; failure isolation proven in later authorized tests.

## ADR-B2A-04 — Revit Connector isolation

- **Problem:** Collect only necessary Revit context without affecting models or user workflows.
- **Evidence:** PLAN audit cites Autodesk API lifecycle/event constraints; no BIMSpend connector exists in cited evidence.
- **Proposed decision:** Separate read-only connector that emits allowlisted document/session metadata to Adapter; no model writes or blocking network operations in Revit callbacks.
- **Alternatives:** Revit add-in owns sync/business logic; no Revit integration; external process/UI automation.
- **Trade-offs:** Separate process boundary reduces coupling but adds IPC and version packaging work.
- **Status:** PROPOSED.
- **Dependencies:** Revit version scope, supported API constraints, Windows Adapter contract.
- **Human approval:** Approve metadata collection and supported Revit versions.
- **Acceptance:** Read-only contract and version matrix; later tests show no model mutation and bounded callback impact.

## ADR-B2A-05 — Labor cost versus billing rate

- **Problem:** Avoid conflating internal labor cost and customer price.
- **Evidence:** Gap resolution states Miru `ProfitabilityBillingRate` is billing/charge rate, not proof of loaded internal labor cost.
- **Proposed decision:** Maintain distinct rate records and permissions; label contribution calculations precisely; do not reuse charge rates as payroll/employer costs.
- **Alternatives:** One universal hourly rate; derive cost from billing rate; defer cost tracking.
- **Trade-offs:** Correct semantics require another protected model and policy.
- **Status:** PROPOSED.
- **Dependencies:** Finance definitions, currencies, effective dates, overhead policy.
- **Human approval:** Approve cost definition and authorized users.
- **Acceptance:** Data dictionary, calculation examples, authorization matrix, and reconciliation rules approved.

## ADR-B2A-06 — Offline encrypted persistence

- **Problem:** Safely retain minimum pending records while offline.
- **Evidence:** Miru `synced_at` does not demonstrate durable encrypted queue, acknowledgement, replay, or bounded loss.
- **Proposed decision:** Require encrypted local queue with explicit retention, atomic persistence, recovery, and user-visible state before any production use.
- **Alternatives:** No offline queue; plaintext local DB; OS-protected local store with short retention.
- **Trade-offs:** Reliability vs key recovery, platform support, and privacy obligations.
- **Status:** BLOCKED.
- **Dependencies:** Data classification, key management, retention, Windows packaging.
- **Human approval:** Approve encryption/key ownership, retention, backup/recovery.
- **Acceptance:** Threat model and storage format approved; authorized later fault tests demonstrate encryption-at-rest, replay and deletion.

## ADR-B2A-07 — Synchronization and idempotency

- **Problem:** Prevent loss/duplication across retry and replay.
- **Evidence:** External IDs and sync timestamps exist in candidate upstream records, but uniqueness constraints/replay safety are NOT proven.
- **Proposed decision:** Use stable client-generated event/session idempotency keys scoped to agent and tenant, with server-enforced unique constraints and acknowledgement.
- **Alternatives:** At-least-once with manual duplicate cleanup; exactly-once claim; no automatic retry.
- **Trade-offs:** At-least-once plus idempotent handling is operationally realistic; requires API/schema support.
- **Status:** BLOCKED.
- **Dependencies:** Miru API inspection and server-side changes, tenant/auth contract.
- **Human approval:** Approve delivery semantics and acceptable loss/duplication bounds.
- **Acceptance:** Duplicate replay creates one logical record; wrong-tenant replay is rejected; failure recovery evidence.

## ADR-B2A-08 — Project identity reconciliation

- **Problem:** Map local Revit file/session and user choices to canonical business projects.
- **Evidence:** Existing reports identify project attribution as custom; no canonical mapping contract established.
- **Proposed decision:** Use explicit user-confirmable mapping to canonical server project ID; preserve local alias/provenance; ambiguity stays unassigned.
- **Alternatives:** Filename/path matching; automatic heuristics; manual timesheets only.
- **Trade-offs:** Confirmation reduces silent misattribution but adds workflow steps.
- **Status:** BLOCKED.
- **Dependencies:** Privacy policy, project APIs, multiple document/session design.
- **Human approval:** Approve mapping behavior and allowed identifiers.
- **Acceptance:** Conflict/unknown cases are visible, auditable, and never silently billed.

## ADR-B2A-09 — Privacy and retention

- **Problem:** Bound workplace monitoring and personal/business data collection.
- **Evidence:** PLAN audit/gap resolution identify raw window titles and ActivityWatch exposure as risks; exact pinned behavior remains unverified.
- **Proposed decision:** Minimize locally; no keystrokes/screenshots/content; explicit notice, purpose limitation, access controls, retention and deletion; raw events remain local unless justified.
- **Alternatives:** Collect full event stream; collect only Revit session metadata; no monitoring.
- **Trade-offs:** Less telemetry may reduce attribution coverage; strengthens privacy and limits exposure.
- **Status:** BLOCKED.
- **Dependencies:** Australian privacy/employment review, agent audit, exact event schema.
- **Human approval:** Approve monitoring purpose, users, notice/consent, retention, access.
- **Acceptance:** Approved data inventory and retention schedule; demonstrated minimization and deletion in later authorized validation.

## ADR-B2A-10 — Authentication and secrets

- **Problem:** Authenticate local Adapter to business APIs and protect credentials.
- **Evidence:** Miru AgentKey bearer auth is described in upstream source reports; desktop token lifecycle and tenant binding remain unresolved.
- **Proposed decision:** Per-agent scoped/revocable credentials, OS-protected secret storage, TLS, rotation/revocation and no secrets in logs; server validates tenant/project authorization.
- **Alternatives:** Shared static API key; user password stored locally; device code/OAuth.
- **Trade-offs:** Scoped secrets reduce blast radius but require enrollment and recovery design.
- **Status:** BLOCKED.
- **Dependencies:** Auth API verification, identity and tenancy design, OS support.
- **Human approval:** Approve enrollment, revocation and recovery policy.
- **Acceptance:** Threat model and end-to-end auth tests; tenant isolation and secret redaction proven later.

## ADR-B2A-11 — Open-source license compliance

- **Problem:** Establish distribution permissions for reused code and dependencies.
- **Evidence:** Miru MIT, ActivityWatch umbrella MPL-2.0; submodule/transitive and asset inventory not consolidated.
- **Proposed decision:** Preserve notices; generate recursive license/NOTICE inventory at pinned commits; legal review before commercial distribution, especially MPL covered-file and transitive GPL/AGPL concerns.
- **Alternatives:** Exclude ActivityWatch; isolate unmodified upstream; accept broader copyleft after counsel review.
- **Trade-offs:** Reuse offers functionality but creates ongoing attribution and source-availability obligations.
- **Status:** BLOCKED.
- **Dependencies:** Recursive exact-gitlink inventory, SBOM, distribution model, legal counsel.
- **Human approval:** Approve allowed/review/prohibited license policy and distribution boundary.
- **Acceptance:** Machine-readable inventory and notices; unresolved licenses block distribution.

## ADR-B2A-12 — SBOM and vulnerability scanning

- **Problem:** Choose auditable inventory and security scan methods.
- **Evidence:** Existing reports correct unverified commands; no SBOM or scans were executed.
- **Proposed decision:** Select pinned SPDX or CycloneDX tooling per ecosystem; preserve manifests, tool versions, invocation, exit codes, database timestamps, and exceptions.
- **Alternatives:** Lockfiles only; one combined scanner; ecosystem-specific tools plus aggregation.
- **Trade-offs:** Reproducibility requires a maintained toolchain and policy.
- **Status:** BLOCKED.
- **Dependencies:** Human toolchain/severity policy; disposable executor; dependency inventory.
- **Human approval:** Approve format/tools/severity and exception process.
- **Acceptance:** SBOM covers direct/transitive/runtime/build dependencies; scans have traceable results and reviewed exceptions.

## ADR-B2A-13 — Windows/Linux verification

- **Problem:** Determine platforms for B2-A baseline.
- **Evidence:** Miru is Linux/container-oriented; ActivityWatch includes Windows-specific watchers; Revit connector is Windows-only. Runtime behavior was not tested.
- **Proposed decision:** Use disposable Linux/container executor for Miru and separate disposable Windows executor for Windows-specific source/build/package verification if approved; no user workstation.
- **Alternatives:** Linux only; Windows only; both.
- **Trade-offs:** Both gives broader evidence but increases time, resource, and toolchain complexity.
- **Status:** BLOCKED.
- **Dependencies:** Platform matrix and disposable environments.
- **Human approval:** Explicit platform and environment approval.
- **Acceptance:** Each selected platform has pinned image/tool manifest, clean checkout, reproducible logs, teardown evidence.

## ADR-B2A-14 — Canonical verification commands

- **Problem:** Ensure future build/test steps are exact and repeatable.
- **Evidence:** Gap resolution flags `bundle licenses`, `rails spec`, unexplained rake tasks, “make or equivalent,” and failure-masking commands as unsupported or non-reproducible.
- **Proposed decision:** Derive every command from pinned upstream CI/docs/build files; record exact working directory, tool versions, inputs, expected outputs and exit code before approval.
- **Alternatives:** Execute current draft as-is; discover commands during run; restrict B2-A to static inventory.
- **Trade-offs:** Prework delays execution but avoids ambiguous or masked results.
- **Status:** BLOCKED.
- **Dependencies:** OpenCode parallel research, Claude audit, exact pinned CI and submodule inspection.
- **Human approval:** Approve final runbook and stop conditions.
- **Acceptance:** Reviewer can reproduce commands without interpretation; failures remain visible; no command runs before authorization.

## Register maintenance

Update this register only with evidence references and explicit status changes. Agent report publication may update research status; only the project owner can convert proposed choices requiring owner authority into approved decisions. Gate B2-A execution remains separately blocked until explicit authorization.
