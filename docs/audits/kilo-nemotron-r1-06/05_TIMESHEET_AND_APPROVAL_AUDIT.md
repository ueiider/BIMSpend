# Timesheet & Approval Audit — BIMSpend R1-06

**Baseline**: `4e83d9b41533423f50c1f8042a2a2ef79445f0a4`
**Files Audited**:
- `src/bimspend/capture/suggestion_engine.py` (463 lines)
- `src/bimspend/capture/suggestion_domain.py` (548 lines)
- `src/bimspend/review.py` (317 lines)
- `src/bimspend/correlation.py` (107 lines)
- `src/bimspend/models.py` (444 lines)
- `src/bimspend/db.py` (1385 lines)

---

## Suggestion Engine (`suggestion_engine.py`)

### Pipeline
```
1. collect_observations(user_id, start_time, end_time)
   └─ db.list_events(user_id) → filter by time range → sort by started_at
   └─ _event_to_observation() → looks up revit_correlation_evidence
   
2. Filter: exclude is_afk=True, is_locked=True
   
3. _group_observations() → consecutive same project_id
   └─ AFK/locked observations EXCLUDED but do NOT break chain
   └─ Same project on either side of AFK gap → MERGED
   
4. Filter: min_duration_minutes (default 5.0)
   
5. _build_suggestion() → TimeEntrySuggestion
   ├─ Deterministic ID: hash(start_time + sorted evidence_ids)
   ├─ project_id = most frequent non-None project_id
   ├─ confidence = highest from events (CONFIRMED > HIGH > MEDIUM > LOW > UNASSIGNED)
   └─ evidence_ids = all event_ids in group
```

### Critical Findings

| ID | Severity | Finding |
|----|----------|---------|
| TE-001 | HIGH | **AFK gaps do not break suggestion chains** — observations on either side of AFK merged into single suggestion, overstating continuous work |
| TE-002 | HIGH | **No timezone handling** — all timestamps treated as UTC; user local time not considered for day boundaries |
| TE-003 | MEDIUM | **Project_id frequency wins** — if 3 events project A, 2 events project B → suggestion gets project A even if B was longer duration |
| TE-004 | MEDIUM | **Confidence = max of events** — one HIGH confidence event upgrades entire suggestion, masking LOW confidence majority |
| TE-005 | MEDIUM | **External_id collision risk** — deterministic ID uses start_time + evidence_ids; clock skew or re-processing could create different IDs for same work |
| TE-006 | LOW | **`company_id` not enforced in collect_observations** — cross-tenant leakage possible if events lack company_id |
| TE-007 | LOW | **Raw SQL in `_get_correlation_evidence`** — bypasses Database abstraction, tight coupling to schema |

### Idempotency
- `generate_suggestions()` is deterministic — same input → same suggestions
- `save_suggestion()` uses `upsert_suggestion()` with `ON CONFLICT(id) DO UPDATE`
- **Gap**: If evidence_ids change (re-correlation), same start_time produces different ID → duplicate suggestions

---

## Correlation (`correlation.py`)

### Strategy
```python
# 1. Exact/substring match on project name in window title (confidence 0.85)
# 2. Fallback: client name in window title (confidence 0.60)
# 3. NO automatic fallback — UNASSIGNED (project_id=None)
```

### Findings
| ID | Severity | Finding |
|----|----------|---------|
| TE-008 | HIGH | **Substring matching on window titles** — "Project Alpha" matches "Alpha Bank Statement" → false positives |
| TE-009 | HIGH | **No project code registry** — relies on full project name/client in window title; Revit documents rarely contain full names |
| TE-010 | MEDIUM | **Case-insensitive but no word boundaries** — "ABC" matches "XABCY" |
| TE-011 | MEDIUM | **No confidence calibration** — 0.85/0.60 arbitrary, not validated against ground truth |
| TE-012 | LOW | **Single-pass, first-match-wins** — no multi-candidate scoring |

---

## Review Workflow (`review.py` + `suggestion_domain.py`)

### TimeEntry State Machine
```
PENDING_REVIEW → SUBMITTED → APPROVED → BILLED
                     │           │
                     ▼           ▼
                  REJECTED ← RETURNED_FOR_CORRECTION
                     │
                     ▼
              PENDING_REVIEW (reset_to_pending)
```

### Authorization (SH-001 + SH-002)
| Action | Required Role | Ownership Check | Company Check |
|--------|---------------|-----------------|---------------|
| submit_entry | DESIGNER | actor.id == entry.user_id | actor.company_id == entry.company_id |
| approve_entry | MANAGER | — | actor.company_id == entry.company_id |
| reject_entry (submitted) | MANAGER | — | actor.company_id == entry.company_id |
| reject_entry (pending) | DESIGNER | actor.id == entry.user_id | actor.company_id == entry.company_id |
| bill_entry | MANAGER | — | actor.company_id == entry.company_id |
| reset_to_pending | DESIGNER | actor.id == entry.user_id | actor.company_id == entry.company_id |
| edit_entry | DESIGNER | actor.id == entry.user_id | actor.company_id == entry.company_id |

### Suggestion State Machine (`suggestion_domain.py`)
```
PENDING_REVIEW → SUBMITTED → APPROVED
                     │
                     ├── REJECTED (manager)
                     ├── REJECTED (designer self-reject)
                     └── RETURNED_FOR_CORRECTION → SUBMITTED (after reset)
PENDING_REVIEW → MERGED (split/merge)
```

### Critical Findings

| ID | Severity | Finding |
|----|----------|---------|
| TE-013 | CRITICAL | **`TimeEntry.attributed_time_id` FK not enforced** — SQLite FK deferred; orphaned TimeEntries possible if AttributedTime deleted |
| TE-014 | HIGH | **`submit_suggestion` creates AttributedTime with `activity_event_id = suggestion.evidence_ids[0]`** — uses first evidence ID as FK target; if evidence_ids empty, uses suggestion.id (invalid FK) |
| TE-015 | HIGH | **Approval does NOT create billing** — correct design, but `bill_entry` allows `billed_minutes > approved_minutes × 2` (sanity check only) |
| TE-016 | HIGH | **`suggestion_domain.py` uses `current_auth.actor` which validates session on EVERY access** — fail-closed but module-level global; not thread-safe for background workers |
| TE-017 | MEDIUM | **`return_for_correction` sets state to REJECTED (not new state)** — loses distinction between rejection and return-for-correction |
| TE-018 | MEDIUM | **Split/merge audit records use `previous_state="multiple"` / `new_state="merged"`** — not queryable by standard state values |
| TE-019 | MEDIUM | **No validation that `edited_minutes` / `edited_project_id` are set before submit** — designer can submit unedited suggestion |
| TE-020 | LOW | **`bill_entry` sanity check: `billed_minutes > minutes * 2`** — arbitrary 2x multiplier, not configurable |

---

## Approval-to-Financial Bridge (R1-06 Gap)

### Current State
- **No financial bridge implemented in R1-06**
- `runner.py` demonstrates the intended flow but uses in-memory calculations
- `dashboard.py::all_projects_summary()` computes:
  - `observed_hours` — from ActivityWatch events
  - `attributed_hours` — from AttributedTime
  - `approved_hours` — from TimeEntry state=APPROVED
  - `billed_hours` — from TimeEntry.billed_minutes
  - `labor_cost` — approved_minutes × loaded_cost_rate
  - `standard_value` — approved_minutes × standard_rate
  - `realization` — billed / observed

### Missing Integration Contract
| Requirement | Status |
|-------------|--------|
| Approved TimeEntry → Financial Service | ❌ Not defined |
| Rate snapshots at approval time | ✅ `standard_rate`, `loaded_cost_rate` stored on TimeEntry |
| Billed minutes separate from approved | ✅ `billed_minutes` field |
| Realization gap tracking | ✅ Computed in dashboard |
| Duplicate accounting prevention | ❌ No idempotency key for financial records |
| Audit trail for financial decisions | ❌ Only time_entry_audit, no financial_audit |

### R1-07 Integration Risks (for OpenCode)
| Risk | Impact |
|------|--------|
| Financial service reads PENDING/SUBMITTED entries | Overstates revenue/cost |
| Rate changes after approval not reflected | Correct — rates snapshotted |
| Billed minutes can exceed approved | Sanity check only (2x) |
| No financial approval workflow | Manager approval ≠ financial approval |
| Cross-company financial isolation | Depends on company_id enforcement |

---

## Duplicate Prevention & Overlap Handling

### TimeEntry Uniqueness
```python
# db.py:272 - v2 migration
CREATE UNIQUE INDEX IF NOT EXISTS ux_time_entries_attribution ON time_entries(attributed_time_id)
```
- One TimeEntry per AttributedTime — prevents double-billing same attributed time
- **Gap**: Multiple AttributedTime can reference same ActivityEvent (different project_id) → could create multiple TimeEntries for same observed time

### Suggestion Overlap
- `_group_observations` merges consecutive same-project observations
- AFK/locked gaps do NOT break chains (TE-001)
- Different projects create separate suggestions — no overlap detection across projects

### AttributedTime Overlap
- `correlate_events()` creates one AttributedTime per ActivityEvent
- `UNIQUE` constraint on `activity_events(source, external_id)` prevents duplicate events
- **Gap**: No constraint preventing overlapping AttributedTime for same user/time

---

## Audit Trail Integrity

### time_entry_audit
- Triggered on state change, minutes change, billed_minutes change
- Records: actor_id, action, previous_state, new_state, previous_minutes, new_minutes, billed_minutes
- **Gap**: `actor_id` can be "unspecified_demo" if not provided — weak accountability

### suggestion_decisions
- Records: submit, approve, reject, return_for_correction, split, merge
- Includes: previous_minutes, new_minutes, notes
- **Gap**: `split`/`merge` use non-standard state values ("multiple", "merged")

---

## Findings Summary

| ID | Severity | Category | Finding |
|----|----------|----------|---------|
| TE-001 | HIGH | Suggestion Engine | AFK gaps don't break chains — overstates continuous work |
| TE-002 | HIGH | Suggestion Engine | No timezone handling — day boundaries incorrect for non-UTC users |
| TE-003 | MEDIUM | Suggestion Engine | Project frequency wins over duration — misattributes mixed-project time |
| TE-004 | MEDIUM | Suggestion Engine | Confidence = max(event confidence) — masks low-confidence majority |
| TE-005 | MEDIUM | Suggestion Engine | Deterministic ID fragile to evidence_id changes |
| TE-006 | LOW | Suggestion Engine | company_id not enforced in collect_observations |
| TE-007 | LOW | Suggestion Engine | Raw SQL bypasses Database abstraction |
| TE-008 | HIGH | Correlation | Substring matching on window titles — false positives |
| TE-009 | HIGH | Correlation | No project code registry — Revit titles rarely match project names |
| TE-010 | MEDIUM | Correlation | No word boundaries in matching |
| TE-011 | MEDIUM | Correlation | Confidence values arbitrary, not calibrated |
| TE-012 | LOW | Correlation | First-match-wins, no multi-candidate scoring |
| TE-013 | CRITICAL | Review | TimeEntry.attributed_time_id FK not enforced in SQLite |
| TE-014 | HIGH | Review | submit_suggestion creates invalid AttributedTime FK |
| TE-015 | HIGH | Review | bill_entry allows 2x approved minutes — arbitrary limit |
| TE-016 | HIGH | Auth | Module-level current_auth not thread-safe for background workers |
| TE-017 | MEDIUM | Review | return_for_correction loses distinction from reject |
| TE-018 | MEDIUM | Audit | split/merge audit states not queryable |
| TE-019 | MEDIUM | Review | No validation of edited fields before submit |
| TE-020 | LOW | Review | 2x billed_minutes limit not configurable |

---

## Recommendations

### P0 — Immediate (for R1-07)
1. **Enforce FK on `time_entries.attributed_time_id`** — `PRAGMA foreign_keys=ON` + explicit FK
2. **Fix `submit_suggestion` AttributedTime creation** — Need valid ActivityEvent FK, not evidence_ids[0]
3. **Add company_id enforcement to `collect_observations()`** — Filter events by company_id
4. **Thread-safe auth context** — Replace module-level `current_auth` with per-request `SessionContext`

### P1 — Short-term
5. **AFK-aware suggestion grouping** — Configurable: break chain on AFK/locked gaps
6. **Project code registry for correlation** — Explicit codes, not substring matching
7. **Timezone-aware day boundaries** — User local timezone for suggestion grouping
8. **Confidence calibration** — Weighted average, not max; configurable thresholds

### P2 — Medium-term
9. **Financial bridge contract** — Define approved TimeEntry → Financial Record mapping
10. **Financial audit table** — Track billing decisions separately from review decisions
11. **Overlap detection** — Prevent multiple TimeEntries for same observed time window
12. **Configurable billed_minutes limit** — Per-project or per-company policy

### P3 — Long-term
13. **ML-based correlation** — Learn project→title patterns from designer corrections
14. **Suggestion quality metrics** — Track acceptance rate, edit rate, rejection reasons
15. **Automatic suggestion refresh** — Re-process when new correlation evidence arrives

---

## Mermaid: Suggestion Generation Pipeline

```mermaid
flowchart TD
    A[collect_observations\nuser_id, start, end] --> B{Filter by\ntime range}
    B --> C[Sort by started_at]
    C --> D[_event_to_observation\nlookup correlation evidence]
    D --> E{Filter AFK/\nlocked}
    E --> F[_group_observations\nconsecutive same project]
    F --> G{Filter min\nduration 5min}
    G --> H[_build_suggestion]
    H --> I[TimeEntrySuggestion\nid, project, confidence,\nevidence_ids]
    
    subgraph Grouping["_group_observations logic"]
        F1[Start group] --> F2{Same project_id?}
        F2 -->|Yes| F3[Add to group]
        F2 -->|No| F4[Close group\nbuild suggestion]
        F3 --> F5{More obs?}
        F4 --> F5
        F5 -->|Yes| F2
        F5 -->|No| F6[Close final group]
        F6 --> H
        
        Note1[AFK/locked EXCLUDED\nbut do NOT break chain] -.-> F2
    end
    
    subgraph Building["_build_suggestion logic"]
        H1[Total minutes] --> H2{project_id\nfrequency}
        H2 --> H3[Most frequent\nnon-None project]
        H3 --> H4[Confidence = max\nCONFIRMED>HIGH>MED>LOW>UNASSIGNED]
        H4 --> H5[evidence_ids = all\nevent_ids in group]
        H5 --> H6[Deterministic ID\nhash(start + sorted evidence)]
        H6 --> I
    end
```

---

## Mermaid: Approval State Machine with Audit

```mermaid
stateDiagram-v2
    [*] --> PENDING_REVIEW: Suggestion created
    
    state PENDING_REVIEW {
        [*] --> DesignerReview
        DesignerReview --> Edit: edit_entry()
        DesignerReview --> Submit: submit_suggestion()\n[DESIGNER]
        DesignerReview --> RejectSelf: reject_suggestion()\n[DESIGNER]
        DesignerReview --> Split: split_suggestion()\n[DESIGNER]
        DesignerReview --> Merge: merge_suggestions()\n[DESIGNER]
    }
    
    SUBMITTED: Submitted for approval
    SUBMITTED --> APPROVED: approve_suggestion()\n[MANAGER]
    SUBMITTED --> REJECTED: reject_suggestion()\n[MANAGER]
    SUBMITTED --> RETURNED_FOR_CORRECTION: return_for_correction()\n[MANAGER]
    
    RETURNED_FOR_CORRECTION --> PENDING_REVIEW: Designer corrects & resubmits
    
    REJECTED --> PENDING_REVIEW: reset_to_pending()\n[DESIGNER]
    
    APPROVED --> BILLED: bill_entry()\n[MANAGER]\nEXPLICIT, SEPARATE
    
    state APPROVED {
        note right: approved_minutes recorded\nbilled_minutes = 0\nNOT auto-billed
    }
    
    state BILLED {
        note right: billed_minutes = X\n(0 < X ≤ approved × 2)\nRealization = X / approved
    }
    
    note right of PENDING_REVIEW
        Audit: suggestion_decisions
        action=submit/approve/reject/
        return_for_correction/split/merge
        actor=validated session
        company_scoped
    end note
    
    note right of SUBMITTED
        Creates TimeEntry
        state=SUBMITTED
        Audit: time_entry_audit
    end note
```