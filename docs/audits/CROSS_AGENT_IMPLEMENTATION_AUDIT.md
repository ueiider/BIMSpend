# Cross-agent implementation audit

## Contributions

- OpenCode Build 01 `e955eb0` is an executable ancestor of main. Work `47c8d35` integrated the synthetic desktop and was merged in PR #1. Main `55dd86e`, `48863e7`, `65e344b` added parser, persistence and GUI integration. Work UI design `9e32d6e` and coordination `c1ee016` are design/history.
- P0 branches form the migration/auth/security sequence starting at main. R1 capture, Revit, suggestion, approval and finance branches extend it. R1-08 is their descendant with desktop modernization and packaging. Architecture-alignment branch is R1-08 plus documentation, with no runtime delta. The separate 20-screen Playwright prototype is design evidence. The Kilo audit is documentation attached to R1-06 history. The B2-A, brainstorm and source-reuse agent branches preserve research and coordination evidence.
- FCC `31a7713` is a separate line. Its recovered code is under docs and excluded from normal startup/packaging. Work Claude evidence branch preserves research provenance rather than replacing FCC source.

## Runtime feature verification

Paths below are relative to `src/bimspend` unless specified. Test results and Windows scope are in [QA](../qa/TEST_AND_BUILD_VERIFICATION.md).

| Feature | Main implementation and evidence | R1-08 delta and next gate |
|---|---|---|
| Startup, navigation, settings | `app/main.py`, `app/shell.py`, overview and integrations navigation. Windows preview smoke and GUI CI. Privacy status is synthetic. | `app/design.py` and shell styling plus local auth wiring. Validate all navigation and permission edges on Windows. Capture settings/lifecycle are incomplete. |
| Projects and team | `app/screens/{projects,project_detail,team}.py`, `db.py`. Project edits/archive, member and assignments; team and work integration tests. | Company scope in P0 and local auth. Test upgrades and separation of company datasets. |
| Activity timeline and integrations | `activity_timeline.py`, `integrations.py`, `app/screens/integrations.py`. Manual attribution and fixture import. `test_integrations_v2.py` covers UTC, AFK/overlap and replay; GUI test in CI. | Derived capture, AFK and WTS modules exist. No desktop lifecycle, durable intervals or proved native executable capture. |
| Attribution/Revit | `correlation.py`, `integrations.py` with fixture document data, project rules, and overlap-safe slices. | `capture/{revit_connector,revit_ipc,project_correlation}.py` implement callbacks, simulated producer and mapping/confidence logic. Missing supported packaged Revit host and end-to-end transport. |
| Timesheets/approval/billing | `review.py`, `db.py`, `app/screens/timesheet_review.py`. Edited and reviewed time persists with audit history, approved/billable and explicit billing. `test_time_state.py`, `test_identity_permissions.py`. | Adds separate suggestion store/service, designer and manager screens. Unify canonical transitions and reconcile whether split/merge/approval feeds the same approved ledger. Four related test modules blocked by Linux platform import. |
| Financial dashboard and budgets | `dashboard.py`, `app/screens/project_detail.py`. Approved labor cost and variance from synthetic budget and project rates. `test_project_financials.py`. | `financial.py` and dedicated screens add Decimal costing, rate history, budget revisions and projections. Reduced Linux suite covered finance. Prove consistent shared ledger, currency and billability across new and legacy screens. |
| Reports/estimates | `reporting.py`, `estimating.py` and screens. Date ranges, grouped CSV, approved comparable estimates tested. | Adds financial reports; confirm tenant scope, safe CSV, profitability definition and sparse historical evidence. |
| Database/security | `db.py` schema creation/migration, local SQLite, role checks in `identity.py`, duplicate protection and audit log. Main actors are synthetic. | P0 adds WAL, transaction handling, migrations through v10 in final R1, auth/session and company scope. `test_p0_sqlite_reliability.py`, `test_p0_auth.py`. Validate staged backup, mixed legacy/auth data, restart and concurrent capture. |
| Miru | Fixture and mock behavior under `adapters/miru.py` and `integrations.py`; no required Miru service. | Native finance and review changes are Python implementation. FCC HTTP client could only serve a separately authorized interoperability workflow. |

## FCC file dispositions

Paths relative to `docs/agents/claude/recovered-fcc/`. A disposition refers to candidacy after verification.

| File | Classification and disposition |
|---|---|
| `aw_adapter/main.py` | Functional HTTP polling/transform/queue prototype, dependent on AW buckets. Superseded for native capture. Adapt privacy and dedup test cases, not the HTTP worker. |
| `aw_adapter/config.yaml`, `requirements.txt` | Example config/dependencies for separate AW worker. Keep out of product runtime. |
| `aw_adapter/test_aw_adapter.py`, `test_schema_validation.py` | Reusable synthetic test ideas for transformation, redaction, stable identifiers, queue and schema. Adapt to canonical contract. |
| `windows_adapter/main.py` | Separate pipe/queue consumers and Miru orchestration. Reference only. Uses two ingestion paths outside product startup. |
| `windows_adapter/correlation_engine.py` | Functional interval prototype. Overlaps main normalization and R1 correlation/suggestion. Port only missing test vectors and invariants after overlap reconciliation. |
| `windows_adapter/metrics_enforcer.py` | Executable validation candidate. Adapt explicit metric definitions if aligned to BIMSpend's domains. |
| `windows_adapter/miru_client.py` | Actual external HTTP client, separate from mock. Reject as mandatory product path. Optional export prototype only. |
| `windows_adapter/config.yaml`, `requirements.txt` | Example endpoint/configuration and dependency list. Keep isolated. |
| `revit_connector/RevitConnector/Addin.cs` | Revit IExternalApplication prototype, subscribes to host events. Candidate for adaptation to supported API versions, lifetime, privacy and contract. |
| `revit_connector/RevitConnector/Events/EventEmitter.cs` | Read-only event serialization candidate. Align session/document IDs, event times, envelope and allowlisted fields. |
| `revit_connector/RevitConnector/Identity/ModelIdentityResolver.cs` | Identity mapping candidate. Adapt and test local, central, cloud, rename and unsaved scenarios. |
| `revit_connector/RevitConnector/Transport/ITransport.cs` | Interface only, potential seam for isolated fixtures. |
| `revit_connector/RevitConnector/Transport/NamedPipeTransport.cs` | Server prototype. Reconcile server/client roles, framing, ACL, reconnect, bounded queue and replay with R1 Python IPC. No end-to-end validation. |
| `revit_connector/RevitConnector/RevitConnector.addin`, `RevitConnector.csproj` | Host metadata and build definition. RevitAPI/RevitAPIUI inputs required. No compiled or installed artifact verified. |
| `revit_connector/admin_mappings.json` | Example map. Reuse as synthetic fixture only. |
| `schemas/{envelope,adapter_correlated_activity,adapter_ingestion_draft,afk_state_changed,revit_application_idling,revit_document_closed,revit_document_opened,revit_view_activated,window_focus_changed}.schema.json` | Nine contracts, duplicated under sibling `contracts/schemas/`. Choose one authoritative version; map units/IDs/names to R1 IPC and existing main parsers before promoting. |
| `fixtures/invalid/{invalid_event_type,invalid_timestamp,invalid_uuid,missing_event_id,missing_required_payload,unknown_field}.json` | Negative examples, retain as validation inputs. |
| `fixtures/valid/{adapter_correlated_activity,adapter_ingestion_draft,afk_state_changed,revit_application_idling,revit_document_closed,revit_document_opened,revit_view_activated,window_focus_changed}.json` | Positive examples, adapt to canonical schema with provenance. |
| `tests/test_schemas.py` | Synthetic standalone schema harness. Current execution 60/60 reported. Adapt to CI, enforce coverage independently of reported assertion count. |
| `docs/OPENCODE_HANDOFF.md` | Historical handoff. Compare claims with current tests and do not use as runtime instruction. |

FCC full runtime and C# compatibility remain unverified. Direct promotion of FCC files would duplicate contracts, introduce external runtime dependencies and bypass the candidate application's auth/SQLite semantics.
