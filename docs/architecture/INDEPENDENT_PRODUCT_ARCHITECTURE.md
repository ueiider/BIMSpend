# Independent product architecture

Owner decision, 6 November 2026. BIMSpend owns Windows capture, Revit event collection, SQLite, project attribution, timesheets, approvals, reporting, finance and access control. Future web/mobile clients consume a BIMSpend-owned management service after that boundary is designed. Third-party import/export is optional interoperability.

| Question | main at 65e344b | R1-08 at 02257ab |
|---|---|---|
| ActivityWatch installation required? | No. Desktop seed/import reads fixtures. | No for preview. Derived Windows capture needs Windows APIs and Python bindings if enabled. |
| Miru installation required? | No. | No. |
| Actual ActivityWatch source? | None identified in shipped Python. | Yes. The Windows capture module has substantial source overlap at the pinned upstream revision. Heartbeat and privacy ancestry is documented and requires final notice reconciliation. |
| Actual Miru source? | None identified. | None identified. Native Python domain and mock export are separate from Miru Rails. |
| Adapters | Fixture readers and mock export. Opt-in loopback client exists but desktop import uses fixture parsing. | Same compatibility surface. Recovered FCC AW HTTP and Miru HTTP are separate, external-dependent prototypes. |
| Standalone commercial product? | Standalone synthetic preview. Operational capture, identity and deployment gates remain. | Better aligned source candidate. Windows startup smoke is verified. Native capture to durable timesheet and versioned Revit host delivery remain open. |

## Blocking boundaries

1. In R1-08, `capture/controller.py` creates its worker around the derived watcher but persists point events with zero duration and AFK false. `capture/heartbeat.py`, `afk_detector.py` and `session_lock.py` have no controller call sites. `app/shell.py` does not own a capture lifecycle. A background worker writes through `Database.conn`, created with SQLite's default same-thread check. Design a worker-owned connection or serialized writer, interval closure and stop/join semantics. Scope idempotency to organization/member as well as source. Keep raw payload out of storage and diagnostics, and revalidate scope across pause/resume/logout.
2. R1-08's `pyproject.toml` has no Windows capture dependencies. The package workflow installs PyInstaller, PyAutoGUI and Pillow for a synthetic build. Prove the optional Windows capability can ship using a reviewed dependency lock and corresponding-source notices.
3. `capture/revit_connector.py` observes API-style callbacks and offers a synthetic observer. `capture/revit_ipc.py` supplies IPC scaffolding. The candidate tree has no C# host project. FCC's recovered host lives on another branch, with a separate envelope and pipe topology. Define one read-only event contract, stable document identity and session boundaries, a local authenticated transport and replay, and verify Autodesk version compatibility in an isolated environment.
4. Reconcile `review.py` with `capture/suggestion_domain.py`, and `dashboard.py` with `financial.py`. Approvals must produce one authoritative reviewed record that both finance and reports read. Preserve existing decisions and billing state across migration, replay and corrections.
5. Real deployments need a data lifecycle, company isolation, authenticated management roles, consent, retention, backup/restore, redaction, distribution review and a disable switch. Keep fixtures and production collection paths separated. Licensing clearance and privacy authorization are distinct release gates.

See [source reuse](ACTIVITYWATCH_MIRU_SOURCE_REUSE_MATRIX.md) and [verification](../qa/TEST_AND_BUILD_VERIFICATION.md).
