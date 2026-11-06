# BIMSpend — Architecture Alignment Audit (2026-11-06)

## Owner-confirmed product decision (authoritative)
BIMSpend is ONE independent commercial application, with integrated automatic activity capture, BIM/Revit project correlation, timesheets and approvals, costing, billing and managerial reporting. ActivityWatch and Miru are open-source REUSE CANDIDATES, not mandatory third-party applications or services to install or operate. Optional migration/import adapters may exist, but must not be confused with required runtime dependencies. Preserve applicable licenses and attribution. Do not imply Miru's code is already incorporated without source evidence.

## Evidence inspected (read-only GitHub inspection)
- Compared `main` with `design/opencode-r1-08-desktop-ui-modernization`: ahead 39, behind 0 at inspection time.
- `src/bimspend/capture/controller.py` implements a native capture lifecycle with explicit consent and company-scoped authentication.
- `src/bimspend/capture/activitywatch_derived/{windows.py,watcher_main.py,privacy_filter.py}` and `docs/open-source/ACTIVITYWATCH_SOURCE_MANIFEST.md` document adapted ActivityWatch code (MPL-2.0); provenance and distribution compliance still require independent validation.
- `src/bimspend/capture/revit_connector.py`, `revit_ipc.py`, `project_correlation.py`, `suggestion_engine.py` are present.
- `src/bimspend/integrations.py` retains an explicitly opt-in, disabled-by-default `ActivityWatchLocalClient`. Presence of an optional adapter is not proof of a mandatory dependency.
- Financial modules and UI screens exist in the R1-08 branch; existence is not proof of full production readiness.
- `AI_HANDOFF.md` still recommended an API/adapter-first Miru architecture, said to await build authorization, and prohibited modifying product code despite documenting later authorized implementation. `CONTEXT_FOR_AI.md` still said no product was built. These are stale historical assertions.

## Verified vs not verified
Verified: repository file presence, source-level implementation evidence, and branch divergence. Not verified: clean builds and CI at current head, complete runtime independence from Miru/ActivityWatch, full Miru feature parity, legal compliance, real Revit validation, secure multi-tenancy, installer readiness, end-to-end Windows capture, complete branch integration.

## Mandatory engineering gates before merge to main
1. Inventory all active branches and exact remote HEAD SHAs; compare against R1-08 and main. Include unmerged finance, capture, review and integration work; identify duplicates/conflicts.
2. Dependency audit: search imports, network clients, launch/install scripts, configs and docs for mandatory Miru or ActivityWatch runtime dependencies. Classify each as native, optional compatibility adapter, planned, or blocker.
3. Feature parity matrix: Miru-derived features (companies, clients, projects, timesheets, invoices, reports, roles) vs BIMSpend actual implemented source and tests; never claim code reuse without provenance.
4. Run clean Windows domain/GUI/capture/integration tests, packaging smoke tests and Revit read-only validation. Record exact commands, results and CI run URLs.
5. License/SBOM and third-party source provenance audit; security/privacy, consent, tenant isolation and sensitive-data handling.
6. Review stale documentation in all agents' handoff files and consolidate a single source of truth. Preserve historical research as historical.
7. Merge only after evidence-backed review and explicit approval. No production deployment or MSI in this documentation-only audit.

## Scope of this checkpoint
Documentation and evidence only. No application source modified; no merge, no deletion, no production change. Outstanding gates remain OPEN.
