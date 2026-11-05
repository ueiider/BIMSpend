# BIMSpend — Master Plan

Updated: 2026-11-05
State: **BUILD 01 AUTHORIZED (2026-11-05).** Owner explicitly authorized initial vertical-slice development. Independent B2-A audit deferred, not passed.

## North star
Create a commercial, low-friction project time-and-cost intelligence product by **reusing proven existing software**, not recreating it. Preserve distinct metrics for observed activity, verified project hours, billed hours, and loaded internal cost.

## Non-negotiables
- **Plan before build.** No product implementation until explicit user approval of a scoped task.
- Reuse-first: evaluate forks, supported APIs and extension points before custom code.
- **Miru** is the first administrative foundation candidate (MIT, verify at pinned commit); **ActivityWatch** the first Windows activity tracking candidate (MPL-2.0, review distribution obligations); **Revit read-only connector** is a hypothesis.
- Windows background collection; simple designer time-log review; manager-only finance and full reporting; responsive web/mobile manager experience are user preferences / product hypotheses, not frozen MVP.
- No automatic assertion that focused-window time equals actual productive or billable work.
- No employee/customer data or company rate spreadsheets in source control.
- No modification to FBT Revit Academy; isolate experiments from BIMSpend main code.
- Every agent starts with `CONTEXT_FOR_AI.md`, this plan and `TASK_TRACKER.md`, and ends by updating `AI_HANDOFF.md` and tracker.
- GitHub is the persistent source of truth; never claim uncommitted work was pushed.

## Phase gates

### Phase 0 — Documentation and control [COMPLETE]
Create plan, tracker, handoff, and source assessment. No application code.

### Phase 1 — PLAN: repository feasibility audit [NEXT]
1. Pin upstream commits and inspect licenses/dependencies/assets.
2. Inventory existing Miru functionality, code structure, database, API and permissions.
3. Inventory ActivityWatch Windows watchers, events, APIs, storage and deployment.
4. Evaluate the least-invasive integration pattern (API/adapter vs fork).
5. Research read-only Revit document/project identity signals and versioning.
6. Build a feature-reuse matrix: READY / CONFIGURE / ADAPT / BUILD / UNKNOWN.
7. Produce threat/privacy and multi-tenancy risk registers; define proof-of-concept acceptance criteria.
8. Produce a **small, staged build proposal** with rough effort, evidence and stop/go recommendation.
**Deliverable:** `docs/technical-feasibility/PLAN_AUDIT_REPORT.md` and proposed build tasks. **Gate:** user reviews and explicitly approves first build task.

### Phase 2 — BUILD: isolated baseline execution [AUTHORIZED — BUILD 01]
Owner authorized 2026-11-05. Independent B2-A audit deferred, not passed. Vertical slice uses synthetic data and adapter interfaces. See build/opencode-bimspend-foundation branch.

### Phase 3 — BUILD: minimal event-to-project proof of concept [AUTHORIZED — BUILD 01]
Owner authorized 2026-11-05. Uses synthetic/test-user data to prove activity event -> ingestion -> project attribution -> manager view, preserving uncertainty and billed-hour separation.

### Phase 4 — Product scope / security / pilot [BLOCKED]
Only after demonstrated feasibility: agree MVP, data governance, workplace-surveillance legal review, security tests, pilot and commercial terms.

## Decision policy
- Candidate selection != architecture approval.
- Documentation updates may record hypotheses and test results; never label them APPROVED without user confirmation.
- Stop when blocked; report evidence and ask for the smallest needed decision.
- Prefer targeted file reads, static scripts and local models for repetitive inventory to conserve paid tokens.

## Reference
See `docs/technical-feasibility/miru-activitywatch-revit-candidate-assessment-2026-11-05.md`.
