# BIMSpend — Feature Gap Analysis

Baseline: `build/bimspend-p0-foundation@03c47f37ff37f0126170305a1c4f220b9ea22a68`.

| Area | Current | Gap | Decision |
|---|---|---|---|
| Windows capture | synthetic fixtures/adapters | no native collector | **ADAPT SOURCE** from AW watcher |
| Idle | AFK field processing | no native detector; AW Windows lock TODO | **ADAPT SOURCE** + **BUILD NEW** lock |
| Privacy | title hash on persistence | formal filtering must precede persistence/logging | **ADAPT SOURCE** |
| Event identity | unique source/external_id | device/batch/collision policy | **BUILD NEW** |
| Overlap | correlation/duplicate tests | deterministic cross-source precedence | **PORT LOGIC** |
| Lifecycle | desktop startup | background host/pause/health/recovery | **PORT LOGIC** |
| Storage | WAL/transactions/migrations v3 | encryption, backup, production retention | preserve + **BUILD NEW** |
| Tenancy | none | all business rows need company scope | **PORT LOGIC** from Miru |
| Authentication | hardcoded designer | no real session/auth | **BUILD NEW** (P0-009/010) |
| Authorization | synthetic role tests | tenant-scoped policies | **PORT LOGIC** |
| Clients/projects/team | basic | client/tenant/membership constraints | preserve + **PORT LOGIC** |
| Model mapping | title/manual mapping | stable Revit identity/history | **BUILD NEW** |
| Timesheets | strong distinct state machine | locks/resubmission/tenant audit | preserve + **PORT LOGIC** |
| Billing | explicit billed state/minutes | no invoice aggregate | **DEFER** invoice; preserve separation |
| Rates | snapshots | no effective-dated split histories | **BUILD NEW**, Miru-informed |
| Budgets | project budget value | no allocations/versions/change audit | **BUILD NEW** |
| Reports | native reports/CSV tests | tenant/activity filters | preserve + **PORT LOGIC** |
| Estimating | synthetic estimator | governance/comparable confidence | preserve |
| Revit | synthetic parsing | real read-only connector/IPC absent | **BUILD NEW** |
| Installer | preview packaging | single signed capture/Revit installer | **ADAPT SOURCE** patterns |
| AW/Miru compatibility | adapter seams | optional only | **DEFER** |

Avoid duplicate implementations: do not adopt aw-server storage; do not import Rails models; do not weaken BIMSpend's state machine. Selectively adapt low-level ActivityWatch capture/idle/heartbeat modules and reproduce Miru tenant/policy/audit/rate/report tests in Python.

Migration risks: company backfill must remain unresolved rather than invent ownership; historical user IDs stay mapped separately; rates must be snapshotted before normalization; native event identity must not overwrite reviewed entries; MPL provenance must remain file-level; background capture cannot ship enabled without consent/pause/retention/uninstall.

Static source inspection is verified. Builds, runtime capture, installer, vulnerabilities, negative tenant tests and legal compliance are **REQUIRES VALIDATION**.
