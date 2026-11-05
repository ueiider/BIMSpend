# Conceptual product roadmap — BIMSpend

**Status: EXPLORATION ONLY. These are hypotheses and possible sequences, not commitments. Nothing here is approved.**

## Roadmap states used in this project

IDEA → UNDER INVESTIGATION → VALIDATED → REJECTED / DEFERRED → APPROVED (only with explicit user approval).

## Conceptual phases (Mermaid)

```mermaid
%%{init: {'theme': 'base'}}%%
gantt
    title BIMSpend conceptual roadmap (unapproved)
    dateFormat  YYYY-MM-DD
    section Discovery
    Product discovery and problem validation     :done,    d1, 2026-11-05, 30d
    Competitor and differentiation assessment    :active,  d2, 2026-11-05, 30d
    Brand and domain clearance (BIMSpend)        :         d3, 2026-12-01, 30d
    section Feasibility (hypothesis)
    Revit journal historical-data PoC            :         d4, 2026-12-01, 45d
    Minimal Autodesk signal attribution study    :         d5, 2027-01-01, 60d
    Privacy, employment law, Autodesk terms review:        d6, 2027-01-01, 45d
    section Potential build (if approved)
    Windows desktop agent + Revit connector      :         d7, 2027-03-01, 90d
    Manager dashboard prototype                  :         d8, 2027-05-01, 60d
    Actual-vs-billed financial model             :         d9, 2027-06-01, 60d
```

## Decision gates (examples)

| Gate | Question | Required before proceeding |
|---|---|---|
| G1 | Is there a validated gap in actual-vs-billed tracking? | Buyer interviews / problem validation |
| G2 | Can Autodesk signals attribute time to a project with acceptable error? | Feasibility PoC results |
| G3 | Is monitoring permitted under law/contracts/terms? | Legal review |
| G4 | Is the brand (BIMSpend / domain) clearable? | Trademark/domain clearance |
| G5 | Should an MVP be built? | Explicit user approval |

## Next recommended step

Answer decision-log question 1: "How is actual time measured today when billed hours are discounted? What source is reliable?" This sits under G1 and precedes any build decision.
