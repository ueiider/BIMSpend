# BIMSpend development preview checkpoint

Source integration: OpenCode `e955eb0bb23bd447be02318422c7b925a105710b` merged with Work `e73e92dc0b54203bfe4f7f80f95364159e20d873` in `a1fa219f21ab243bf9c1a994b0778dec239f9f93`. Claude contracts `68e4a791ea72e527aa888c33773eb07eb8b8a485` were inspected but not merged because the published branch contains documentation and schemas, not executable adapter code.

## Executed on Windows in isolated workspace

- Baseline: 7/7 existing tests passed; synthetic runner completed; Python compileall passed; Tkinter 8.6 imported.
- After integration: 12/12 tests passed with `PYTHONPATH=src; python -m pytest tests -q --basetemp=.pytest_tmp`. The new regression tests created and updated all five Tkinter screens, exercised create/edit/archive project, manual ambiguous attribution, designer submission, manager approval, and verified persistent restart. This proves programmatic widget creation, not visual usability or manual click paths.
- Initial `pytest` without `--basetemp` failed because this sandbox denied creation of its default temporary directory. The test script sets a workspace local temporary directory; it passed with 12/12 tests.
- No real capture or external transmission was invoked. This is supported by inspected fixture adapters and test paths, not a network traffic audit.
- No standalone EXE built. Windows scripts use the existing Python standard library application. CI workflow results remain **NOT RUN** until GitHub Actions completes.

## Implemented here

- Preserve separate explicit project `is_archived` across SQLite migration, JSON model and GUI. Previous prefix rename and `is_billable = False` archive behavior corrupted commercial identity.
- Generate new project IDs with UUIDs instead of list length, preventing reused IDs after project removal or fixture replacement.
- Hash non-redacted window titles before SQLite storage; discard untrusted raw payloads. Synthetic title correlation now runs in memory before the persistence privacy boundary. Existing historical databases may already hold raw titles; no automatic migration or destructive scrub is attempted.
- Seed attributed suggestions and pending timesheet entries from synthetic events; skip duplicate source events. Ambiguous events stay unassigned. Manual assignment to an authorized active project creates a pending entry.
- Display observed hours from non-AFK events on the overview instead of using attributed hours as proxy.
- Expose rejected entries in the designer review list; manager actions in the demo label `manager_demo` (no real authentication/authorization). Remove duplicate SQLite connection in app startup.

## Windows preview

From a fresh checkout on Windows with Python 3.9+:

```powershell
.\scripts\Install-BIMSpend-Dev.ps1
.\scripts\Test-BIMSpend.ps1 -Python .\.venv\Scripts\python.exe
.\scripts\Launch-BIMSpend.ps1 -Python .\.venv\Scripts\python.exe
```

The launcher creates `.preview/bimspend.db` with synthetic fixtures on first run. Do not use it with real employee data or regard it as a production security boundary. Run the five screens and actions manually before sharing a desktop preview.

## Remaining release blockers

1. No authenticated user and manager roles; manager controls are a synthetic persona, so no real multi-user approval.
2. No actual ActivityWatch/Revit/Windows Adapter/Miru synchronization; Claude's schemas require UUID identity and assigned projects, incompatible with fixture IDs and unassigned activity.
3. No bill button, timesheet editing, budget workflow, report export or historical estimating UI; domain billing method exists.
4. No standalone Windows EXE, installer, privacy consent, retention policy or migration scrub for earlier databases.
5. Existing v1 SQLite databases with NOT NULL `attributed_time.project_id` cannot accept unassigned events; documented migration is a no-op. Test migration before upgrading existing data.
6. UI interaction screenshots, accessibility, sizing and actual multi-user security are not validated. CI results pending.

Preview is for synthetic development only, not release or deployment.
