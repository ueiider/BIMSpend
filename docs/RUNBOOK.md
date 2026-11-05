# BIMSpend Build 01 — Runbook

**Status:** BUILD 01 AUTHORIZED (2026-11-05). Independent B2-A audit deferred, not passed.

This runbook describes how to launch and test the BIMSpend Build 01
vertical slice: a minimal end-to-end prototype for project
time-and-cost intelligence using synthetic data and adapter interfaces.

**No real employee data. No employee monitoring. No production deployment.**

## Prerequisites

- Python 3.9+ (tested on 3.12.10)
- pip

No Ruby, Node, PostgreSQL, Docker or Rust required for this slice. The
pinned Miru (Ruby/Rails/PostgreSQL) and ActivityWatch (Python/Poetry/
Rust) baselines cannot be fully built in this environment (missing Ruby,
PostgreSQL, Docker, pnpm, Poetry); this slice deliberately uses a
standalone Python/SQLite stack with adapter interfaces so those
integrations can be connected later.

## Install

```powershell
# From the repository root
cd src
pip install -e .           # install bimspend package
pip install -e .[dev]      # also install pytest for tests
```

## Run the vertical slice demo

```powershell
cd src
python -m bimspend.runner
```

This:
1. Loads synthetic projects and activity events from `data/synthetic/`.
2. Ingests events idempotently (duplicate `source + external_id` ignored).
3. Correlates observed activity to projects (suggestion, not approved).
4. Simulates designer review (approve / reject / pending).
5. Prints a manager project-hours dashboard showing observed /
   attributed / approved / billed hours per project.

Expected output confirms metric separation:
```
Observed hours != Attributed hours != Approved hours != Billed hours
```

## Run the automated tests

```powershell
cd src
pytest tests/ -v
```

### Test suites

| File | What it verifies |
|------|------------------|
| `tests/test_time_state.py` | Observed/attributed/approved/billed separation; pending entries not auto-invoiced; labour cost vs standard value separation |
| `tests/test_duplicate_events.py` | Idempotent ingestion (duplicate `source + external_id` ignored); original record wins on conflicting duplicates |
| `tests/test_attribution.py` | Window-title -> project correlation confidence; AFK events excluded from attribution |

All tests must pass before considering the slice complete.

## Stop/go criteria (Build 01)

- [ ] All three test suites pass
- [ ] Runner demo executes without error and shows metric separation
- [ ] No real employee data or secrets in the repository
- [ ] No production deployment performed
- [ ] Independent B2-A audit remains deferred (not passed)

## Architecture notes

- `src/bimspend/adapters/base.py` — abstract interfaces (`ProjectAdapter`,
  `ActivityAdapter`, `CorrelationAdapter`, `ReviewAdapter`,
  `DashboardAdapter`). Real ActivityWatch/Miru/Revit integrations implement
  these later.
- `src/bimspend/adapters/activitywatch.py` — synthetic ActivityWatch-like
  adapter (reads `data/synthetic/events.json`).
- `src/bimspend/adapters/miru.py` — synthetic Miru-like project adapter
  (reads `data/synthetic/projects.json`).
- `src/bimspend/correlation.py` — observed-event -> project attribution
  with confidence scoring.
- `src/bimspend/review.py` — designer review workflow
  (pending_review / approved / rejected).
- `src/bimspend/dashboard.py` — manager project-hours aggregation.
- `src/bimspend/db.py` — SQLite persistence with idempotent event
  ingestion (UNIQUE on source + external_id).
- `src/bimspend/models.py` — domain models (Project, ActivityEvent,
  AttributedTime, TimeEntry, TimeEntryState).

## Governance

- `CONTEXT_FOR_AI.md`, `MASTER_PLAN.md`, `TASK_TRACKER.md`,
  `AI_HANDOFF.md` — project context and status
- `docs/decisions/decision-log.md` — decision log (Build 01 approved)
- `docs/technical-feasibility/PLAN_AUDIT_REPORT.md` — feasibility audit
