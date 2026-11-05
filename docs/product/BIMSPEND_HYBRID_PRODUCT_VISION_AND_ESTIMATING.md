# BIMSpend — Hybrid Product Vision & Historical Estimating Brainstorm
Date: 2026-11-05
Status: PRODUCT DISCOVERY / PROPOSAL — NOT APPROVED IMPLEMENTATION
Origin: Owner–assistant product brainstorm. Illustrative numbers are not empirical evidence.

## 1. Product thesis
BIMSpend is an integrated **BIM work intelligence, project control, and estimating** platform. Its central feedback loop is:
**Detect activity → associate project → designer describes work → validate/approve timelog → attribute labor cost → track project budget → build a structured historical dataset → estimate future project effort and price.**

This is not merely a timesheet, passive computer monitor, or billing application. Its intended commercial buyer includes **owners and managers of engineering and architecture design businesses** who need reliable project pricing, ongoing visibility into designers' effort, cost, budget consumption, and evidence-backed historical benchmarks. Designers should receive a low-friction experience rather than burdensome reporting.

## 2. Intended audiences and workflows
**Designer / My Workspace:** locally detected sessions, suggested project/model associations, editable daily/weekly timelogs, classification, written descriptions of actual work, review and submission, clear confidence/uncertainty indicators. Capture should minimize manual entry but never substitute for a person's account of their work.

**Business owner / Management Workspace:** project portfolio, scoped budgets, actual and committed labor hours/costs, estimated completion, phase and discipline breakdown, timesheet approvals, change/rework visibility, historical comparables, and proposed fees for future projects. Respect role-based permissions and privacy.

**Commercial positioning:** company-wide integrated experience (capture/timelog for designers; controls/estimating for managers), with potential future modular packaging. Support solo practitioners later/where feasible; commercial packaging remains undecided.

## 3. Core modules
1. **Smart Tracking** — local ActivityWatch activity signals and read-only Revit document/session context; possible future sources. Detection is evidence of application activity, NOT proof of productive or billable work.
2. **Timesheets & Approvals** — project and work-package attribution; editable entries; task descriptions; classifications; billable/non-billable; designer review, manager approval, audit trail.
3. **Project Management / Control** — customers, projects, phases, disciplines, systems, tasks, budgets, deliverables, progress and change events.
4. **Financial Intelligence** — loaded internal labor costs, client billing rates, contracted fees, actual invoicing, cost-to-complete, margin and overruns; maintain distinct concepts and historical rate snapshots.
5. **BIM Intelligence / Smart Estimating** — structured historical hours/costs, project complexity characteristics, comparable-project analysis, estimates and confidence ranges. Advanced productivity insights are future scope.

## 4. Example timelog record
- Project: 20–30 Lee Street (illustrative scenario)
- Discipline: Fire Protection
- System: Sprinklers
- Phase: Detailed Design
- Work package: BIM Coordination
- Activity: Resolving pipe/duct clashes, or sprinkler layout revisions due to ceiling changes
- Designer description: free text plus controlled taxonomy
- Activity evidence: local application events and read-only Revit model association, with timestamps and source provenance
- Detected duration / designer-declared duration / manager-approved duration: **separate fields**
- Confidence and reason for mismatch: explicit
- Billable status, change reason, deliverable, reviewer, approval timestamp and change history
- Loaded labor cost rate **as of work date** and relevant billing rate, stored distinctly
- Offline synchronization status, stable IDs and idempotency requirements

**Important:** Work may happen in meetings, on paper, in design thinking, and in non-Revit apps. Lack of activity does not prove no work. Conflicting signals prompt clarification, not accusations or automatic fraud labeling. Review consent, transparency, retention and access controls before implementing monitoring.

## 5. Historical dataset / knowledge flywheel
Approved and properly classified timelogs form a **structured history of engineering effort** rather than only an accrued-hour balance. Index by client, project type, building type, area, levels, units, discipline, system, phase, work package, complexity, deliverable, team composition, design revisions and change reasons where legitimately available. Preserve source provenance, corrections, approval states and scope boundaries.

Example questions:
- Typical sprinkler layout hours per comparable residential level?
- Coordination hours by complexity and phase?
- Impact of architectural revisions on sprinkler head layouts and rework?
- How many hours and what labor cost did shop drawings consume?
- What effort range should be included in a new fee proposal?

Do not treat sparse, inconsistent or unapproved historical data as reliable benchmarks. Historical comparability, sample size, outliers, scope normalization, confidence intervals, inflation/rate changes and human override are necessary for mature estimating.

## 6. Smart Estimating concept
Manager enters prospective project characteristics (building type, floors, area, units, disciplines, system scope, deliverables, complexity, design stage, expected coordination and revisions). BIMSpend proposes effort ranges from comparable approved historical work, with evidence, sample sizes and assumptions; manager adjusts inputs and applies loaded labor cost, contingency/overhead and target margin to form an indicative price.

**Illustrative simplified formula only:** hours = levels × assumed hours/level; labor cost = hours × loaded hourly cost; indicative selling price = eligible cost / (1 - target gross margin). A gross margin is NOT a markup. This simplified calculation omits overhead, subcontractors, expenses, taxes, contingency and contract-specific scope and must not be mistaken for a quotation or a validated benchmark. The prior brainstorm used sliders such as 12 levels, 18 h/level, AUD 65/h, 30% target margin solely as fictional examples.

## 7. Live project control
Show **budgeted vs actual** hours and costs by phase, discipline and work package; unassigned/pending timesheets; budget remaining; forecast at completion; change/rework and fee variations. Separate measured effort from actual deliverable progress: spending 75% of hours alone does not prove the project is 75% complete. Flag deviations and let managers investigate.

Example illustrative project: 300 budgeted hours, 224 recorded, 76 remaining, AUD 14,560 labor cost at AUD 65/h. These are fictional UI examples, not verified project data.

## 8. Product experience proposal
**Daily Review:** detected vs attributed vs unassigned time, project suggestions, confidence indicators, activity taxonomy, descriptions, correction and submission. An illustrative mockup showed 7h42 detected, 6h35 attributed, 1h07 needing review. Those are fictional.
**Management dashboard:** portfolio and project drill-down; hours/cost budgets, work packages, approval queues and variance signals.
**Estimating workspace:** comparable-project selector, assumptions, hour range, cost/rate policy, target margin, fee proposal and rationale.
**Auditability:** evidence → declared timelog → approved timelog → historical estimate lineage.

## 9. Proposed MVP boundaries
Initial Windows + Revit environment, using Miru business foundation, ActivityWatch local activity collection, BIMSpend Windows Adapter and a **read-only Revit Connector**. Proposed MVP includes customer/project setup, basic tracking and project attribution, designer timelog review, minimal approval policy, separate cost/billing rates, basic financial dashboard and foundational structured activity taxonomy. Initial estimation may be manual or rule-based until sufficient validated history exists.

Later phases: advanced statistical estimating, multiple BIM tools (e.g. Navisworks/AutoCAD), richer team permissions, sophisticated forecasting, and BIM-specific productivity insights. Do not imply those are already built.

## 10. Architectural boundaries / constraints
- **Miru**: proposed business foundation; pinned upstream commit `10e457e1d0cd2ac782be9d1edbcbd5a1a573486a`.
- **ActivityWatch**: proposed local monitoring foundation; pinned bundle `9fee4702fea08dbe0149cc6e28f4ef66b49f54ec`. Submodule internals remain unverified unless actually inspected.
- **BIMSpend Windows Adapter**: new integration/normalization and offline processing boundary.
- **Revit Connector**: read-only metadata/session context; no model modification.
- Offline encrypted durable persistence, privacy, idempotency, identity reconciliation, license/SBOM checks, Windows/Linux reproducibility and canonical commands remain technical review topics, not solved by this brainstorm.

## 11. Open product decisions
1. Exact minimum timelog taxonomy: discipline, system, phase, work package, activity and change reason.
2. What counts as an approved historical benchmark and who can correct it?
3. How to quantify project scope and deliverable completion independently from recorded hours?
4. How to distinguish labor cost, billing rate, contract fee, invoiced revenue, gross margin and overhead in the UI?
5. Which signals can be retained, for how long, and who can see individual-level activity?
6. How to attribute cross-application work and multiple simultaneous Revit instances?
7. When is a comparable-project estimate statistically useful, and how are uncertainty and sparse samples displayed?
8. MVP deployment, roles, solo-user support, subscription/module packaging and commercial pricing.
9. How to record scope variations, revisions, rework and their financial attribution.
10. How to avoid monitoring being interpreted as a direct measure of employee worth/productivity.

## 12. Agent coordination and governance
As of this brainstorm, three agents are designated: **Claude Code via FCC/NVIDIA NIM** (independent B2-A audit), **OpenCode** (parallel technical research), and **ChatGPT Work** (architecture consolidation). Claude Desktop Free is excluded due to usage limits. Do not assert unpublished deliverables are completed. Work in separate branches; no changes to main, no merges, no implementation/build/test, and **Gate B2-A stays BLOCKED pending explicit owner approval**.

This file is a **product-vision reference for future planning**. It does not amend approved technical architecture, authorize development, or replace evidence-backed reports. Reconcile proposals with agent audits before adopting them.
