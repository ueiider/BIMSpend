# Candidate codebase assessment — Miru + ActivityWatch + Revit integration

Date: 2026-11-05
Status: **DISCOVERY / CONDITIONAL PROTOTYPE GO — NOT PRODUCTION APPROVAL**

## Executive decision

- **Miru (saeloun/miru-web): YES, candidate for a commercial administrative foundation**, subject to confirming the exact LICENSE and third-party dependencies at the revision actually adopted. Public repository describes MIT licensing, Rails/React application, projects, clients, teams, time entries, invoices and reporting. This is NOT an endorsement of production security, maintainability or a fit to our data model.
- **ActivityWatch (ActivityWatch/activitywatch): YES, candidate for a Windows tracking foundation**, subject to MPL-2.0 obligations, notices, bundled components and security/privacy review. Active-window and idle events are useful signals; they do **not** prove productive hours or correctly identify a BIM project on their own.
- **Custom Revit add-in: YES, technically plausible**, using documented Revit API events to identify documents and sessions. Exact per-project time attribution is not established; event signals alone do not measure human work.
- **Combined stack: NOT VERIFIED.** No repository checkout/build, installation, integration, dependency vulnerability scan, penetration test or live Revit proof of concept was executed in this chat. No production or commercial release approval.

## Candidate repositories

| Candidate | URL | Proposed role | License understanding | Limitations |
|---|---|---|---|---|
| Miru web | https://github.com/saeloun/miru-web | Multi-user admin, clients, projects, time records, invoices, reports, dashboard | MIT (verify at pinned commit) | Manual time-entry concepts may require significant adaptation; validate API, tenancy, RBAC, audit trails, upgrades |
| ActivityWatch | https://github.com/ActivityWatch/activitywatch | Windows activity/idle collection and local event API | MPL-2.0 (verify components and pinned revision) | Window focus ≠ productive effort; local-first design; not a complete managed cloud fleet solution |
| Journalysis | https://github.com/andydandy74/Journalysis | Optional historical Revit Journal research | MIT (verify at pinned revision) | Diagnostics do not reliably reconstruct actual work hours |
| solidtime | https://github.com/solidtime-io/solidtime | Functional benchmark, possible alternative | AGPL-3.0 (verify) | Network copyleft obligations need specialist review |
| Kimai | https://github.com/kimai/kimai | Functional benchmark, possible alternative | AGPL-3.0 (verify) | Same concern |

**Licensing caveat:** Commercial use is permitted by MIT and MPL-2.0 subject to their terms. MIT requires preservation of copyright/license notices; MPL-2.0 can require making source of covered modified files available when distributed. Review third-party dependencies/assets and deployment specifics; public visibility alone is not a license. Do not treat this note as legal advice.

## Proposed architecture — unapproved hypothesis

Windows activity/idle collector + read-only Revit add-in -> BIMSpend Windows agent (event correlation, idle rules, offline queue, consent/transparency) -> authenticated backend and tenant-separated storage -> Miru-derived management UI and responsive web/mobile dashboard.

Avoid shipping an unmodified ActivityWatch server endpoint openly to the internet. Establish an authenticated, encrypted, least-privilege ingestion boundary and clear retention controls.

## Functional distinctions (critical)

- **Session time:** Revit open / model open duration.
- **Observed active time:** window/input-based activity estimate.
- **Attributed project work time:** corroborated time mapped to a commercial project, with exceptions and uncertainty.
- **Billed hours:** invoice quantity; may be discounted and must never be equated with actual hours.
- **Loaded internal hourly cost:** employer cost, not client charge-out rate.
- **Revenue / contribution:** use consistent tax basis; contribution after labour is not net profit.

Illustrative only: 12 actual hours, 8 billed at A$110/h => A$880 revenue; 66.7% realization; A$73.33 effective revenue per actual hour; A$440 reference unbilled value.

## Mandatory technical due diligence before choosing the base

1. Pin exact upstream commits and inventory LICENSE, NOTICE, vendored code, fonts, images, packages and transitive dependency licenses.
2. Clone and reproduce clean builds in isolated environments; document Windows support, versions, prerequisites and deployment.
3. Audit Miru: database schema, tenant isolation, authentication, RBAC, API write/read permissions, CSRF/XSS/SSRF, secrets, encryption, backup/restore, audit log, upgrade/migration safety, rate limiting, dependency advisories.
4. Audit ActivityWatch: actual event payloads, idle/window accuracy, multi-monitor/multi-app behavior, offline retention, local API exposure, memory/CPU usage, code signing, autostart, updates, security, data minimization.
5. Prototype Revit read-only connector: DocumentOpened/Closing, active document changes, save/sync, multiple models/windows/versions, renamed files, central/local/ACC identities, crashes and reboots; never assume events measure productivity.
6. Verify a minimal end-to-end demo: a consenting test user opens Revit, project mapping resolves, agent detects idle, events synchronize securely, manager sees attributable time, and billed hours remain separate.
7. Test multi-tenant data segregation, permissions (owner/PM/designer), responsive mobile web/PWA feasibility, consent notices, retention/deletion/export and applicable Australian workplace surveillance/privacy requirements.
8. Assess upstream health: recent commits, maintainers, issue backlog, security policy, release frequency, upgrade divergence, and realistic fork maintenance cost.
9. Decide **fork vs API integration vs clean-room implementation** only after evidence. Do not estimate percent code reusable without a component-by-component audit.
10. Keep confidential company spreadsheets, employee/customer identities and credentials out of GitHub. Use synthetic fixtures.

## Current go/no-go

- **GO:** repository-level technical investigation and isolated prototype, with licenses respected.
- **NO-GO:** claiming the three components already work together; deploying to employees/clients; advertising secure production readiness; assuming time-in-window equals billable productivity.
- **NO IMPLEMENTATION AUTHORIZATION:** this note records research and a recommended test plan; the user has not approved an MVP or architecture.

## Source pointers

- https://github.com/saeloun/miru-web
- https://github.com/ActivityWatch/activitywatch
- https://docs.activitywatch.net/
- https://www.revitapidocs.com/ (secondary Revit API reference; validate against Autodesk's official SDK)
- https://www.autodesk.com/developer-network/platform-technologies/revit

## Open questions

- Does Miru's current API support secure automated time ingestion at intended scale without a large rewrite?
- Is ActivityWatch adaptation preferable to a custom collector after licensing and performance review?
- How do we handle time spent on BIM work outside Revit (PDF, email, coordination meetings)?
- How will commercial project identities map to multiple Revit models and apps?
- How will user consent, transparency and manager permissions be designed?
- Is a responsive web app sufficient or is a PWA required?

Next action: run a documented, reproducible audit and proof of concept **without modifying the FBT Revit Academy project or shipping production code**.
