# Commercial data and estimation hypotheses

## Data received in conversation — not committed
1. `Item price list.xlsx` — internal commercial rate card and unit-based service pricing.
2. `Maria Angelica Sales by Product_Service Detail.xlsx` — historical sales/invoice report (2025-07 through 2026-06), quantities and charged rates.

The user confirmed `Quantity` in the sales report is **hours billed to clients**, not a reliable measure of actual hours worked. Sometimes actual effort exceeds billed hours, and the company discounts hours subjectively. Do not use invoice quantity as measured labor time.

## Privacy and intellectual property
These spreadsheets are not included. Do not reproduce named staff, clients, invoices, exact commercial rates or sensitive project details in public GitHub. Only use anonymized/synthetic datasets unless permission and a private storage plan are established.

## Definitions
- `actual_hours`: measured or verified work effort (may require correction for idle/other apps).
- `billed_hours`: invoiced quantity, possibly discounted.
- `standard_charge_rate`: published hourly price to client.
- `internal_loaded_cost_rate`: true employer cost per hour including relevant overhead, distinct from charge-out rate.
- `revenue`: actual invoiced value (excluding GST if comparing like-for-like).
- `realization = billed_hours / actual_hours` (where comparable).
- `effective_rate = revenue / actual_hours`.
- `labor_cost = actual_hours * loaded_cost_rate`.
- `contribution_after_labor = revenue - labor_cost` (not net profit).
- `quote_price = estimated_cost / (1 - target_gross_margin)` only when the cost base includes all intended cost categories.

## Synthetic example A — subjective billing discount
Actual hours 12, billed hours 8, client rate A$110/h → invoice A$880, equivalent standard value A$1,320, unbilled reference A$440, realization 66.7%, effective revenue per actual hour A$73.33. **Not actual employee data.**

## Synthetic example B — project financial dashboard
Fee A$18,000, actual hours 160, internal cost A$65/h → labor cost A$10,400, remaining after labor A$7,600; excludes all other costs.

## Synthetic example C — quoting calculator
12 floors × 18 assumed hours/floor = 216 baseline hours; 15% contingency → 248.4 hours; A$80 loaded hourly cost → A$19,872 labor cost; at 30% target margin → A$28,388.57 quote on labor-only base. **Not a validated benchmark.**

## Historical comparison caution
Building type, levels, apartment count, head count, repeated floor plates, model maturity, coordination complexity, LOD, scope, variations and project phase affect effort. Models with equal sprinkler count can require different time. Historical estimates should show uncertainty and comparable cases.
