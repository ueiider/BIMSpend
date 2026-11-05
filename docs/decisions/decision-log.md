# Decision log / progress tracker

## Status: DISCOVERY — NO MVP APPROVED
Updated 2026-11-05.

### User-stated preferences (not technical approvals)
- Commercial subscription is desired.
- Single install should deploy PC app and integrations.
- Designers should not need routine login, manual project selection, or timers.
- Auto-start when supported Autodesk applications run.
- Manager needs access from another computer to see people, projects, hours and costs.
- Product should not be branded as Revit-only; investigate broader Autodesk coverage.
- GitHub should become the persistent source of truth accessible from phone and desktop.
- Preserve brainstorm rather than prematurely finalize features or architecture.

### Hypotheses, not decisions
- Cloud dashboard, per-seat pricing, AI estimates, model element counting, historical journal recovery, variation analytics, automatic activity classification, multi-app support scope.

### Tested / observed
- User listed 101 local Revit Journal files, versions 2021–2026.
- User supplied two pricing/billing workbooks.
- User confirmed invoice quantity is billed hours, sometimes discounted relative to actual effort.
- User screenshot showed bimspend.com offered for purchase at a point in time.

### Next research questions (ordered)
1. How is actual time measured today when billed hours are discounted? What source is reliable?
2. What minimal Autodesk signals can reliably attribute time to a commercial project?
3. What manager output would materially improve quoting or billing decisions?
4. What is possible across Revit/AutoCAD/Navisworks/Civil 3D with consent and realistic maintenance cost?
5. Which functions do direct competitors already offer, and what gap is validated by prospective buyers?

### Change-log template
`YYYY-MM-DD | Idea / Hypothesis / Tested / Approved | Topic | Evidence | Decision / Next action`

### Initial entry
`2026-11-05 | Tested | Revit Journals | User PowerShell inventory | 101 journal files exist; parser feasibility unknown.`
`2026-11-05 | Tested | Billing semantics | User clarification | Quantity in sales report is hours billed, not actual time.`
`2026-11-05 | Hypothesis | Product value | Conversation | Tracking could feed cost realization and future estimates.`
`2026-11-05 | Approved | Build 01 authorization | Owner explicit decision | Owner authorized initial vertical-slice development; B2-A audit deferred, not passed. Synthetic data and adapter interfaces only; no real employee data, no monitoring, no production deploy. Branch: build/opencode-bimspend-foundation.`
`2026-11-05 | Tested | Build 01 domain layer | 7 pytest tests pass | Time-state separation, duplicate idempotency, attribution all verified. GUI shell added with Overview, Projects, Project Detail, Activity Timeline, Timesheet Review screens.`
