# BIMSpend — Target Architecture

## Decision

BIMSpend is one independent commercial product and one Windows installation experience. It owns capture, idle detection, Revit correlation, review, business records and offline persistence. ActivityWatch and Miru are source-reuse inputs and optional compatibility boundaries, not required installations.

| Component | Responsibility | Exclusion |
|---|---|---|
| Desktop | designer review, manager workflow | no focus→approval inference |
| Native Capture Host | foreground app/window, idle, health/lifecycle | no keystrokes/screenshots/clipboard |
| Read-only Revit Connector | versioned process/session/document events over local IPC | no model writes or callback network |
| Activity Engine | redact, normalize, deduplicate, overlap, attribution suggestions | no auto-approval/billing |
| Business Domain | company, client, project, team, timesheet, rates, budget, reports | no Rails/Miru runtime dependency |
| SQLite | canonical offline store, migration, audit | no parallel aw-server DB |
| Future API | encrypted tenant-scoped sync | never trust client tenant/project claims |
| Optional adapters | AW import/Miru exchange | never required for core |

Flow: immutable observed event → pre-persistence privacy → Revit evidence → idle/overlap processing → attributed suggestion/unassigned → designer confirmation/submission → manager approval/rejection → explicit billing. Observed, attributed, submitted, approved, billable and billed remain distinct.

Every business record is company-scoped. Roles/memberships are per company. Historical user IDs remain through `user_identity_map` until explicitly reconciled; migration must not invent real identities. Labor-cost and billing-rate histories are separate and effective-dated.

Retain SQLite WAL, short transactions and ordered migrations. A background host may survive UI closure only with configured consent and visible running/paused/error state. Durable queue encryption needs Windows DPAPI/key design. Local IPC is authenticated/versioned. Auto-start remains disabled in development.

MPL-derived files live in a clearly identified package with notices/source availability. Miru behavior is normally ported because Rails is incompatible with the desktop runtime.

One signed installer will eventually package Desktop, Capture Host and version-targeted read-only Revit payloads, but not aw-server, Miru, PostgreSQL or Rails. Production identity, cloud topology, IPC, Revit support matrix, encryption, retention and workplace/privacy compliance are **REQUIRES VALIDATION**.
