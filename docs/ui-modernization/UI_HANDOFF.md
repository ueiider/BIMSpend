# BIMSpend — UI Handoff

**Branch**: `design/opencode-r1-08-desktop-ui-modernization`
**Base**: R1-07 `build/bimspend-r1-07-financial-integration` at `15faa0560c17a4c0445345f8283b36ba770a6b48`
**Mode**: UI MODERNIZATION — visual and UX improvements only, no new backend services

## Read in this order

1. `CONTEXT_FOR_AI.md`
2. `TASK_TRACKER.md`
3. `AI_HANDOFF.md`
4. `docs/ui-modernization/UI_PROGRESS_TRACKER.md` (this document)
5. `docs/product-design/` (if UI spec exists)

## Completed work

R1-07 financial integration is complete: schema v10, FinancialService/BudgetService/CostRateService,
FinancialDashboardScreen, ProjectFinancialDetailScreen, FinancialReportsScreen, 22 domain tests.
All 168 domain tests + 7 GUI tests pass.

## Current state of UI

Framework: Tkinter + ttk ("clam" theme). 14 screens with lazy loading in shell.
Shell has no login, no role-based nav, no breadcrumbs, no search.
TimesheetReviewScreen uses hardcoded "designer_01".

## Prohibitions (from AGENTS.md)

- Do not implement new financial/billing services
- Do not rewrite as web app
- Do not build disconnected HTML prototype
- Do not modify Nemotron's remediation branch
- Do not modify `main`
- Do not force-push

## Next action

Start Phase 2 — Design System creation.
