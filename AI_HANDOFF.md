# BIMSpend — AI Handoff

Last updated: 2026-11-05
Mode: **PLAN ONLY** — research, inspect, reason, and document. No implementation.

## Read in this order
1. `CONTEXT_FOR_AI.md`
2. `MASTER_PLAN.md`
3. `TASK_TRACKER.md`
4. `docs/technical-feasibility/miru-activitywatch-revit-candidate-assessment-2026-11-05.md`

## Mission for next agent
Determine how much of BIMSpend can be delivered by **reusing existing open-source software** rather than creating new code. Audit `https://github.com/saeloun/miru-web` and `https://github.com/ActivityWatch/activitywatch`; assess a read-only Revit connector. Provide an evidence-backed, scoped plan, **not a build**.

## Current known findings
- Miru is a promising MIT-licensed administrative app for projects, team, time entries, invoices and reporting. Current code and dependencies have **not** been audited here.
- ActivityWatch is an MPL-2.0 local-first tracker with active-window and AFK watchers; its data cannot be assumed to measure productive hours.
- Combined integration, security, multi-tenancy, scalability and Revit project mapping **not yet proven**.
- Designer should see only relevant own activity and timelog-assistance functions; manager has full management/finance capabilities. Exact permissions are unapproved design hypotheses.
- Web manager dashboard with mobile responsive access; background Windows agent; optional Autodesk connector. No architecture approved.
- Historical Revit Journals are diagnostic, not exact actual-hours data.

## PLAN-mode deliverables
- Pinned upstream revisions, component maps, license/dependency inventory.
- Feature matrix READY / CONFIGURE / ADAPT / BUILD / UNKNOWN.
- Specific APIs/events and expected integration boundaries, with source path references.
- Risks: privacy/consent, workplace surveillance, tenant isolation, auth, dependency vulnerabilities, maintenance and distribution licensing.
- Smallest reproducible prototype proposal and acceptance tests, with rough estimates explicitly marked estimates.
- `docs/technical-feasibility/PLAN_AUDIT_REPORT.md`, tracker updates, and this handoff updated with evidence and unresolved issues.

## Prohibitions
Do not implement, fork, install on user devices, deploy, edit FBT Revit Academy, modify BIMSpend product code, publish sensitive files, claim tests were run when they were not, or declare MVP approved. Do not auto-advance to BUILD. Ask the user for approval after PLAN report.

## Token discipline
Use repository search and narrow file reads, cache factual summaries in GitHub, avoid repeatedly ingesting entire repositories, use local automation/models for mechanical inspection, and report only decisions/evidence. When an agent ends, include next task ID and blockers.

## Next action
Start **P1-01** in PLAN mode. Save factual findings and stop before implementation.
