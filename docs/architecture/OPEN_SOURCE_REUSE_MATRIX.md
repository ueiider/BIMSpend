# BIMSpend — Open-Source Reuse Matrix

**Audit date:** 2026-11-05  
**BIMSpend baseline:** `03c47f37ff37f0126170305a1c4f220b9ea22a68`  
**ActivityWatch bundle:** `9fee4702fea08dbe0149cc6e28f4ef66b49f54ec`  
**Miru:** `10e457e1d0cd2ac782be9d1edbcbd5a1a573486a` (`develop`)

Classifications: **REUSE DIRECTLY**, **ADAPT SOURCE**, **PORT LOGIC**, **BUILD NEW**, **DEFER**, **REQUIRES VALIDATION**.

## Corrected evidence boundary

The ActivityWatch umbrella gitlinks and actual sources were inspected, eliminating the earlier “submodules not initialized” limitation: aw-watcher-window `10638b2...`, aw-watcher-afk `b483926...`, aw-client `fe10696...`, aw-core `28c3acf...`, aw-server `67cfb47...`, aw-qt `bbccb71...`.

## ActivityWatch

| Feature | Exact evidence | Dependencies/tests | Decision | BIMSpend destination |
|---|---|---|---|---|
| Windows app/title | `aw-watcher-window/aw_watcher_window/windows.py`, `main.py` | pywin32 306, wmi; main/startup tests | **ADAPT SOURCE** | `capture/windows.py`; native events, no aw-server |
| Heartbeat loop | `main.py` / `compute_pulsetime` | watcher tests | **ADAPT SOURCE** | `capture/window_watcher.py` |
| Privacy | `privacy_filter.py`; privacy tests | regex | **REUSE DIRECTLY** in isolated MPL file or **PORT LOGIC** after legal choice | pre-DB/log boundary |
| Idle | `aw-watcher-afk/windows.py`, `afk.py`; failure/lock/continuous tests | ctypes | **ADAPT SOURCE** | `capture/idle_windows.py`, `idle_tracker.py` |
| Screen lock | Windows `is_screen_locked()` is TODO/False | — | **BUILD NEW** | WTS/session implementation and tests |
| Heartbeat merge | `aw-core/aw_transform/heartbeats.py`; heartbeat tests | Event model | **ADAPT SOURCE** | `activity/heartbeat.py` |
| Group/overlap | `merge_events_by_keys.py`, union/transform tests | JSON/Event | **PORT LOGIC** | `activity/transforms.py`, preserve provenance |
| Durable queue | `aw-client/client.py`; failqueue/requestqueue tests | requests, persist-queue, SQLite | **PORT LOGIC** | BIMSpend SQLite queue |
| Server/datastore/query | `aw-server/rest.py`, `aw-core/aw_datastore/*`, `aw_query/*` | server/Peewee | **DEFER** | avoid duplicate DB; optional adapter |
| Tray/lifecycle | `aw-qt/manager.py`; manager/autostart tests | Qt/PyInstaller | **PORT LOGIC** | BIMSpend host; avoid Qt dependency |
| Packaging | umbrella `aw.spec`, Inno Setup script | PyInstaller/Inno | **ADAPT SOURCE** patterns | single installer |
| Input watcher | `aw-watcher-input@4e6461d...` | surveillance expansion | **DEFER** | exclude from MVP |

## Miru

Miru is MIT but Rails/PostgreSQL/React; BIMSpend is Python/Tkinter/SQLite. Reuse domain behavior/tests, not a mandatory runtime.

| Feature | Exact source | Decision | BIMSpend action |
|---|---|---|---|
| Company/workspace | `company.rb`, specs | **PORT LOGIC** | company tenancy + legacy reconciliation |
| Users/auth | `user.rb` (Devise JWT/MFA/passkeys) | **BUILD NEW** | native session; remove hardcoded identity |
| Roles | `role.rb`, `policies/*`, role tests | **PORT LOGIC** | tenant-scoped domain authorization |
| Clients/projects/team | related models, policies, system specs | **PORT LOGIC** | preserve and tenant-enable |
| Timesheets | `timesheet_entry.rb`, policy/specs | **PORT LOGIC** | preserve stronger BIMSpend state machine |
| Agent ingestion | agent timesheet controller, `agent.rb`, `agent_key.rb` | **PORT LOGIC** | native device contract with stronger idempotency |
| Audit | `audited` declarations/action trails | **PORT LOGIC** | append-only actor/tenant/before-after audit |
| Invoices | invoice/line-item/payment models/specs | **PORT LOGIC** invoices; **DEFER** payments | explicit billing separate from approval |
| Rates | `profitability_billing_rate.rb` | **PORT LOGIC** | separate effective-dated billing and labor-cost rates |
| Reports | `services/reports/time_entries/*`, CSV/specs | **PORT LOGIC** | native Python filters/grouping/export |
| Budgets | no first-class app budget found at pin | **BUILD NEW** | budget versions/variance |
| UI | React app | **DEFER** | no redesign now |

## Preserve BIMSpend

Preserve the observed/attributed/submitted/approved/billed split, SQLite WAL/transactions/migrations v1–v3, source and attribution uniqueness, and project/team/budget/report/estimating modules. Existing ActivityWatch/Miru-shaped adapters remain optional compatibility seams. Hardcoded `designer_01` remains an authentication blocker.

No upstream code was run or installed. Runtime, SBOM, Windows packaging, vulnerabilities and legal approval remain **REQUIRES VALIDATION**.
