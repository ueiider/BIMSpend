# BIMSpend — Task Tracker

Updated: 2026-11-05
Current phase: **PHASE 1 — PLAN COMPLETE / BUILD 01 AUTHORIZED**
Build status: **AUTHORIZED — owner approved 2026-11-05; B2-A audit deferred, not passed**

| ID | Task | Status | Evidence / deliverable |
|---|---|---|---|
| P0-01 | Document open-source candidates and preliminary go/no-go | DONE | docs/technical-feasibility/miru-activitywatch-revit-candidate-assessment-2026-11-05.md |
| P0-02 | Establish master plan, task tracker, AI handoff | DONE | MASTER_PLAN.md, TASK_TRACKER.md, AI_HANDOFF.md |
| P1-01 | Pin Miru + ActivityWatch upstream SHAs, license and third-party inventory | DONE (static) | PLAN_AUDIT_REPORT.md §§2,11; transitive inventory/runtime scans NÃO VALIDADO |
| P1-02 | Miru feature, architecture, API, auth, tenancy and security static audit | DONE (static) | PLAN_AUDIT_REPORT.md §3 |
| P1-03 | ActivityWatch watcher, event, Windows install, API and privacy static audit | DONE (static) | PLAN_AUDIT_REPORT.md §4; Windows runtime NÃO VALIDADO |
| P1-04 | Revit read-only connector feasibility, model identity, multi-instance research | DONE (research) | PLAN_AUDIT_REPORT.md §5; live Revit/ACC NÃO VALIDADO |
| P1-05 | Compare fork vs API/adapter; compatibility and deployment options | DONE | PLAN_AUDIT_REPORT.md §§6–7 |
| P1-06 | Threat/privacy/legal risk register and acceptance criteria | DONE (planning) | PLAN_AUDIT_REPORT.md §8; legal compliance NÃO VALIDADO |
| P1-07 | Produce staged implementation proposal and explicit approval gate | DONE | PLAN_AUDIT_REPORT.md §§9–10 |
| B2-01 | Run isolated reproducible baseline builds/tests | AUTHORIZED — BUILD 01 | Owner approved 2026-11-05; B2-A audit deferred; baseline validation documented in build branch |
| B3-01 | Prototype end-to-end event -> project -> manager report | AUTHORIZED — BUILD 01 | Owner approved 2026-11-05; vertical slice implemented in build branch |

## Audit conclusion

Preferred direction: Miru administrative foundation + existing Miru agent API; ActivityWatch local-only collector consumed through an adapter; read-only versioned Revit connector sends signals to the adapter. Do not expose ActivityWatch to the cloud and do not deep-merge the codebases.

## Next single action

**Approval decision:** user reviews `docs/technical-feasibility/PLAN_AUDIT_REPORT.md`. If explicitly approved, execute only **Gate B2-A / B2-01**: isolated reproducible baseline builds, recursive SHA capture, SBOM/license inventory and security scans. No product integration or UI build.

## Working rules

Build remains blocked. Update status only with evidence. Use synthetic/test data. Never infer actual or billable time from foreground activity. Do not modify FBT Revit Academy. Tests not executed are marked **NÃO VALIDADO**.


## Open-source architecture realignment — 2026-11-05

| ID | Task | Status | Evidence |
|---|---|---|---|
| OSA-01 | Verify BIMSpend P0 baseline and prior reuse decisions | DONE (static) | P0 HEAD `03c47f37ff37f0126170305a1c4f220b9ea22a68`; prior reports reconciled |
| OSA-02 | Resolve ActivityWatch bundle gitlinks and inspect capture/AFK/core/client/server/manager source | DONE (static) | `docs/architecture/OPEN_SOURCE_REUSE_MATRIX.md` |
| OSA-03 | Inspect Miru company/auth/project/team/timesheet/rate/billing/report source and tests | DONE (static) | pinned Miru `10e457e1d0cd2ac782be9d1edbcbd5a1a573486a` |
| OSA-04 | Define independent BIMSpend target architecture | DONE (planning) | `TARGET_ARCHITECTURE.md` |
| OSA-05 | Map current gaps and migration risks | DONE (static/planning) | `FEATURE_GAP_ANALYSIS.md` |
| OSA-06 | Produce source-specific reuse-first implementation sequence | DONE (planning) | `IMPLEMENTATION_SEQUENCE.md` |
| OSA-07 | Record licensing/dependency boundaries | DONE (static); legal/SBOM NOT VALIDATED | `LICENSING_AND_DEPENDENCIES.md` |

**Architecture correction:** ActivityWatch and Miru are not mandatory runtime services. BIMSpend owns its collector, idle detection, Revit connector, database and business domain. Bounded ActivityWatch source may be adapted under an explicit MPL boundary; Miru business behavior/tests should primarily be ported to Python.

**Remaining blockers:** legal approval of MPL distribution method; transitive SBOM/vulnerability scans; Windows runtime/package validation; P0-009/P0-010 authentication; tenant migration design; production privacy/workplace review.

**Next exact engineering action:** after owner review, complete P0 authentication/session and domain authorization before adding native background capture. No implementation was authorized or performed by this audit.
