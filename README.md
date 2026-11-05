# BIMSpend — Build 01 Vertical Slice

**Status:** BUILD 01 AUTHORIZED (2026-11-05). Independent B2-A audit deferred, not passed.

This is the first working vertical slice of BIMSpend: a minimal end-to-end
prototype for project time-and-cost intelligence. It uses synthetic data and
adapter interfaces so real ActivityWatch, Miru and Revit integrations can be
connected later.

**No real employee data. No employee monitoring. No production deployment.**

## Architecture (composition, not merger)

Following the PLAN_AUDIT_REPORT recommendation ("API/adapter first"):

| Layer | Responsibility | Implementation |
|-------|---------------|----------------|
| Project identity | Companies, clients, projects, teams | `src/bimspend/adapters/miru.py` (synthetic Miru-like API) |
| Activity observation | Active window / AFK events | `src/bimspend/adapters/activitywatch.py` (synthetic ActivityWatch-like API) |
| Correlation | Observed activity -> attributed project time | `src/bimspend/correlation.py` |
| Review | Designer review of suggested hours | `src/bimspend/review.py` |
| Dashboard | Manager project-hours view | `src/bimspend/dashboard.py` |
| Persistence | SQLite (stand-in for PostgreSQL) | `src/bimspend/db.py` |

## Metric separation (core design principle)

Observed activity, attributed time, approved time, billed hours and loaded
internal cost are stored as **separate records**. No automatic inference that
window focus equals productive or billable work.

## Quick start

```powershell
# From the repository root
cd src
pip install -e .           # install package (dev: pip install -e .[dev])
python -m pytest tests/    # run automated tests
python -m bimspend.runner  # launch the vertical slice demo
```

See `docs/RUNBOOK.md` for full launch and test instructions.

## Repository layout

```
src/bimspend/          # application source
tests/                 # automated tests
data/synthetic/        # synthetic fixtures (no real data)
docs/RUNBOOK.md        # launch and test instructions
```

## Related governance

- `CONTEXT_FOR_AI.md` — continuation context
- `MASTER_PLAN.md` — master plan (BUILD 01 AUTHORIZED)
- `TASK_TRACKER.md` — task status
- `AI_HANDOFF.md` — AI handoff
- `docs/decisions/decision-log.md` — decision log
- `docs/technical-feasibility/PLAN_AUDIT_REPORT.md` — feasibility audit
