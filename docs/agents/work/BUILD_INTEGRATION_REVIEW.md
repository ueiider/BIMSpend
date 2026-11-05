# BIMSpend Build Integration — bounded review

**Date:** 2026-11-05. **Scope:** source review and static schema parse at exact remote commits. Development authorized; independent B2-A audit deferred, not passed. No merge, deployment, employee monitoring, or production-readiness claim.

## Pinned state

| Source | Remote head | Status |
|---|---|---|
| main | `eb13fc90eb768080f6790bb364b482274860688c` | planning baseline |
| OpenCode foundation | `87d0eb107371a5f882f80914caf2fa343489c6f3` | Python/SQLite synthetic CLI slice, seven test functions present |
| Claude contracts | `68e4a791ea72e527aa888c33773eb07eb8b8a485` | draft documentation, nine JSON schemas; no executable integration |
| Work UI specification | `9e32d6e34c8ef63a557b61d42d3a3b8aead3d91d` | nine conceptual screens/SVG, no UI implementation |

OpenCode branch is three commits ahead of main; Claude branch is two commits ahead. Source inspected through GitHub at those heads. The UI specification is at `docs/product-design/BIMSPEND_INFORMATION_ARCHITECTURE_AND_UI_SPEC.md`; the SVG is conceptual.

## Executable reality and dependency matrix

| Layer | Current code/interface | Dependency to become integrated |
|---|---|---|
| UI | No GUI; `runner.py` prints CLI summaries | Implement local review UI against corrected domain states |
| Python domain | `models.py`: Project, ActivityEvent, AttributedTime, TimeEntry | State separation, validation, tenant/user scope |
| SQLite | `db.py`: projects/events/attribution/entries; event UNIQUE(source,external_id) | Encryption/retention and replay design before real data |
| Windows Adapter | No process/service | Claude event envelope, normalization, local IPC |
| ActivityWatch adapter | JSON fixture `adapters/activitywatch.py` | Exact pinned local API behavior and privacy filtering |
| Revit Connector | No executable connector | Read-only/version-specific connector and session contract |
| Miru boundary | JSON fixture `adapters/miru.py` | Authorized project read path and server idempotent draft write |
| Timesheets | Designer `approve_entry`/reject prototype | Submission then separate manager decision, never auto-bill |
| Cost/budget | Rate snapshot and labor-cost property; no budget model | Protected cost rate, approved time, budget basis and authorization |
| Reports/history | CLI project summary; no report or estimate workflow | Persisted approved/classified history and comparable-case rules |

No actual Miru, ActivityWatch or Revit integration exists at reviewed commits. No production network transmission is present in the inspected synthetic adapters/runner.

## Critical source findings (OpenCode head `87d0eb1`)

| ID | Finding and exact source | Required change / verification |
|---|---|---|
| D1 Critical | `src/bimspend/review.py:approve_entry` sets `billed_minutes=entry.minutes` by default; `runner.py` invokes it without billing argument. | Remove billing side effect. Separate invoice/billed transition and test approval leaves billed at zero. |
| D2 Critical | `models.py:TimeEntryState` has pending_review/approved/rejected only; `review.py` uses designer as approver; `dashboard.py` counts this as approved and cost-relevant. | Add explicit designer confirmed/submitted and manager approved states/actors, with audit and permissions. |
| D3 High | `correlation.py:correlate_events` chooses `user_projects[0]` at confidence 0.35 for unmatched title with user_id. | Abstain on ambiguous input; preserve unassigned review queue; test Outlook/unknown and multiple possible projects. |
| D4 High | `runner.py` builds project `observed_hours` using attributed minutes, while raw event totals are keyed by user and unused. | Derive observed totals from actual event provenance or mark project observed unavailable; test observed != attributed. |
| D5 High | `models.py:ActivityEvent` and `db.py:activity_events` store raw `window_title` and payload in plain SQLite. | Synthetic only now. Add minimization/redaction/retention before real capture; no raw title to manager UI. |
| D6 High | `runner.py` uses persistent `bimspend_demo.db`; second run has zero newly ingested events, so displayed observed/attributed totals can drop while prior entries remain. | Make demo deterministic or recompute from persisted state; test restart/replay. |
| D7 High | `adapters/miru.py` claims project-read via Miru integration but the pinned AgentKey endpoint only supports `time create`. | Define authorized project read interface separately; no invented agent GET endpoint. |
| D8 Medium | `README.md` and `docs/RUNBOOK.md` instruct `cd src; pip install -e .`, while `pyproject.toml` is at repo root. | Fix run instructions at repo root and verify clean environment. |
| D9 Medium | `dashboard.py` realization uses billed/observed. The product financial definition uses billed/actual comparable hours; observed attention is not actual effort. | Label separate diagnostic ratio or calculate realization from approved/verified hours with defined basis. |

OpenCode source includes seven tests in three files: attribution, event deduplication and time-state calculations. Their presence is verified; pass/fail is not independently verified here. These tests do not cover D1–D9 adequately.

## Claude contract compatibility

Nine JSON schema files at `docs/agents/claude/contracts/schemas/` parsed successfully as JSON during this review (**9/9 JSON syntax PASS**). This is not JSON Schema semantic validation, fixture validation, or a runtime contract test. The accompanying `tests/README.md` contains proposed test snippets/commands, not an executable test suite in the published branch.

| ID | Contract versus foundation | Action |
|---|---|---|
| C1 Critical | Claude `envelope.schema.json` requires UUID event/session/run IDs; OpenCode fixtures use `evt_001`/`aw_evt_001`, and models lack envelope/source/correlation fields. | Publish an explicit fixture-to-envelope mapping and validate both producer/consumer against same sample. |
| C2 Critical | Claude correlated and ingestion schemas require UUID `project_id`; OpenCode uses `proj_001`. | Agree canonical project ID type, or versioned translation layer with stable tenant binding. |
| C3 Critical | Claude `adapter_correlated_activity.schema.json` requires `attribution.project_id` and name, so an unassigned/ambiguous interval cannot conform. | Support null/absent project plus reason/review state; test abstention. |
| C4 High | Claude ingestion draft requires integer `duration_minutes`; OpenCode `TimeEntry.minutes` is float. | Specify rounding/precision and reconcile split intervals before any upload. |
| C5 High | Claude model identity schemas permit file path, central path and document title; ingestion draft includes central path. | Enforce local redaction/hash rules and schema restrictions before upload; privacy proof test. |
| C6 High | Claude queue/idempotency docs propose server uniqueness and retry/ack/409 handling; OpenCode only deduplicates local event IDs. | Add independent draft submission key, server constraint and replay tests before Miru sync. |
| C7 High | Claude metrics say manager approval precedes billing; OpenCode's designer approval auto-bills. | Resolve D1/D2 before contract adoption or manager UI. |
| C8 Medium | Claude documents versions/queue/Revit API behavior, but no runnable adapter, Revit code, queue implementation or contract tests. | Label as specification; implement and validate in owned branches before integration. |

A JSON document parsing is not proof its referenced schemas resolve or its examples satisfy the schema. No version compatibility with running components was established.

## UI inventory versus code

| Screen | Status at OpenCode head |
|---|---|
| Overview Dashboard | CLI aggregate only; no screen |
| Projects | Synthetic project adapter/SQLite records; no screen or user CRUD |
| Project Details | No screen |
| Activity Timeline | Synthetic events/correlation; no screen |
| Timesheet Review | Designer helper only; no manager workflow/screen |
| Team Management | No users/roles/screen |
| Project Costs and Budgets | Cost property only; no budget/screen |
| Reports and Historical Estimating | CLI summary only; no historical estimating |
| Settings and Privacy Controls | No screen, no policy controls |

No navigation or interactive controls exist to evaluate for accessibility or breakage. The Work SVG remains a visual concept.

## Acceptance scenarios and test evidence

**Execution attempt:** A GitHub clone into the isolated workspace produced no checkout before interruption; the alternate source reconstruction did not complete. No Python application command or pytest command ran in this review. Thus no application scenario is marked PASS. Reproduce at OpenCode SHA in an isolated checkout from repository root, after fixing D8: `python -m pytest tests -v`; `$env:PYTHONPATH='src'; python -m bimspend.runner`. Use only synthetic fixtures. Record command, environment, output and exit code.

| # | Scenario | Source capability | Test result |
|---|---|---|---|
| 1 | Launch | CLI runner exists | NOT RUN |
| 2–3 | Create/edit project | SQLite upsert exists; no UI | NOT RUN; UI MISSING |
| 4 | Ingest synthetic activity | Fixture adapter + event insert | NOT RUN |
| 5 | Attribute activity | Correlator exists | NOT RUN |
| 6 | Leave ambiguity unassigned | Fallback violates criterion when user_id provided | SOURCE FAIL (D3); runtime NOT RUN |
| 7 | Review entry | Designer helper exists | NOT RUN; partial |
| 8–9 | Submit and manager approve/reject | No distinct workflow | MISSING |
| 10 | Approval does not bill | Default code violates criterion | SOURCE FAIL (D1); runtime NOT RUN |
| 11 | Labor cost | Property exists | NOT RUN |
| 12 | Budget versus actual | No budget model | MISSING |
| 13 | Report | CLI summary only | NOT RUN; partial |
| 14–15 | Restart and persistence | SQLite exists; runner replay defect D6 | NOT RUN |
| 16 | No live monitoring/upload | Only fixture adapters/runner inspected | STATIC EVIDENCE; runtime NOT RUN |

A source finding is not an executed test failure. Required new tests: manager state/authorization, approval without billing, ambiguous abstention, raw title redaction, project observed aggregation, rerun/persistence, UUID/ID mapping, schema validation, cross-tenant rejection, queue crash recovery and Revit read-only/multi-process behavior.

## Preview release checklist

| Check | State |
|---|---|
| CLI application launch / tests pass | NOT RUN independently |
| Basic synthetic event flow | Implemented in code, execution NOT RUN |
| Project creation/edit UI, timesheet submission/manager approval | MISSING |
| Correct metric and billing semantics | BLOCKED D1/D2/D4/D9 |
| Persistence across restart | Code exists, D6 risk, NOT RUN |
| No live monitoring / no real data | Fixture-only code observed; verify at runtime |
| No production credentials/upload | None found in inspected runner/adapters |
| Run instructions | Present, incorrect working directory D8 |
| Exact source reproducibility | SHAs pinned; clean run NOT VERIFIED |
| Known limitations | This review and upstream runbook |

**Development-preview verdict: NOT READY.** A command-line synthetic prototype exists, but the required core domain defects, user workflows and launch/test evidence remain. Production readiness is not assessed.

## Product completeness and priority

| Capability | Status | Next priority |
|---|---|---|
| Miru reuse | Mocked fixture adapter | P2 authorized read + idempotent write boundary |
| ActivityWatch reuse | Mocked JSON adapter | P2 privacy-minimized exact local API |
| Windows Adapter | Planned | P2 after contract reconciliation |
| Revit Companion | Planned | P3 versioned read-only test connector |
| Company Workspace | Planned | P2 tenancy/roles/UI shell |
| Timesheets | Partial, incorrect state | **P0** D1/D2 |
| Team management | Planned | P3 |
| Cost intelligence | Partial property with unsafe state basis | **P0** gate calculations by manager approval |
| Budgeting | Planned | P2 |
| Billing | Mocked `billed_minutes` field, incorrect default | **P0** separate billing |
| Reporting | Partial CLI aggregation, D4/D9 | **P1** correct totals |
| Historical estimating | Planned | P3 after reliable approved history |

**Next actions:** (1) OpenCode fixes D1–D4/D6/D8 and adds focused regression tests in its branch; (2) Claude reconciles C1–C5 and publishes runnable schema fixtures/tests in its branch; (3) Work rechecks pinned heads and tests a combined isolated checkout once artifacts are compatible; (4) implement minimal local UI over corrected synthetic states; (5) review preview again. No merge without owner approval.
