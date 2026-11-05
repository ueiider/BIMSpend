# Historical project pricing workflow — Mermaid

**Status: EXPLORATION ONLY. Historical estimating benchmarks are a hypothesis, not a validated method.**

## From history to future estimate

```mermaid
flowchart TB
    H1[Historical projects:<br/>actual hours, billed hours,<br/>fees, scope, phase, LOD]
    H2[Tag each project by:<br/>building type, levels,<br/>apartment count, repeat plates,<br/>coordination complexity]
    H3[Filter to comparable<br/>projects only]
    H4[Compute effort per unit:<br/>hours/floor, hours/apartment,<br/>cost per deliverable]
    H5[Show uncertainty ranges,<br/>not false precision]
    F1[New project:<br/>scope, levels, complexity]
    F2[Apply historical benchmarks<br/>+ contingency]
    F3[Loaded labor cost +<br/>target margin → quote]
    F4[Track actuals against quote<br/>during delivery]

    H1 --> H2 --> H3 --> H4 --> H5 --> F1 --> F2 --> F3 --> F4
    style H1 fill:#183457,stroke:#3a6995,color:#fff
    style F3 fill:#183457,stroke:#3a6995,color:#fff

    linkStyle default stroke:#63c5ed,stroke-width:2
```

## Cautionary notes

- Models with equal sprinkler counts (or other deliverable counts) can require different time.
- Effort depends on project phase, model maturity, coordination complexity, scope, and variations.
- Small or non-comparable samples produce unreliable benchmarks.
- Journal-based historical recovery is unproven; see `docs/research/historical-data-research.md`.
