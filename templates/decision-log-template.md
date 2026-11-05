# Decision log entry template

Copy this template for each new decision entry in `docs/decisions/decision-log.md`.

```
YYYY-MM-DD | <Idea | Hypothesis | Tested | Validated | Rejected | Deferred | Approved> | <Topic> | <Evidence> | <Decision / Next action>
```

Rules:
- Date in ISO format (YYYY-MM-DD).
- Status must be one of: IDEA, UNDER INVESTIGATION, VALIDATED, REJECTED, DEFERRED, APPROVED.
- APPROVED only when the user explicitly approved the decision.
- Evidence must reference something real (user statement, document, observation, test result) — never invented.
- Link to supporting docs where relevant.

## Example

```
2026-11-05 | Tested | Billing semantics | User clarification | Quantity in sales report is hours billed, not actual time.
```
