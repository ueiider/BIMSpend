# BIMSpend — AI Handoff

Last updated: 2026-11-05
Mode: **PLAN COMPLETE — AWAITING USER APPROVAL. BUILD BLOCKED.**

## Read in this order

1. `CONTEXT_FOR_AI.md`
2. `MASTER_PLAN.md`
3. `TASK_TRACKER.md`
4. `AI_HANDOFF.md`
5. `docs/technical-feasibility/miru-activitywatch-revit-candidate-assessment-2026-11-05.md`
6. `docs/technical-feasibility/PLAN_AUDIT_REPORT.md`

## Completed work

P1-01 through P1-07 were completed as a static/research audit. The full evidence, reuse matrix, risk register, architecture, acceptance criteria and effort ranges are in `PLAN_AUDIT_REPORT.md`.

Pinned primary revisions:

- Miru: `10e457e1d0cd2ac782be9d1edbcbd5a1a573486a` (`develop`)
- ActivityWatch bundle: `9fee4702fea08dbe0149cc6e28f4ef66b49f54ec` (`master`)

## Key findings

1. Miru already exposes `POST /api/v1/agent/timesheet_entries` with bearer `AgentKey`, company/user binding, project scope, source/proof metadata, external run/session identifiers and pending review.
2. Miru already provides companies, clients, projects, team membership, timesheets, bill states, invoices, reports, audit history and role policies. It is the strongest reuse base.
3. Miru needs validation/adaptation for ingestion idempotency, agent rate limiting, device credential operation, exact manager role coverage, cross-tenant tests and BIMSpend financial/attribution semantics.
4. ActivityWatch provides reusable local window and AFK heartbeats, local API/history and privacy filters. Keep it on loopback; do not use it as a cloud multi-tenant service.
5. The smallest custom components are a local secure adapter/correlation queue and a read-only versioned Revit connector.
6. Revit connector signals must be correlated outside Revit to avoid multiple-process/document double counting. Autodesk Idling is not a human-idle or productivity signal.
7. Preferred pattern: **API/adapter first**, narrow Miru fork only if proven necessary; avoid modifying ActivityWatch covered files where possible.
8. Manager-only finance/full reports and designer own-history/review remain the provisional role split.
9. Observed activity, attributed/approved time, billed hours and loaded internal cost remain separate.

## Validation boundary

Static source and official-document research completed. The following remain **NÃO VALIDADO**: clean builds/tests, recursive ActivityWatch gitlink capture, transitive license/SBOM and CVE scans, Windows install/runtime/performance, live Revit and ACC identity, tenant-negative tests, penetration tests, backup/restore, legal compliance and production readiness.

## Recommended next gate

Await explicit user approval. If approved, execute only **Gate B2-A / B2-01** from the report (estimated 3–5 engineer-days):

1. isolated checkouts at pinned SHAs;
2. recursive submodule SHA capture;
3. reproducible builds/tests;
4. SBOM/license inventory;
5. dependency/container security scans;
6. evidence and stop/go report.

Do not implement the adapter, Revit connector, Miru modifications, branding or product UI under B2-A.

## Prohibitions

Do not auto-advance to BUILD. Do not install on the user's machine, deploy, use confidential data, modify product code, touch FBT Revit Academy, expose ActivityWatch remotely, or equate window focus with actual/billable work.
