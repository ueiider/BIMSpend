# Automatic tracking workflow — Mermaid

**Status: EXPLORATION ONLY. This is a conceptual workflow, not an implemented process.**

## Designer-side flow (zero routine interaction)

```mermaid
flowchart TD
    Start([Windows sign-in /<br/>Autodesk app launch]) --> Agent[Windows desktop agent starts<br/>in background]
    Agent --> App[Designer opens Revit /<br/>AutoCAD / Navisworks]
    App --> Conn[Application connector attaches<br/>to session]
    Conn --> Events[Session / file / command events]
    Events --> Filter{Idle or<br/>non-design activity?}
    Filter -->|Yes| Drop[Exclude or flag as idle<br/>— not counted as active time]
    Filter -->|No| Map[Map model/file to<br/>commercial project<br/>hypothesis: mapping required]
    Map --> Buffer[Write encrypted local buffer record]
    Buffer --> Sync[Sync to central store<br/>when online]
    Sync --> Dashboard[Manager dashboard: hours,<br/>cost, actual vs billed]

    style Agent fill:#183457,stroke:#3a6995,color:#fff
    style Buffer fill:#183457,stroke:#3a6995,color:#fff

    linkStyle default stroke:#63c5ed,stroke-width:2
```

## Manager-side review flow

```mermaid
flowchart TD
    M1[Manager opens dashboard<br/>from another computer]
    M2[Select period, user, project]
    M3[View actual hours vs<br/>billed hours vs cost]
    M4[Realization & effective<br/>rate calculated]
    M5[Flag variances:<br/>unbilled time, discounts]
    M6[Use history to inform<br/>future quotes/estimates]
    M1 --> M2 --> M3 --> M4 --> M5 --> M6
```

## Design requirements

- No designer daily login, timer, project selection, or timesheet entry (user requirement).
- Transparent monitoring with corrections/appeals process for designers.
- Admin controls deployment, user mapping, permissions, retention.
- Do not present this workflow as implemented software.
