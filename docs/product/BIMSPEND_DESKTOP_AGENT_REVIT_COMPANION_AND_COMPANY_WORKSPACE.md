# BIMSpend — Desktop Agent, Revit Companion & Company Workspace
Date: 2026-11-05
Status: BRAINSTORM / PROPOSED PRODUCT EXPERIENCE — NOT IMPLEMENTED OR APPROVED
Related: [Hybrid Product Vision & Historical Estimating](BIMSPEND_HYBRID_PRODUCT_VISION_AND_ESTIMATING.md)

## 1. Product opportunity
Offer engineering and architecture company owners an integrated platform for:
- Knowing how many **validated hours** designers have spent per project, phase, system and work package.
- Understanding those hours as **internal labor cost** and comparing them with approved budgets and contracted fees.
- Identifying budget pressure and scope changes early.
- Building a durable, structured, auditable **historical effort database** that improves pricing of future projects.
- Giving designers a genuinely useful, low-friction tool for reviewing their time and documenting what they accomplished.

Avoid positioning the product as employee surveillance. Active screen time is not a productivity or quality score.

## 2. Proposed user journey
1. **Install and enroll:** IT or user installs BIMSpend Desktop Agent on Windows. During setup, sign in and join an authorized company workspace; authenticate securely, configure privacy policy and permitted capture.
2. **Windows sign-in:** Agent starts quietly in the system tray according to policy, shows clear capture/sync state and offers pause/stop where allowed. **Do not launch Revit automatically at Windows login.**
3. **Company connection:** Agent authenticates, loads authorized projects and preferences, and synchronizes pending approved records. Show online/offline/authentication/queued/failed status distinctly. Connected does not imply every record is synchronized.
4. **Revit launch:** A separately installed, read-only BIMSpend Revit add-in loads with Revit and exposes a Ribbon entry / optional dockable side panel. It should not alter models or require Revit to be running for general Windows tracking.
5. **Work:** Local ActivityWatch signals and read-only Revit document/session context suggest which project is active. Handle multiple Revit instances and context switching explicitly; never silently assume the active model equals all work performed.
6. **Daily review:** Designer sees detected vs attributed vs unassigned time, proposed work sessions, classification and a written description of what was actually done. Designer can correct project, activity and duration, or mark non-work/personal time where permitted.
7. **Submission and approval:** Distinguish detected activity, designer-declared time, and manager-approved time; preserve provenance, adjustments and audit trail. Approved records feed project financial controls and future historical benchmarks under explicit policy.
8. **Manager view:** Authorized company owners/managers access company workspace dashboards, budgeted vs actual hours and labor costs, risks, approvals and historical estimating.

## 3. Revit Companion — conceptual UI
Ribbon tab: **BIMSpend**. Entry: **Open My Workspace**. Optional dockable panel:
- Company workspace identity, user identity and connection/sync state.
- Detected active Revit document and suggested project association, with uncertainty and correction option.
- Today: detected activity, attributed time, unassigned time and submitted/approved time (clearly labeled).
- Week: own submitted hours, own project allocation, pending timelogs.
- Review and submit timelogs, activity classification and work description.
- Privacy/capture state and offline queue indicator.
- Quick link to full desktop timesheet and authorized project list.

**Role separation:** Designer sees their own work and project assignments by default; salary/loaded labor cost, client fee, company margins and other employees' detailed activity are manager-only, subject to company policy. The Revit panel should be optional, non-blocking and responsive. The desktop agent remains independent of the Revit UI.

## 4. Company workspace / hosting options
Options to evaluate:
- **Company on-prem server:** direct data custody, but burdens IT, backups, upgrades and remote access.
- **Cloud SaaS:** easier onboarding, centralized updates, multi-tenant isolation, ongoing operating and security costs.
- **Hybrid local capture + central backend:** proposed preferred direction — encrypted local durable queue with eventual synchronization to a cloud-hosted company workspace. Not a requirement to deploy a physical server in each customer's office.

Treat this as a **product direction, not a validated deployment architecture**. Before approval, define tenancy isolation, authentication/SSO, device enrollment, least-privilege roles, encryption/key management, offline conflict resolution, idempotent ingestion, retention/deletion, export, backup/recovery, incident response, hosting regions and compliance requirements. Reconcile with Miru and existing B2-A technical findings.

## 5. Tracking approach — preferred concept
**Automatic capture with intelligent confirmation**:
- Capture permitted activity locally after Windows login, transparently and within agreed work policies.
- Suggest project associations using app activity + Revit document context, with confidence and provenance.
- Designer reviews and explains activities rather than blindly accepting time estimates.
- Explicit states: tracking active / paused / offline / signed out; a network outage must not imply tracking has stopped.
- No automatic inference that idle time equals no work; allow meetings, design thinking, calculations, non-Revit work, breaks and legitimate corrections.
- Avoid continuous screenshots, keystroke capture or invasive surveillance by default.
- Define personal-time exclusions, working-hours policy, visibility and employee transparency before release.

**Open decision:** exact opt-in/organization policy, whether capture starts automatically for every organization, and which user controls are mandatory. Do not mark this brainstorm preference as approved.

## 6. Commercial differentiators
### A. Project Pulse — owner dashboard
- Portfolio status, approved and pending time, hours budget consumed, actual loaded labor cost, remaining hours and forecast at completion.
- Drill-down by project, discipline, system, design phase, work package, designer role and change reason.
- Risk indicators combine hours/cost with **independent deliverable progress** and scope; percent budget used alone does not determine project health.
- Example fictional project snapshots: Lee Street 224/300 h, Residential Tower B 135/250 h, Commercial Fitout 168/150 h. Illustrations only.

### B. Variation and rework evidence
- Designer marks architectural changes, clash resolution, scope changes and rework in structured timelogs.
- Link relevant context and approvals without exposing unnecessary personal telemetry.
- Manager can build a reviewable change/variation justification showing extra effort, cost and source evidence. This does not automatically establish contractual entitlement.

### C. Historical estimating flywheel
- Approved, well-classified timelogs form a comparable-project history.
- Estimate hours and costs for future proposals by scope, building type, levels, area, units, systems, phase, complexity and deliverables.
- Expose assumptions, sample sizes, confidence, uncertainty and manager override.
- Keep loaded internal labor cost, billing rates, contracted fees, invoicing and margin separate.
- Historical knowledge remains in the organization with appropriate access and data governance, even as staff roles change.

### D. Designer value proposition
- Less manual timesheet administration.
- Accurate personal project-hour view and easier corrections.
- Clear project context and simple activity descriptions.
- Ability to explain real work beyond time spent in a foreground app.
- Visible and understandable privacy controls.

## 7. Proposed technical component responsibilities
**Windows Desktop Agent:** start at login; local capture coordination, authenticated workspace identity, transparent status, durable encrypted local queue, retries and user review surfaces. Precise split with Windows Adapter remains to be designed.

**ActivityWatch:** source of local activity signals; verify pinned implementations and actual capabilities before adopting.

**Read-only Revit Connector:** loads when Revit opens; reports document/session context through a bounded local interface, never writes to Revit model.

**BIMSpend Windows Adapter:** proposed normalization/attribution boundary between local signals and business records; handles provenance, uncertainty, deduplication and integration, subject to technical design.

**Miru-derived business foundation:** project, client and time/financial business data, extended only where evidence supports it. Existing Miru features must not be assumed to provide encrypted durable offline sync, external ID idempotency, loaded labor cost or read-only Revit integration.

**Company backend:** workspace authorization, central time record ingestion, approvals, financial analytics, historical benchmark dataset and estimating workflows. Multi-tenant cloud architecture remains to be validated.

## 8. Design risks and unresolved decisions
1. Exact Windows autostart behavior, first-run enrollment and update mechanism.
2. Revit add-in installation, compatibility across versions, UI lifecycle and multiple open Revit instances.
3. Device/organization identity, token expiration, revocation, rotation and sign-out.
4. Offline encryption, durable queue, retries, idempotent acknowledgments and conflict resolution.
5. Revit document/project mapping, ambiguity and cross-application work attribution.
6. Company workspace hosting, tenancy isolation, data residency and enterprise private hosting options.
7. User roles, timesheet approvals, financial data segregation and audit trails.
8. Monitoring notice, consent/legal basis, employee privacy, personal-time exclusions, data minimization and retention.
9. Budget vs deliverable-progress signals and forecast-at-completion methodology.
10. Scope variations and contractual attribution.
11. How many validated historical projects are required before displaying an evidence-backed estimate.
12. Product packaging: integrated company platform initially, possible modular subscription later.

## 9. MVP proposal and phased roadmap
**MVP candidate:** Windows desktop agent with clear status; company enrollment; local capture; read-only Revit context; project suggestions; daily timelog review; basic approvals; distinct loaded labor costs/billing rates; simple company project-hours/cost dashboard; foundational activity taxonomy and historical records.

**Next:** Project Pulse risk indicators, variations/rework tagging, improved forecasting, reporting and owner-friendly proposal support.

**Later:** advanced statistically grounded Smart Estimating, more BIM applications, sophisticated multi-company/enterprise deployment and deeper BIM insights.

Do not assume all MVP items are approved or feasible until audits and architecture decisions are reconciled.

## 10. Agent handoff and governance
Use this document alongside the original product-vision file during BIMSpend planning. Its purpose is to preserve **owner brainstorming ideas** for Work, OpenCode and NVIDIA to evaluate. It does not replace their evidence-backed reports.

- Never treat illustrative UI metrics as real project data.
- No code implementation, builds, deployments or changes to main authorized by this document.
- B2-A Gate remains BLOCKED pending independent audit, reconciliation and explicit human approval.
- Preserve the separation of Miru, ActivityWatch, Windows Adapter and read-only Revit Connector.
