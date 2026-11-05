# Technical research — NOT implementation specification

## Potential component diagram
Windows agent ↔ application-specific connectors (Revit, AutoCAD, Navisworks, Civil 3D if viable) → local buffer → optional cloud sync → manager dashboard. Alternative architectures remain open.

## Installation hypothesis
One Windows installer bundles desktop agent and suitable integration packages; starts at Windows sign-in and attaches to supported Autodesk products. Different Revit versions may require different .NET/add-in builds. Revit versions installed later need a supported integration registration mechanism.

## Critical accounting cases
Multiple Revit instances; same project in multiple models; model renamed/moved; central/local/cloud models; family editor (.rfa); idle periods; remote desktop; offline usage; overnight open session; simultaneous other app use; work outside Autodesk; multi-user shared PCs; daylight saving/time zone.

## Revit Journals inventory — user-run read-only PowerShell, 2026-11-05
| Revit | Files | Oldest file modification | Newest file modification |
|---|---:|---|---|
| 2021 | 10 | 2025-10-14 | 2025-10-31 |
| 2022 | 14 | 2026-09-15 | 2026-11-05 |
| 2023 | 25 | 2025-04-07 | 2026-10-23 |
| 2024 | 26 | 2026-08-25 | 2026-11-04 |
| 2025 | 10 | 2026-08-12 | 2026-11-05 |
| 2026 | 16 | 2026-10-26 | 2026-11-05 |
| **Total** | **101** | | |

These are file modification timestamps, not verified session times. Some journals may be incomplete or rotated. Journal parser needs testing before any claims of retroactive hours.

## Historical data candidates
Local Revit Journals (diagnostic traces); model file metadata; worksharing history where accessible; Autodesk Construction Cloud/BIM 360 model versions and sync events; previously installed third-party trackers. Cloud sync history ≠ active work time. Never infer exact hours from only open/close timestamps.

## Safe proof-of-concept approach
Inventory available logs read-only; inspect anonymized patterns; compare a small set of known sessions with observed elapsed and active time; quantify error and coverage; preserve evidence/confidence and provenance. Do not upload raw Journals or proprietary model content without permission.
