# BIMSpend B2-A — Consolidated Architecture (Preliminary)

**Date:** 2026-11-05  
**Status:** Preliminary architecture proposal; pending Claude/NVIDIA audit, OpenCode parallel research, reconciliation, and human approval.  
**Gate:** B2-A **BLOCKED**. This document records architecture planning only. No BIMSpend behavior described here is implemented or validated by execution.

## 1. Evidence boundary

This consolidation is based on the fixed BIMSpend planning baseline at `eb13fc90eb768080f6790bb364b482274860688c`, Work review at `fac85d23e10e4c70ee06d89a87ceb789fe592f4d`, OpenCode execution plan at `73e54ab583d76e6f3b018aaeb5449a1c42c91b9a`, reuse matrix at `b26c6d1a97f270a55d6669916b1369339d1fc98d`, coordination plan at `c90a510a83a892bf3476d8395eca46fd09f01b60`, and gap resolution at `0982411fc0d7ae0bb43508d086d71a088a575c7a`. Their exact report paths and evidentiary limits are in the integration matrix and preliminary approval package.

Pinned upstream references remain unchanged:
- Miru: `10e457e1d0cd2ac782be9d1edbcbd5a1a573486a`
- ActivityWatch umbrella: `9fee4702fea08dbe0149cc6e28f4ef66b49f54ec`

The ActivityWatch umbrella commit and submodule gitlink object existence were reported verified by Work/OpenCode. **Implementation at those submodule gitlinks is not verified here**: the reports state submodules were not initialized/read. README descriptions and component names are not proof of exact endpoints, privacy behavior, ports, payloads, packaging, or watcher lifecycle.

## 2. Proposed component boundaries

| Component | Owns | Responsibilities | Must not own |
|---|---|---|---|
| Miru business foundation | Canonical organization, customer, project, user, timesheet approval, billing workflows | Reuse/configure existing Rails business workflows and reporting where evidence supports fit | Local telemetry collection; Revit API lifecycle; silently interpreting observed activity as approved/billable |
| ActivityWatch | Local activity event capture and local event storage, if exact pinned behavior is verified | Expose minimum necessary local events to a trusted adapter | Customer/project truth, labor costing, invoice approval |
| BIMSpend Windows Adapter | Local integration state and mapping between local sources and business APIs | Lifecycle, filtering/minimization, attribution proposals, durable queue, retries, idempotency, health/error handling | Revit model writes; authoritative billing or approval |
| Read-only Revit Connector | Revit session/document observations | Read permitted document/session metadata through supported Revit API lifecycle | Model edits, transactions that modify model, writes to documents, billing decisions |

The Windows Adapter is the integration boundary between local monitoring/connector inputs and the business foundation. The Adapter and Revit Connector are proposed new BIMSpend components; they are not existing upstream features.

## 3. Miru business foundation

### 3.1 Entities and ownership

Miru is the proposed system of record for business identities and workflows: company/tenant, users, clients/customers, projects, teams, time records, review state, invoices and reports, subject to revalidation against source and the independent audit. The gap report cites source review for these capabilities at the pinned Miru revision. Miru MIT license is a reuse candidate, subject to dependency/license inventory and legal review.

BIMSpend-specific records must be introduced only through separately approved design/build work. Candidate additions include project identity aliases, attribution evidence/confidence, internal loaded labor cost, and synchronization receipt state. These records are not proven upstream functionality.

### 3.2 Time and financial semantics

Keep these concepts distinct:
- **Observed activity:** local signals such as foreground application/window and idle state. Not a timesheet, productivity judgment, or billable quantity.
- **Attributed time:** a proposed association of observed events with a BIMSpend project, accompanied by evidence, confidence, and user correction/confirmation.
- **Submitted time:** a user-created or user-confirmed timesheet record.
- **Approved time:** a reviewer-approved business record.
- **Billed time/revenue:** invoiced commercial amounts.

Keep **internal loaded labor cost** separate from **client billing/charge rate**. The gap report explicitly warns that Miru’s `ProfitabilityBillingRate` represents billing/charge-rate evidence and does not prove loaded employer labor cost. Any margin-like calculation must use explicit semantics; revenue less labor cost is contribution after labor, not automatically net profit. Rates require access controls, effective dates, currency, units, and an approved calculation policy.

### 3.3 Reuse versus custom work

Reuse candidate: Miru organization/project/timesheet/invoice/reporting workflows, AgentKey ingestion, and auth controls identified in upstream source reports. Configure and verify before extending. Custom BIMSpend work: local data capture integration, attribution review, internal labor cost model if approved, project identity reconciliation, encrypted offline persistence, sync/idempotency, and Revit read-only integration. None is authorized for implementation by this plan.

## 4. ActivityWatch monitoring

### 4.1 Collection boundary

Proposed minimum collection: timestamps, application/process identity, an approved and minimized window/context token, idle/active state, source event ID, and adapter-generated session correlation. Avoid keystrokes, screenshots, document content, clipboard, and raw window titles unless separately justified and explicitly approved. The exact ActivityWatch event fields and privacy filter behavior at the pinned gitlinks remain **NOT VERIFIED**.

ActivityWatch is local monitoring only. Treat it as an untrusted input source for business attribution: local events can be missing, duplicated, delayed, manipulated, or ambiguous.

### 4.2 Attribution and user control

The Adapter may propose a project association from Revit foreground/session metadata and configured mappings. Each proposal should include source, time interval, mapping rule, confidence, and a clear user confirmation/correction path. Ambiguous events remain unassigned or marked for review; never silently force them into billable time. AFK/idle events should bound or qualify observation, not establish productivity.

### 4.3 Privacy and retention

Require opt-in/notice and policy review before any workforce collection. Define data categories, purposes, retention/deletion, access, export, and audit. Prefer on-device filtering and short retention for raw events; send only confirmed/minimized time records to the business system. Do not expose ActivityWatch’s local service beyond loopback. Port/bind behavior at the pinned submodule revisions is NOT VERIFIED and must be confirmed before integration.

## 5. BIMSpend Windows Adapter

Proposed responsibilities:
1. Start/stop under an explicit user/system policy; expose visible status and pause controls.
2. Discover and health-check local ActivityWatch and Revit Connector inputs without assuming their ports or protocols.
3. Normalize timestamps/time zones and source identifiers; preserve provenance.
4. Apply allowlists/redaction and project mapping locally.
5. Persist only the minimum approved pending data in encrypted storage.
6. Retry with bounded backoff, explicit acknowledgement, deduplication keys, and safe replay.
7. Report recoverable errors without losing queued records; quarantine malformed or untrusted inputs.
8. Send only approved payloads to Miru/BIMSpend APIs over authenticated TLS; avoid storing credentials in logs.

Offline operation, encryption design, queue guarantees, API contract, idempotency, and adapter lifecycle are all proposed requirements and remain unimplemented/unvalidated. Failure of either local source must not crash Revit or corrupt business records.

## 6. Read-only Revit Connector

Proposed connector reads only session/document identity and allowlisted model metadata required for project attribution. Use Revit-supported API entry points/events and obey API-thread constraints. Autodesk event and document metadata references are listed in the PLAN audit, but compatibility and behavior must be checked for the approved Revit versions.

Session identity should distinguish process, document, and open/closed lifecycle without exporting sensitive file paths or names by default. Multiple Revit processes/documents require explicit foreground/session correlation; do not assume one active instance. No writes, model transactions that change elements, parameter modifications, save operations, or model content extraction are in scope. Connector failures must be isolated and observable; a connector crash or API exception must not block Revit work.

The connector must explicitly support a read-only contract, bounded callback work, no network calls inside Revit callbacks, and a kill/pause mechanism. Target Revit versions, .NET framework/runtime packaging, signing, and installer strategy remain decisions.

## 7. Proposed integration and trust boundaries

```text
ActivityWatch (local events; exact pinned implementation TBD)
       │ minimum local event contract; loopback/local IPC TBD
       ▼
Windows Adapter (filter → normalize → correlate → queue → user review)
       ▲
       │ bounded local IPC; no model writes
Read-only Revit Connector (document/session metadata only)
       │
       └──────────────► Adapter ── authenticated TLS/API ──► Miru business foundation
```

Data ownership:
- ActivityWatch owns captured local events.
- Revit owns its model and document state; connector reads a restricted subset.
- Adapter owns temporary mapping/queue state and provenance.
- Miru owns canonical business entities and submitted/reviewed/billed records.

Trust boundaries:
- Local event content is untrusted and minimized.
- Revit metadata is sensitive business context; export only the fields approved by policy.
- Adapter-to-server traffic is authenticated, tenant-scoped, encrypted in transit, and replay-safe.
- Tenant identity and project authorization must be enforced server-side; client-provided IDs alone are not trusted.

No interface, endpoint, payload, authentication flow, encryption format, or deployment has been implemented or runtime validated.

## 8. Unresolved architecture questions

1. Which ActivityWatch submodule implementation and API at exact gitlinks will be supported?
2. Which Revit versions and deployment model are in scope, and what is the approved .NET boundary?
3. Which local signals and window metadata are acceptable under workplace/privacy policy?
4. Is attribution automatic only as a suggestion, and what user confirmation is mandatory?
5. What is the canonical cross-system project identity and conflict-resolution workflow?
6. What is the definition/source/effective-date policy for loaded internal labor cost?
7. What offline retention, encryption/key management, deletion, and recovery guarantees are required?
8. What server-side idempotency key and tenant binding will be enforced?
9. Which auth mechanism and secret rotation policy applies to desktop agents?
10. What licenses and transitive dependencies are permissible for commercial distribution?

## 9. Status

Architecture separation is **PROPOSED**, supported by existing planning/reuse evidence. It is not a human-approved ADR and is not execution authorization. The independent Claude/NVIDIA audit and OpenCode parallel research are not yet published on their expected remote branches as of this review. Gate B2-A remains **BLOCKED** pending reports, reconciliation, complete prerequisites, and explicit human approval.
