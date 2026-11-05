# Project time-to-cost conversion — Mermaid

**Status: EXPLORATION ONLY. Formulas are discussion aids, not an approved pricing or cost model.**

## Conversion flow

```mermaid
flowchart TB
    subgraph Inputs ["Measured / observed inputs"]
        I1[Actual hours worked<br/>from tracking]
        I2[Loaded labor cost rate<br/>A$/hour]
        I3[Standard charge rate<br/>A$/hour]
        I4[Invoiced / billed hours<br/>from invoices]
    end

    subgraph Calculations ["Derived metrics"]
        C1[Labor cost =<br/>actual hours × loaded rate]
        C2[Revenue =<br/>billed hours × charge rate]
        C3[Realization =<br/>billed / actual hours]
        C4[Effective rate =<br/>revenue / actual hours]
        C5[Unbilled reference =<br/>standard value − revenue]
    end

    subgraph Outputs ["Dashboard outputs"]
        O1[Project contribution<br/>after labor = revenue − labor cost]
        O2[Profitability view]
        O3[Historical benchmark<br/>for future quotes]
    end

    I1 --> C1
    I2 --> C1
    I3 --> C2
    I4 --> C2
    I1 --> C3
    I4 --> C3
    C2 --> C4
    C1 --> C3
    I3 --> C5
    C2 --> C5
    C1 --> O1
    C2 --> O1
    C3 --> O2
    C4 --> O2
    C3 --> O3
    C4 --> O3

    style C1 fill:#183457,stroke:#3a6995,color:#fff
    style C3 fill:#183457,stroke:#3a6995,color:#fff
    style O1 fill:#183457,stroke:#3a6995,color:#fff

    linkStyle default stroke:#63c5ed,stroke-width:2
```

## Key distinction (synthetic illustration)

Actual hours worked ≠ hours invoiced. Example: designer works 12 hours; company invoices 8 hours at A$110/h → invoice A$880 vs standard value A$1,320. The A$440 difference is unbilled reference value, not automatically accounting loss.

## Synthetic example — project cost

| Item | Value | Basis |
|---|---|---|
| Fee | A$18,000 | Synthetic |
| Actual hours | 160 h | Synthetic |
| Loaded hourly cost | A$65/h | Synthetic |
| Labor cost | A$10,400 | Synthetic |
| Remaining after labor | A$7,600 | Excludes all other costs |

See `docs/financial-model/synthetic-examples.md` for full worked examples (Examples A–C).
