# Changelog — BIMSpend brainstorming repository

All notable structural and documentation changes are recorded here. This changelog tracks repository organization, not product approvals.

## 2026-11-05 — Repository initialized

- Created local workspace at `D:\BIMSpend` and private GitHub repository `ueiider/BIMSpend`.
- Extracted `BIMSpend-Brainstorm.zip` and reorganised its contents into the standard structure (docs/, visuals/, examples/, templates/, archive/).
- Preserved all original source documents under descriptive new filenames; originals remain intact (no content discarded).
- Archived the original zip at `archive/original-source/BIMSpend-Brainstorm.zip` for provenance.
- Added `AGENTS.md` (AI agent operating instructions), `CHANGELOG.md`, `CONTEXT_FOR_AI.md` (expanded continuation context), and `README.md`.
- Added `docs/research/historical-data-research.md` (Revit Journal historical-data research).
- Added `docs/financial-model/synthetic-examples.md` (worked synthetic calculations).
- Added `docs/product-vision/product-vision.md` and `docs/product-vision/product-roadmap.md` (vision and conceptual roadmap).
- Added Mermaid diagram documents for system architecture, automatic tracking workflow, desktop–connector communication, time-to-cost conversion, historical pricing workflow, and roadmap.
- Added `templates/decision-log-template.md` and `docs/meeting-notes/meeting-notes-template.md`.
- Retained all original SVG diagrams (well-formed) and synthetic example data.
- Committed and pushed to GitHub; repository visibility confirmed PRIVATE.

## 2026-11-05 — Open-source candidate assessment

- Documented Miru (MIT), ActivityWatch (MPL-2.0), optional Journalysis (MIT), and custom Revit add-in as research candidates, not selected architecture.
- Added licensing caveats, component architecture hypothesis, security/privacy checks, mandatory integration tests, and conditional prototype GO / production NO-GO.
- Updated `CONTEXT_FOR_AI.md` so future agents can resume with the latest findings and mobile dashboard hypothesis.
- No software installed, code copied, production deployment performed, or MVP approved.

## 2026-11-06 — R1-06 Designer Review and Manager Approval UI

- Branch `build/bimspend-r1-06-review-approval-ui` created from R1-05 commit `556b7b8291896175ec92602b52e6b0ce8901ab76`
- Schema migrated to v9: added `suggestion_decisions` table for audit trail of submit/approve/reject/return_for_correction/split/merge
- Added `src/bimspend/capture/suggestion_domain.py`: SuggestionService domain service with submit/approve/reject/return_for_correction/split/merge operations, all enforcing authenticated session, company-scoped authorization, and role-based access control
- Added `src/bimspend/app/screens/designer_review.py`: DesignerReviewScreen with suggestion table (project, start, end, minutes, confidence, source, state), project filter, and actions (edit, submit, reject, split, merge)
- Added `src/bimspend/app/screens/manager_approval.py`: ManagerApprovalScreen with entry table (entry ID, project, user, start, end, minutes, confidence, state), project filter, and actions (approve, reject, return for correction, bulk approve, bulk reject)
- Updated `src/bimspend/app/shell.py`: Added navigation entries for designer_review and manager_approval screens
- Fixed `src/bimspend/db.py`: upsert_suggestion now uses DO UPDATE instead of DO NOTHING so state changes are persisted
- Added `tests/capture/test_suggestion_domain.py`: 7 tests for auth enforcement, RBAC, company-scoped authorization, audit trail recording
- Fixed `tests/capture/test_suggestion_engine.py`: Added missing project creation in test_designer_reject_suggestion
- Updated `.github/workflows/preview-tests.yml`: Added `build/bimspend-r1-06-review-approval-ui` to branch filter
- All 146 domain tests pass (7 GUI tests deselected - no Tcl/Tk display available)
- Committed and pushed as `0ae3d9895fc8b73240851012eb0b27cf144afe68`
- Updated AI_HANDOFF.md, TASK_TRACKER.md, R1_NATIVE_CAPTURE_PROGRESS.md

## 2026-11-05 — PLAN-first workflow established

- Added `MASTER_PLAN.md`, `TASK_TRACKER.md`, and `AI_HANDOFF.md` to enforce reuse-first PLAN → approval → BUILD → TEST workflow and conserve paid tokens.
- Defined phase gates, P1-01 next action, required evidence, manager/designer role hypotheses, and prohibitions on unauthorized implementation.
- No application code, deployments or integrations changed.
