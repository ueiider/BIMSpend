# BIMSpend — Continuation Context for Any AI Agent

You are continuing an exploratory product brainstorm. Do not assume implementation is authorized.

## 1. What BIMSpend is

BIMSpend is a working name for a potential commercial, subscription-based software platform for engineering, architecture, and BIM companies. The initial concept involves:

1. Automatic time tracking while designers work in supported applications.
2. Integration with Autodesk products, potentially including Revit, AutoCAD, Navisworks, Civil 3D, and others.
3. A Windows desktop application operating in the background.
4. Optional application-specific plugins or connectors.
5. Centralized project and employee information.
6. A management dashboard accessible from another computer.
7. Project cost monitoring.
8. Comparison of actual working hours against invoiced hours.
9. Historical project analytics.
10. Potential assistance with estimating the cost and selling price of future projects.
11. Subscription-based commercial licensing.

**IMPORTANT: These are hypotheses, not finalized product requirements.** The precise product scope, integration methods, supported applications, pricing model, and technical architecture are still undecided. Do not prematurely convert brainstorming ideas into implementation commitments. The user wants minimal or zero daily interaction from designers after installation.

## 2. Why the concept originated

The conversation began with a set of monetizable "Fire Design" ideas (AI auditor, hydraulic calculation assistant, BIM clash resolution, quantity/variation tracker, AI sprinkler layout, standards assistant, drawing revision detector, Fire BIM Academy, Revit productivity toolkit, site inspection AI, RFI copilot, estimating AI) and narrowed to time and cost tracking. The user proposed a Revit-related product to count hours and costs; potential differentiators include comparing actual effort, charged effort, and internal cost to improve estimating and quoting.

## 3. Problems being investigated (hypotheses)

1. Designers lose time manually reporting hours; managers lack timely project visibility.
2. Work happens in multiple models/apps, not just Revit.
3. Managers cannot easily distinguish actual effort from billed effort and discretionary discounts.
4. Quoting depends on subjective experience and insufficient historic benchmarks.

## 4. What has already been discussed

- A single Windows installer would provision a desktop agent plus compatible Autodesk integrations; launch automatically with Windows/Revit; no daily login or timer.
- Manager access likely web/cloud, but architecture is undecided.
- Multiple Revit versions require version-specific integration builds. Multiple simultaneously open models require non-duplicated accounting.
- Robust model-to-commercial-project mapping, offline persistence, employee transparency, and security are needed.
- Two spreadsheets were shared in chat: `Item price list.xlsx` and `Maria Angelica Sales by Product_Service Detail.xlsx`. They contain company-specific rates and invoices. **Do NOT commit raw spreadsheets or identifiable employee/customer data.**
- The user confirmed `Quantity` in the sales report is hours **billed to clients**, not a reliable measure of actual hours worked. Sometimes actual effort exceeds billed hours, and the company discounts hours subjectively. This gap is central.
- Revit Journals may contain session timing and events but are diagnostics, not reliable timesheets.
- The user's PC has 101 Revit Journal text files across Revit 2021–2026. These may allow partial reconstruction of sessions, not proven hours. No parsing result yet.
- `bimspend.com` was shown offered for sale at A$17.22 first year (time-dependent). ASIC/IP Australia/domain registration clearance NOT confirmed.
- BIMS Pulse and BIMetrics already used commercially; rejected. Working name: BIMSpend (not legally cleared).
- No product built. No validated API design. No agreed MVP. No verified financial benchmarks.

## 5. Current hypotheses

- Tracking could feed cost realization and future estimates (hypothesis, not validated).
- Actual-hours records do not currently exist in a reliable form; this is an open research question.
- Generic automatic time tracking is not novel (competitors exist); differentiation hypothesis is cost intelligence + actual-vs-billed + historical scope-based estimating.
- Per-seat subscriptions (previously discussed A$15/A$29 per user/month were illustrative guesses, not validated prices).

## 6. Research findings

### Competitors (research leads, not comprehensive audit)

- Time Tracker Pro (Autodesk marketplace): automatic Revit tracking / idle detection.
- Project Tracker (Autodesk marketplace): time by project/file/view/task.
- INFINITY Suite Time Summary / Advanced Analytics: Revit time summaries and per-file analytics.
- ManicTime: automatic desktop time tracking.

Generic time tracking is not original. Cross-app tracking and manager reporting already exist. The proposed combination of observed CAD/BIM activity, actual-vs-billed hours, cost realization, and historical scope-based estimating is a differentiation hypothesis — NOT proof of novelty or patentability. No originality/patent claim established.

### Historical data

Local Revit Journals (diagnostic traces); model file metadata; worksharing history where accessible; Autodesk Construction Cloud/BIM 360 model versions and sync events; previously installed third-party trackers. Cloud sync history ≠ active work time. Never infer exact hours from only open/close timestamps. See `docs/research/historical-data-research.md` and `docs/technical-feasibility/technical-research.md`.

### Key financial concepts (synthetic illustrations only)

- `actual_hours`: measured or verified work effort (may require correction for idle/other apps).
- `billed_hours`: invoiced quantity, possibly discounted.
- `standard_charge_rate`: published hourly price to client.
- `internal_loaded_cost_rate`: true employer cost per hour including relevant overhead, distinct from charge-out rate.
- `revenue`: actual invoiced value (excluding GST if comparing like-for-like).
- `realization = billed_hours / actual_hours` (where comparable).
- `effective_rate = revenue / actual_hours`.
- `labor_cost = actual_hours * loaded_cost_rate`.
- `contribution_after_labor = revenue - labor_cost` (not net profit).
- `quote_price = estimated_cost / (1 - target_gross_margin)` only when the cost base includes all intended cost categories.

Synthetic example: actual 12 h, billed 8 h, client rate A$110/h → invoice A$880, standard value A$1,320, unbilled reference A$440, realization 66.7%, effective revenue per actual hour A$73.33. **Not actual employee data.**

## 7. Open questions

1. How does the company currently know actual hours spent when it invoices fewer hours? Is there a manual timesheet, a manager estimate, or other data source?
2. What minimal Autodesk signals can reliably attribute time to a commercial project?
3. What manager output would materially improve quoting or billing decisions?
4. What is possible across Revit/AutoCAD/Navisworks/Civil 3D with consent and realistic maintenance cost?
5. Which functions do direct competitors already offer, and what gap is validated by prospective buyers?
6. How are model files mapped to commercial projects across multiple disciplines and renames?
7. How is time allocated when Revit is open alongside a meeting/PDF/email?
8. What constitutes a completed task and how is complexity captured?
9. What does a manager need to see live vs historical?
10. Who pays and how is licensing activated without employee daily login?
11. What is permitted under employment law, customer contracts, and Autodesk terms?

## 8. Rejected assumptions

- Invoice quantity = actual working hours. (Rejected: quantity = hours billed, sometimes discounted.)
- Basic automatic time tracking is novel. (Rejected: competitors already offer it.)
- BIMSpend is the first product of its kind. (Rejected: no such claim.)
- bimspend.com ownership/trademark availability confirmed. (Rejected: only a sales listing was observed; no clearance performed.)
- Any feature, architecture, or price is approved. (Rejected: nothing is approved.)

## 9. Current project status

**DISCOVERY — NO MVP APPROVED.** Updated 2026-11-05. This repository is the persistent source of truth, accessible from desktop and mobile via GitHub (private repo `ueiider/BIMSpend`).

User-stated preferences (not technical approvals): commercial subscription desired; single install deploys PC app and integrations; designers no routine login/manual project selection/timers; auto-start when supported Autodesk applications run; manager access from another computer; not branded Revit-only; GitHub as source of truth; preserve brainstorm rather than prematurely finalize.

## 10. Next recommended brainstorming topic

**How is actual time measured today when billed hours are discounted? What source is reliable?** (Decision log item 1.) Resolve this before investing in tracking architecture or estimating features.

## 11. Update protocol

After each discussion, update relevant docs, append a dated note to `docs/decisions/decision-log.md` (format: `YYYY-MM-DD | Idea / Hypothesis / Tested / Approved | Topic | Evidence | Decision / Next action`), and optionally open a GitHub Issue. Keep changes in GitHub private until cleared for publication. Never label a decision APPROVED unless the user explicitly approved it.

## 12. New research — reuse of existing GitHub code (2026-11-05)

The user liked the Miru dashboard and asked whether existing open-source software could be copied and adapted for BIMSpend. **Miru is the leading candidate for administrative functionality**, **ActivityWatch for Windows active-window/idle observation**, and a **custom read-only Revit connector** for document/project signals. A responsive manager web/mobile dashboard is a desired hypothesis, possibly a PWA. These are **candidates, not selected or implemented architecture**.

Preliminary legal/technical conclusion: **YES to evaluating and prototyping** Miru (MIT) and ActivityWatch (MPL-2.0), observing their license terms; **NO production readiness or combined-stack compatibility has been established**. GPL/AGPL competitors are useful references but require separate licensing review if incorporated. No code checkout, runtime integration, dependency/security audit, or live Revit test has occurred in this chat. Do not claim otherwise.

Read the complete assessment, risks, open questions, and mandatory validation checklist in `docs/technical-feasibility/miru-activitywatch-revit-candidate-assessment-2026-11-05.md`. Keep billed hours distinct from observed/actual hours and internal loaded costs. No product MVP approved. The user requested that these findings be committed to GitHub.
