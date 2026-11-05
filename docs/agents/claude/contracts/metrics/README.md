# BIMSpend Integration Contracts — Metric Separation (Observed / Attributed / Approved / Billed)

Version: 1.0.0
Status: Draft — Implementation Checkpoint 1
Branch: `build/claude-integration-contracts`

## Core Principle

**Never collapse these four metrics.** Each serves a distinct purpose and must be stored, reported, and audited separately.

```
┌─────────────────────────────────────────────────────────────────────┐
│  OBSERVED ACTIVITY                                                    │
│  ─────────────────────────────────────────────────────────────────  │
│  Source: ActivityWatch (window focus, AFK) + Revit Connector         │
│  Unit: Seconds                                                       │
│  Meaning: "User had this window in foreground"                       │
│  Uncertainty: HIGH — includes meetings, email, idle, multitasking   │
│  Privacy: Raw window titles NEVER leave adapter                      │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼ Correlation + Filtering
┌─────────────────────────────────────────────────────────────────────┐
│  ATTRIBUTED TIME                                                     │
│  ─────────────────────────────────────────────────────────────────  │
│  Source: Windows Adapter (correlation engine)                        │
│  Unit: Minutes (rounded)                                             │
│  Meaning: "User likely worked on Project X"                          │
│  Confidence: 0.0–1.0 (explicit in record)                           │
│  Review: Designer can see, edit, dispute before approval            │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼ Human Review + Approval
┌─────────────────────────────────────────────────────────────────────┐
│  APPROVED TIME                                                       │
│  ─────────────────────────────────────────────────────────────────  │
│  Source: Miru TimesheetEntry (review_status = 'approved')            │
│  Unit: Minutes                                                       │
│  Meaning: "Manager/designer confirmed this time for Project X"      │
│  Authority: Explicit human decision                                  │
│  Audit: Full history in Miru `audited` trail                        │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼ Invoicing Decision
┌─────────────────────────────────────────────────────────────────────┐
│  BILLED HOURS                                                        │
│  ─────────────────────────────────────────────────────────────────  │
│  Source: Miru Invoice / TimesheetEntry (bill_status = 'billed')     │
│  Unit: Hours (decimal, typically 0.25 increments)                   │
│  Meaning: "Client invoiced for this quantity"                        │
│  Policy: May be LESS than approved (discounts, write-offs)          │
│  NEVER: Auto-derived from observed/attributed                       │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Model

### Observed Activity (Adapter Local Only)

```json
{
  "metric_type": "observed",
  "interval": { "start_utc": "...", "end_utc": "...", "duration_seconds": 1800 },
  "breakdown": {
    "revit_foreground_seconds": 1450,
    "other_app_seconds": 170,
    "afk_seconds": 120,
    "idle_seconds": 60
  },
  "source_events": ["uuid1", "uuid2"],
  "privacy_filtered": true
}
```

**Storage:** Adapter local DB only. Never transmitted to Miru.

### Attributed Time (Adapter → Miru Draft)

```json
{
  "metric_type": "attributed",
  "timesheet_entry_draft": {
    "external_run_id": "...",
    "external_session_id": "...",
    "duration_minutes": 25,
    "work_date": "2026-11-05",
    "project_id": "uuid-v4",
    "source": "automation",
    "source_metadata": {
      "correlation_confidence": 0.92,
      "observed_seconds": 1620,
      "active_seconds": 1500,
      "afk_seconds": 120,
      "model_identity": { ... },
      "attribution_factors": { ... }
    },
    "proof_metadata": { ... }
  }
}
```

**Storage:** Miru `TimesheetEntry` with `review_status = 'pending_review'`, `source = 'automation'`.

### Approved Time (Miru After Review)

```json
{
  "metric_type": "approved",
  "timesheet_entry": {
    "id": "uuid-v4",
    "duration_minutes": 25,
    "work_date": "2026-11-05",
    "project_id": "uuid-v4",
    "user_id": "uuid-v4",
    "review_status": "approved",
    "approved_by": "uuid-v4",
    "approved_utc": "2026-11-05T14:00:00Z",
    "source": "automation",
    "source_metadata": { ... }  // Preserved from draft
  }
}
```

**Storage:** Miru `TimesheetEntry` with `review_status = 'approved'`.

### Billed Hours (Miru Invoice)

```json
{
  "metric_type": "billed",
  "invoice_line_item": {
    "id": "uuid-v4",
    "invoice_id": "uuid-v4",
    "quantity_hours": 2.0,  // May differ from approved minutes!
    "rate_per_hour": 110.00,
    "amount": 220.00,
    "timesheet_entries": ["uuid-v4"],  // Links to approved entries
    "description": "Project Alpha - Design Development"
  }
}
```

**Storage:** Miru `InvoiceLineItem` linked to `TimesheetEntry` via `invoice_line_item_time_entries`.

## Transformation Rules

### Observed → Attributed

| Rule | Description |
|------|-------------|
| AFK Exclusion | `afk_seconds` subtracted from `observed_seconds` |
| Idle Exclusion | `idle_seconds` subtracted (configurable threshold) |
| Confidence Weighting | `attributed_minutes = round(active_seconds / 60 * confidence)` |
| Minimum Threshold | Intervals < 5 min attributed time → discarded (configurable) |
| Confidence Floor | Confidence < 0.5 → not submitted, queued locally only |

### Attributed → Approved

| Rule | Description |
|------|-------------|
| Designer Review | Designer sees draft, can edit duration, project, note |
| Manager Approval | Manager approves/rejects; audit trail recorded |
| No Auto-Approval | Automated entries NEVER auto-approve |
| Edit Preserves Metadata | Edits keep `source_metadata` for audit |

### Approved → Billed

| Rule | Description |
|------|-------------|
| Explicit Invoicing | Billed quantity set at invoice creation |
| May Be Less | `billed_hours ≤ approved_hours` (discounts, scope limits) |
| Never More | `billed_hours > approved_hours` → validation error |
| Traceability | Every billed hour links to approved timesheet entries |

## Realization Metrics (Derived, Read-Only)

```json
{
  "project_id": "uuid-v4",
  "period": "2026-11",
  "realization": {
    "observed_hours": 180.5,
    "attributed_hours": 142.0,
    "approved_hours": 138.5,
    "billed_hours": 120.0,
    "attribution_rate": 0.787,   // attributed / observed
    "approval_rate": 0.975,      // approved / attributed
    "billing_rate": 0.866,       // billed / approved
    "overall_realization": 0.665 // billed / observed
  },
  "financial": {
    "standard_charge_rate": 110.00,
    "internal_loaded_cost_rate": 65.00,  // Separate model!
    "revenue": 13200.00,
    "labor_cost": 8997.50,
    "contribution_after_labor": 4202.50
  }
}
```

**Critical:** `internal_loaded_cost_rate` is a **separate protected model** in BIMSpend. It is NOT `ProfitabilityBillingRate` (which is a charge-out rate). Loaded cost includes employer overhead, benefits, etc.

## Reporting Requirements

### Designer View (Own Data Only)

| Metric | Visible? | Source |
|--------|----------|--------|
| Observed activity (own) | YES (local only) | Adapter |
| Attributed drafts (own) | YES | Miru `pending_review` |
| Approved time (own) | YES | Miru `approved` |
| Billed hours (own project) | NO | Finance only |

### Manager View (Team Data)

| Metric | Visible? | Source |
|--------|----------|--------|
| Attributed drafts (team) | YES | Miru `pending_review` |
| Approved time (team) | YES | Miru `approved` |
| Billed hours (team projects) | YES | Miru `Invoice` |
| Realization reports | YES | Derived |

### Finance View (All Data)

| Metric | Visible? | Source |
|--------|----------|--------|
| All metrics | YES | Miru + BIMSpend |
| Loaded cost rates | YES (restricted) | BIMSpend protected model |
| Contribution margins | YES | Derived |

## Enforcement

### Adapter Level

- Never send raw `observed` metrics to Miru
- Always include `source_metadata` with confidence, observed_seconds, attribution_factors
- Never submit `attributed` with confidence < 0.5

### Miru Level (Policy)

- `TimesheetEntryPolicy`: automation entries default `pending_review`
- `TimesheetEntryPolicy#update`: cannot change `review_status` to `approved` without privileged role
- `InvoiceLineItem` validation: `quantity_hours` ≤ sum of linked approved entries

### Database Constraints

```sql
-- Miru migrations needed
ALTER TABLE timesheet_entries ADD CONSTRAINT chk_automation_pending
  CHECK (source != 'automation' OR review_status = 'pending_review');

ALTER TABLE invoice_line_items ADD CONSTRAINT chk_billed_not_exceed_approved
  CHECK (quantity_hours <= (
    SELECT COALESCE(SUM(duration_minutes)/60.0, 0)
    FROM invoice_line_item_time_entries ilite
    JOIN timesheet_entries te ON te.id = ilite.timesheet_entry_id
    WHERE ilite.invoice_line_item_id = invoice_line_items.id
      AND te.review_status = 'approved'
  ));
```

## Testing Requirements

### Unit Tests

- [ ] Observed → attributed calculation (AFK, idle, confidence, threshold)
- [ ] Attributed → approved: metadata preservation
- [ ] Approved → billed: validation (billed ≤ approved)
- [ ] Realization rate calculations
- [ ] Loaded cost vs charge rate separation

### Integration Tests

- [ ] Full flow: AW event → attributed draft → approval → invoice → realization
- [ ] Discount scenario: approved 10h, billed 8h → realization 80%
- [ ] Rejection: attributed draft rejected → no approved, no billed
- [ ] Edit during review: designer edits duration → metadata preserved

### Audit Tests

- [ ] No automated entry reaches `approved` without human action
- [ ] No billed hour exists without linked approved entry
- [ ] `source_metadata` immutable after submission
- [ ] Loaded cost rate never equals billing rate without explicit config