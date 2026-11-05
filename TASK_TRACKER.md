# BIMSpend — Task Tracker

Updated: 2026-11-05
Current phase: **PHASE 1 — PLAN**
Build status: **BLOCKED — explicit approval required**

| ID | Task | Status | Evidence / deliverable |
|---|---|---|---|
| P0-01 | Document open-source candidates and preliminary go/no-go | DONE | docs/technical-feasibility/miru-activitywatch-revit-candidate-assessment-2026-11-05.md |
| P0-02 | Establish master plan, task tracker, AI handoff | DONE | MASTER_PLAN.md, TASK_TRACKER.md, AI_HANDOFF.md |
| P1-01 | Pin Miru + ActivityWatch upstream SHAs, license and third-party inventory | TODO | Audit report with source links/paths |
| P1-02 | Miru feature, architecture, API, auth, tenancy and security static audit | TODO | Reuse matrix and evidence |
| P1-03 | ActivityWatch watcher, event, Windows install, API and privacy static audit | TODO | Reuse matrix and evidence |
| P1-04 | Revit read-only connector feasibility, model identity, multi-instance research | TODO | Integration options |
| P1-05 | Compare fork vs API/adapter; compatibility and deployment options | TODO | Decision matrix |
| P1-06 | Threat/privacy/legal risk register and acceptance criteria | TODO | Risk register |
| P1-07 | Produce staged implementation proposal and explicit approval gate | TODO | docs/technical-feasibility/PLAN_AUDIT_REPORT.md |
| B2-01 | Run isolated reproducible baseline builds/tests | BLOCKED | Only after user approves |
| B3-01 | Prototype end-to-end event -> project -> manager report | BLOCKED | Only after user approves |

## Next single action
**P1-01:** In PLAN mode, pin upstream SHAs and inspect top-level licenses and dependencies for Miru and ActivityWatch. Record citations and uncertainties; **no code changes**.

## Working rules
Update statuses only with evidence. Do not mark an item DONE because it is planned. No installation, deployment, production changes, or push to upstream projects without permission. Use synthetic fixtures only. If agent has no repository access, say so; do not fabricate verification.
