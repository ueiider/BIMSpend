# Synthetic example calculations — financial model concepts

**All figures in this document are synthetic illustrations. They are not actual company data, employee records, invoices, or commercial rates.**

## Core definitions

| Term | Definition |
|---|---|
| actual_hours | Measured or verified work effort (may require correction for idle or other-application use). |
| billed_hours | Invoiced quantity to the client; possibly discounted. Not necessarily equal to actual hours. |
| standard_charge_rate | Published hourly price charged to the client. |
| internal_loaded_cost_rate | True employer cost per hour including relevant overhead; distinct from charge-out rate. |
| revenue | Actual invoiced value (excluding GST when comparing like-for-like). |
| realization | billed_hours / actual_hours (where comparable). |
| effective_rate | revenue / actual_hours. |
| labor_cost | actual_hours × loaded_cost_rate. |
| contribution_after_labor | revenue − labor_cost (not net profit; excludes all other costs). |
| quote_price | estimated_cost / (1 − target_gross_margin), only when the cost base includes all intended cost categories. |

## Example A — Subjective billing discount

A designer works 12 actual hours on a task. The company invoices the client for 8 hours at a standard charge rate of A$110/h.

| Metric | Value | Basis |
|---|---|---|
| actual_hours | 12 h | Synthetic |
| billed_hours | 8 h | Synthetic |
| standard_charge_rate | A$110/h | Synthetic |
| revenue (invoice) | A$880 | 8 × 110 |
| standard value of actual time | A$1,320 | 12 × 110 |
| unbilled reference value | A$440 | 1,320 − 880 |
| realization | 66.7% | 8 / 12 |
| effective_rate | A$73.33/h | 880 / 12 |

Interpretation: the 4-hour / A$440 difference is unbilled reference value; it is not automatically an accounting loss. Actual hours and billed hours are distinct metrics.

## Example B — Project financial dashboard

| Metric | Value | Basis |
|---|---|---|
| fee | A$18,000 | Synthetic |
| actual_hours | 160 h | Synthetic |
| internal_hourly_cost | A$65/h | Synthetic |
| labor_cost | A$10,400 | 160 × 65 |
| remaining_after_labor | A$7,600 | 18,000 − 10,400 |

Excludes all other costs (overhead, software, subconsultants, risk). Not net profit.

## Example C — Quoting calculator

| Metric | Value | Basis |
|---|---|---|
| floors | 12 | Synthetic |
| assumed_hours_per_floor | 18 h | Synthetic |
| baseline_hours | 216 h | 12 × 18 |
| contingency | 15% | Synthetic |
| hours_with_contingency | 248.4 h | 216 × 1.15 |
| loaded_hourly_cost | A$80/h | Synthetic |
| labor_cost | A$19,872 | 248.4 × 80 |
| target_margin | 30% | Synthetic |
| quote_on_labor_only_base | A$28,388.57 | 19,872 / (1 − 0.30) |

**Not a validated benchmark.** Building type, levels, apartment count, head count, repeated floor plates, model maturity, coordination complexity, LOD, scope, variations, and project phase all affect effort. Models with equal deliverable counts can require different time. Historical estimates should show uncertainty and comparable cases.

## Source of synthetic data

The scenario parameters above correspond to `examples/synthetic-data/illustrative-scenarios.csv`, which is machine-readable and explicitly labelled `Synthetic`.

## Caution

Do not assume invoice quantities represent actual working hours. Do not reverse-engineer confidential commercial rates from these examples. Use these formulas only as discussion aids for the pricing hypothesis, not as an approved pricing model.
