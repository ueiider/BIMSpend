# Desktop agent and application connector communication — Mermaid

**Status: EXPLORATION ONLY. Communication protocol and boundaries are undecided.**

## Conceptual communication flow

```mermaid
sequenceDiagram
    participant U as Designer (user)
    participant Revit as Revit / AutoCAD / Navisworks
    participant Conn as Application connector<br/>plugin / add-in
    participant Agent as Windows desktop agent<br/>background service
    participant Buffer as Local encrypted buffer<br/>offline persistence
    participant Sync as Sync service<br/>(optional, undecided)
    participant Dashboard as Manager dashboard<br/>another computer

    U->>Revit: Opens model, works normally
    Revit->>Conn: Session, file, command events
    Conn->>Agent: Activity signals (IPC / local API)
    Agent->>Agent: Deduplicate, idle filtering,<br/>project mapping (hypothesis)
    Agent->>Buffer: Write buffered record<br/>offline-safe
    alt Online
        Buffer->>Sync: Upload when connected
    end
    Sync->>Dashboard: Project / employee / time / cost view
    Dashboard->>U: Transparency / corrections / appeals (design required)

    note over Agent, Dashboard: No daily login, no manual timer,<br/>no project selection required from designer (hypothesis)
```

## Open interface questions

- Connector-to-agent transport: local TCP, named pipes, .NET interop, or file-based queue — undecided.
- Version support: one build per supported Revit version; registration mechanism for later-installed versions — undecided.
- Offline behavior: local buffer with retry/sync when online — hypothesis.
- Multi-instance and multi-model deduplication — not solved.
- Security: local encryption, access controls, employee notice — design required.
