# BIMSpend — Development Coordination Status

**Date:** 2026-11-05  
**Owner decision:** Development authorized on 2026-11-05. The independent B2-A audit is **DEFERRED — NOT APPROVED / NOT PASSED**. This record captures the owner's instruction in this coordination branch; it does not amend `main`.  
**Coordination branch:** `work/development-coordination`  
**Scope:** Review and coordinate the two assigned development streams. No application code, merge, deployment, or employee monitoring by this coordinator.

## Current status

| Workstream | Expected branch | Remote state checked | Result |
|---|---|---|---|
| OpenCode BIMSpend foundation | `build/opencode-bimspend-foundation` | Branch search / remote branch list | **NOT FOUND**; no implementation commit or tests available to review |
| Claude integration contracts | `build/claude-integration-contracts` | Branch head `eb13fc90eb768080f6790bb364b482274860688c` | Branch exists but points to the same commit as `main`; no contract changes or deliverable present |
| OpenCode B2-A parallel research (context only) | `agent/opencode-b2a-parallel-research` | `a42874a0a4bc4bb268f7ecd9371ad749c7983950` | Published research, not implementation; useful gap evidence below |

No commit from either assigned development branch is presently reviewable. No application tests were run in this coordination task. Therefore no test is reported as passing or failing; required but absent tests are listed below.

## Verified planning baseline and source reports

The current `main` head was verified as `eb13fc90eb768080f6790bb364b482274860688c`. The current tracker and handoff still show the old **BUILD BLOCKED / awaiting approval** state; the newer owner instruction authorizes development, while the independent B2-A audit remains deferred and not approved. The owner decision is recorded here without rewriting historical reports or `main`.

Relevant sources at that baseline:

- [Context](https://github.com/ueiider/BIMSpend/blob/main/CONTEXT_FOR_AI.md)
- [Master plan](https://github.com/ueiider/BIMSpend/blob/main/MASTER_PLAN.md)
- [Task tracker](https://github.com/ueiider/BIMSpend/blob/main/TASK_TRACKER.md)
- [AI handoff](https://github.com/ueiider/BIMSpend/blob/main/AI_HANDOFF.md)
- [Candidate assessment](https://github.com/ueiider/BIMSpend/blob/main/docs/technical-feasibility/miru-activitywatch-revit-candidate-assessment-2026-11-05.md)
- [PLAN audit](https://github.com/ueiider/BIMSpend/blob/main/docs/technical-feasibility/PLAN_AUDIT_REPORT.md)
- [System architecture hypothesis](https://github.com/ueiider/BIMSpend/blob/main/docs/technical-feasibility/system-architecture.md)
- [Desktop/connector communication hypothesis](https://github.com/ueiider/BIMSpend/blob/main/docs/technical-feasibility/desktop-connector-communication.md)
- [OpenCode parallel technical research](https://github.com/ueiider/BIMSpend/blob/agent/opencode-b2a-parallel-research/docs/agents/opencode/B2A_PARALLEL_TECHNICAL_RESEARCH.md), commit `a42874a0a4bc4bb268f7ecd9371ad749c7983950`
- [B2-A technical gap resolution](https://github.com/ueiider/BIMSpend/blob/agent/opencode-b2a-gap-resolution/docs/agents/opencode/B2A_TECHNICAL_GAP_RESOLUTION.md), commit `0982411fc0d7ae0bb43508d086d71a088a575c7a`

The planning reports are research/proposals, not evidence that the combined application builds or works. ActivityWatch implementation details at exact submodule gitlinks remain NOT VERIFIED. The OpenCode B2-A research further reports that Miru's agent timesheet endpoint lacks idempotency enforcement and agent-route rate limiting; its `AgentKey` has no expiry/rotation/device binding; no durable encrypted offline queue was found; and Miru's `ProfitabilityBillingRate` is a client billing rate, not loaded internal labor cost.

## Recommended first executable vertical slice

Use a local-only, reviewable slice derived from the planning report's B3-A concept:

1. Ingest **synthetic ActivityWatch-shaped events** and synthetic Revit connector events through the agreed interfaces. Use fixture data or a fake local source by default; do not start watchers against employee sessions.
2. Normalize timestamps and source IDs, correlate a single selected Revit session/document with active/AFK intervals, and produce an observed-time candidate with provenance and confidence.
3. Present the candidate locally for review/correction. Keep ambiguous intervals unassigned.
4. Store only temporary/minimized development data. No cloud sync, Miru write, invoice, employee rollout, production credentials, or real employee data.
5. Add a separately approved developer-only Revit smoke test only if needed after contract and safety review; use a test model and do not deploy to employees.

This keeps a thin event-to-review path demonstrable while deferring production sync, real monitoring, financial reporting, and multi-tenant behavior. It is a coordination recommendation, not a claim that either assigned branch implements it.

## Application and data-flow acceptance criteria

The implementation branches should provide evidence against these criteria before an integration review:

### Application behavior

- Application starts in a safe development mode with capture and network upload disabled by default.
- Fixture-driven flow produces a local review item; the UI/API labels it **observed/candidate**, never approved, billable, invoiced, or productive.
- User can accept, correct, reject, or leave an ambiguous project mapping unresolved.
- Source outages, malformed events, duplicate events, clock skew and shutdown/restart are visible and do not silently create or lose accepted records.
- Connector contract is read-only: no document transactions, element edits, save operations, or network calls inside Revit callbacks.
- Multiple Revit documents/processes are separately correlated; no overlapping interval is counted twice.
- No raw window title, full local path, username, keystroke, screenshot, customer identity, or confidential project data is emitted by default.

### Data flow

- Every normalized event has a stable source/event ID, UTC timestamp (or explicit offset), source type, process/session correlation where available, and schema version.
- Any attribution proposal carries mapping evidence, confidence, and review state; source observations remain distinguishable from user-confirmed time.
- Duplicate input/replay is harmless within the local slice; the eventual server contract must separately define idempotency key, tenant binding and acknowledgement.
- Missing or conflicting project identity becomes unassigned/review-required, never silently mapped.
- Data lineage can be traced from fixture/input through normalized event, interval, and review item.
- No external network destination is contacted in this slice; logs and fixtures contain synthetic data only.

### Compatibility between the two agent streams

Before combining code, compare the actual artifacts against one shared checklist:

| Contract point | Compatibility rule | Current state |
|---|---|---|
| Event schema/version | Producer and consumer agree on field names, types, required/optional fields, schema version and unknown-field policy | BLOCKED — Claude contract changes absent |
| Time representation | UTC/offset, interval boundary semantics, precision, DST and clock-skew policy agree | PROPOSED — confirm in contract |
| Stable identity | Event, session, Revit process/document and project mapping identifiers have consistent scope/lifetime | BLOCKED — no deliverables |
| Attribution semantics | Observed, candidate, user-confirmed, approved, billed and internal cost are never conflated | REQUIRED from planning baseline |
| Read-only Revit behavior | Lifecycle events and metadata are bounded; no model writes or callback network I/O | REQUIRED; runtime NOT VALIDATED |
| Transport | Local IPC/authentication, serialization, retry and error envelope match producer/consumer | BLOCKED — transport undecided in main |
| Persistence | Data minimization, encryption, retention, replay and deletion requirements are explicit | BLOCKED — not in initial slice |
| Miru compatibility | No assumptions that Miru provides idempotency, offline sync, project-read agent command or rate limiting | GAP CONFIRMED by OpenCode research |
| Version/platform | Revit target versions, .NET builds, Windows packaging and local source versions match | NOT VALIDATED |
| Safe mode | Fixtures can run with no monitoring and no network egress | ACCEPTANCE REQUIREMENT |

Claude owns the integration-contract artifacts; OpenCode owns the foundation implementation. This report does not create either deliverable or prescribe their internal implementation.

## Integration checklist

For each future commit, review only after its remote SHA and changed-file list are available:

- [ ] Confirm branch and exact commit SHA; ensure changes stay within that agent's assigned scope.
- [ ] Read the commit diff and any linked contract/version changes.
- [ ] Match all producer/consumer schemas and error semantics; record mismatches by field and path.
- [ ] Confirm safe default: no employee monitoring, external upload, production secrets, or real data.
- [ ] Confirm read-only Revit boundary and version-specific project targets.
- [ ] Inspect tests for schema compatibility, time boundaries, unknown/invalid events, AFK, duplicate/replay, multiple sessions, and ambiguous attribution.
- [ ] Inspect tests for no network egress in local slice, no raw sensitive fields, and no model mutation.
- [ ] Run only tests explicitly assigned/authorized to the development task; report exact command, environment, exit code and failures. This coordinator has not run tests.
- [ ] Record missing tests as **MISSING**, tests not run as **NOT VALIDATED**, failures as **FAILING** with commit and evidence.
- [ ] Do not merge either branch or resolve scope ownership without explicit approval.

## Missing tests / current review gaps

Because there are no implementation commits on the expected OpenCode branch and no contract diff on the Claude branch, these are **missing evidence**, not inferred test failures:

1. Contract schema validation and producer-consumer compatibility tests.
2. Timestamp/interval tests: boundaries, overlaps, timezone/DST, clock skew and gaps.
3. AFK filtering, duplicate delivery and deterministic replay tests.
4. Multiple Revit processes/documents, active-document switching and session close/reopen tests.
5. Ambiguous/renamed/missing project mapping and user correction tests.
6. Privacy tests asserting no raw title/path/user-sensitive fields in output or logs.
7. Safe-mode test asserting fixtures run without watcher process or network egress.
8. Connector read-only test/evidence for no document modification and no blocking callback work.
9. Error/restart/recovery tests proving invalid input is quarantined and accepted review items persist as designed.
10. Tenant/auth/idempotency/rate-limit and encrypted offline storage tests are outside the first local-only slice; required before any server sync or employee pilot.

**Test status:** No failing tests identified because no target implementation tests or runs were available. Required tests above are MISSING; runtime/build/security status remains NOT VALIDATED.

## Handoffs and stop conditions

- **OpenCode:** publish the foundation branch and exact remote commits; include run instructions, changed files, tests, and known gaps. Do not wait for Claude to continue independent foundation work.
- **Claude:** publish the integration contract on its branch with schema/version, examples, identity/time/error semantics and test vectors. Current branch is still at main; no contract artifact has been verified.
- **Coordinator:** compare commits and contracts when both are available, report actionable incompatibilities and failing/missing tests. No implementation overlap.
- **Owner:** review the bounded slice and any unresolved decisions before a wider sync/monitoring scope.

Stop integration if event semantics differ, sensitive data appears by default, Revit writes are possible, local fixtures initiate network upload, server retries can duplicate time entries, or a branch exceeds its assigned scope.

## Decision and limits

Development is authorized by the owner instruction dated 2026-11-05. The authorization does **not** mean:
- independent B2-A audit passed;
- B2-A build/security/license evidence was generated;
- production monitoring or employee deployment is authorized;
- Miru/ActivityWatch integration is validated;
- either development branch is ready to merge.

No code was changed, no builds/tests were run, no branches were merged, and no employee monitoring was enabled in preparing this coordination report.
