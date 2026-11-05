# BIMSpend — Task Tracker

Updated: 2026-11-05
Current phase: **PHASE 1 — PLAN COMPLETE / AWAITING APPROVAL**
Build status: **BLOCKED — explicit approval required**

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
| B2-01 | Run isolated reproducible baseline builds/tests | BLOCKED | Proposed Gate B2-A; only after user approves |
| B3-01 | Prototype end-to-end event -> project -> manager report | BLOCKED | Proposed Gates B3-A/B3-B; only after later approvals |

## Audit conclusion

Preferred direction: Miru administrative foundation + existing Miru agent API; ActivityWatch local-only collector consumed through an adapter; read-only versioned Revit connector sends signals to the adapter. Do not expose ActivityWatch to the cloud and do not deep-merge the codebases.

## Next single action

**Approval decision:** user reviews `docs/technical-feasibility/PLAN_AUDIT_REPORT.md`. If explicitly approved, execute only **Gate B2-A / B2-01**: isolated reproducible baseline builds, recursive SHA capture, SBOM/license inventory and security scans. No product integration or UI build.

## Working rules

Build remains blocked. Update status only with evidence. Use synthetic/test data. Never infer actual or billable time from foreground activity. Do not modify FBT Revit Academy. Tests not executed are marked **NÃO VALIDADO**.
