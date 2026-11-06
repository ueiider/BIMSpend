# BIMSpend — Task Tracker

Updated: 2026-11-05
Current phase: **PHASE 1 — PLAN COMPLETE / BUILD 01 AUTHORIZED**
Build status: **AUTHORIZED — owner approved 2026-11-05; B2-A audit deferred, not passed**

| ID | Task | Status | Evidence / deliverable |
|---|---|---|---|
| P0-01 | Document open-source candidates and preliminary go/no-go | DONE | docs/technical-feasibility/miru-activitywatch-revit-candidate-assessment-2026-11-05.md |
| P0-02 | Establish master plan, task tracker, AI handoff | DONE | MASTER_PLAN.md, TASK_TRACKER.md, AI_HANDOFF.md |
| P1-01 | Pin Miru + ActivityWatch upstream SHAs, license and third-party inventory | DONE (static) | PLAN_AUDIT_REPORT.md §§2,11; transitive inventory/runtime scans NÃO VALIDADO |
| P1-02 | Miru feature, architecture, API, auth, tenancy and security static audit | DONE (static) | PLAN_AUDIT_REPORT.md §3 |
| P1-03 | ActivityWatch watcher, event, Windows install, API and privacy static audit | DONE (static) | PLAN_AUDIT_REPORT.md §4; Windows runtime NÃO VALIDADO |
| P1-04 | Revit read-only connector feasibility, model identity, multi-instance research | DONE (research) | PLAN_AUDIT_REPORT.md §5; live Revit/ACC NÃO VALIDADO |
| P1-05 | Compare fork vs API/adapter; compatibility and deployment options | DONE | PLAN_AUDIT_REPORT.md §§6–7 |
| P1-06 | Threat/privacy/legal risk register and acceptance criteria | DONE (planning) | PLAN_AUDIT_REPORT.md §8; legal compliance NÃO VALIDADO |
| P1-07 | Produce staged implementation proposal and explicit approval gate | DONE | PLAN_AUDIT_REPORT.md §§9–10 |
| B2-01 | Run isolated reproducible baseline builds/tests | AUTHORIZED — BUILD 01 | Owner approved 2026-11-05; B2-A audit deferred; baseline validation documented in build branch |
| P0-009/P0-010 | Authentication, session, and authorization foundation | DONE | Branch build/bimspend-p0-auth-session at 3e61aaf1f24fb692718e514010f0aee36a6ff69e; 62 tests passed |
| SH-001/SH-002/SH-003 | Security hardening: session validation, company-scoped authorization, password storage | DONE | Branch build/bimspend-p0-security-hardening at 70d4074fc82853a0a80b9d375c691cbc70f0f303; 88 domain tests + 7 GUI tests passed; schema v5; pbkdf2 210k iterations; CI test_report_date_filter_grouping_csv_and_privacy fixed to use authenticated sessions |
| R1-01/R1-02/R1-03 | ActivityWatch source reuse, native Windows capture, AFK/session-lock/heartbeat | DONE | Branch build/bimspend-r1-native-capture at 70d4074fc82853a0a80b9d375c691cbc70f0f303; 113 domain tests + 7 GUI tests passed; schema v6; ActivityWatch-derived code in src/bimspend/capture/activitywatch_derived/ (MPL-2.0); source manifest at docs/open-source/ACTIVITYWATCH_SOURCE_MANIFEST.md |
| R1-04 | Native Revit activity detection and project correlation | DONE | Branch build/bimspend-r1-04-revit-correlation at 8be6e927808c4a76063ea9f7bfc4ab49b0aada98; 126 domain tests + 45 GUI+capture tests passed; schema v7; Revit connector, IPC channel, correlation engine implemented |
| R1-05 | Automatic time entry suggestion engine | DONE | Branch build/bimspend-r1-05-timesheet-suggestions at 68ca19c6041ccaee4200a26ae9f468d87c863bfa; 139 domain tests + 58 GUI+capture tests passed; schema v8; SuggestionEngine, SuggestionConfig, TimeEntrySuggestion implemented with deterministic ID generation, company-scoped authorization, submit/reject workflow |
| B3-01 | Prototype end-to-end event -> project -> manager report | AUTHORIZED — BUILD 01 | Owner approved 2026-11-05; vertical slice implemented in build branch |

## Audit conclusion

Preferred direction: Miru administrative foundation + existing Miru agent API; ActivityWatch local-only collector consumed through an adapter; read-only versioned Revit connector sends signals to the adapter. Do not expose ActivityWatch to the cloud and do not deep-merge the codebases.

## Next single action

**Approval decision:** user reviews `docs/technical-feasibility/PLAN_AUDIT_REPORT.md`. If explicitly approved, execute only **Gate B2-A / B2-01**: isolated reproducible baseline builds, recursive SHA capture, SBOM/license inventory and security scans. No product integration or UI build.

## Working rules

Build remains blocked. Update status only with evidence. Use synthetic/test data. Never infer actual or billable time from foreground activity. Do not modify FBT Revit Academy. Tests not executed are marked **NÃO VALIDADO**.
