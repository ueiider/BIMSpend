# Historical data research — Revit Journal Files and related sources

**Status: research only. Not an implementation specification. No journal files were modified, scanned for confidential content, or uploaded.**

## Purpose

Investigate whether historical project effort can be reconstructed from data already present on a designer's PC, in support of the BIMSpend hypothesis that actual hours can be compared with invoiced hours and used to improve future estimates. All findings below are hypotheses requiring validation.

## Available data sources

| Source | What it may contain | Reliability for active working time | Notes |
|---|---|---|---|
| Local Revit Journal files (`Journal*.txt`) | Diagnostic traces: application start/end, document open/save, commands, warnings, errors, timestamps | Low to medium — diagnostics, not timesheets | 101 files observed across Revit 2021–2026. File modification timestamp ≠ session time. |
| Revit model file metadata (`.rvt`) | Author, last saved by, save date, build, worksharing GUIDs | Low for effort | Metadata changes on save only; does not capture active work time. |
| Worksharing history / central model sync events | Sync events, user, file, timestamp (where accessible) | Medium for sync activity | Sync events are not continuous work; users may sync infrequently or not at all. |
| Autodesk Construction Cloud / BIM 360 model versions | Version history, who uploaded, when | Medium for publication activity | Cloud sync history ≠ active work time; offline work not captured. |
| Previously installed third-party trackers (e.g., ManicTime, INFINITY) | Application usage, idle/active time, per-file duration | Varies | Depends on whether such tools were installed and for how long. |
| Manual timesheets / calendars / emails | Self-reported project time | Varies by discipline | Often the only source of billed-hours justification today. |

## Potential reconstruction methods

1. **Journal parse for session bounds:** Use journal "Journal started"/"Journal ended" or Revit startup/shutdown events to bound a session; subtract known idle gaps if detectable.
2. **Document activity weighting:** Weight time by document open/save frequency, command count, and file modification deltas as a proxy for active effort.
3. **Cross-source correlation:** Compare journal-derived session bounds against directly observed elapsed time for a small set of known sessions to quantify error and coverage.
4. **Project attribution:** Map journals to commercial projects via file path, model name, workset/project parameter, or user-supplied mapping. Ambiguous for renamed/moved/shared models.

## Technical limitations

- Journals are diagnostic traces, not authoritative timesheets. They may be incomplete, rotated, missing, or reset by version.
- An open Revit session does not equal active design time (idle, overnight open sessions, meetings, remote desktop, background work).
- Multiple Revit instances, central/local models, family editor (`.rfa`), renames, and multi-user PCs complicate attribution.
- Journal files do not reliably map to a commercial project without additional context.
- File modification timestamps are not verified session times.
- Retroactive reconstruction from old journals has unquantified error; do not present results as measured hours.

## Privacy considerations

- Journal files may contain file paths, user names, computer names, command history, and potentially project-identifying information.
- Do not scan, extract, or upload journal files or model content containing confidential project data unless explicitly authorized.
- Any analysis should be read-only, local, anonymized, and aggregated. Employee transparency and consent are design requirements, not afterthoughts.
- Employment law, customer contracts, and Autodesk terms may restrict monitoring; legal review is needed before any deployment.

## Data confidence levels

| Claim | Confidence | Basis |
|---|---|---|
| 101 Revit Journal files exist across Revit 2021–2026 | Tested | User-run PowerShell inventory (2026-11-05) |
| Journals contain timestamps and commands | Tested | General knowledge of Revit Journal format |
| Journals can reconstruct reliable active working hours | Unproven | No parser output supplied; diagnostic format only |
| Historical effort can drive future estimates | Hypothesis | Effort depends on scope, complexity, phase, LOD, variations; not derivable from hours alone |

## Proposed proof-of-concept experiments

1. Inventory journal files read-only; record count, version, date range, file size (no content upload).
2. Inspect anonymized journal patterns: session open/close markers, document events, command frequency.
3. Select a small set of known sessions (observed start/end) and compare against journal-derived bounds; quantify error and coverage.
4. Test project attribution on a non-confidential sample model: path, name, workset, project parameter mapping.
5. Document results with confidence levels and provenance; do not infer exact hours from open/close timestamps alone.

## Related documents

- `docs/technical-feasibility/technical-research.md` — component diagram, installation hypothesis, critical accounting cases, journal inventory table.
- `docs/competitors/market-and-brand.md` — competitor and brand research.
- `CONTEXT_FOR_AI.md` — historical data section (section 6).
