"""Financial management domain service for BIMSpend R1-07.

Provides project costing, budget consumption, financial reporting,
and forecasting built on approved timesheet data.

All monetary amounts use Decimal for authoritative calculations.
Never uses binary floating-point for financial amounts.

State separation:
  - Observed activity (activity_events) -> NOT financial
  - Attributed time (attributed_time) -> NOT financial
  - Approved time (time_entries state=approved) -> FINANCIAL source of truth
  - Billed time (time_entries state=billed) -> separate revenue concern

Security: All methods enforce company-scoped authorization and
role-based access control via current_auth.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Optional

from bimspend.db import Database
from bimspend.identity import Actor, Role, current_auth
from bimspend.models import (
    AdjustmentType,
    BudgetRevision,
    EmployeeBillingRate,
    EmployeeCostRate,
    FinancialAdjustment,
    FinancialSummary,
    ProjectBudget,
    TimeEntry,
    TimeEntryState,
)


class FinancialDomainError(Exception):
    """Raised when a financial domain operation fails."""


class CostRateService:
    """Service for managing employee cost and billing rates.

    Historical rate preservation: rates are never silently rewritten.
    New rates create new records with effective_from dates.
    Only managers and administrators can create/modify rates.
    """

    def __init__(self, db: Database):
        self.db = db

    # ------------------------------------------------------------------
    # Cost rates
    # ------------------------------------------------------------------

    def set_cost_rate(
        self,
        member_id: str,
        company_id: str,
        hourly_cost_aud: Decimal,
        effective_from: str,
        actor_id: str | None = None,
        effective_to: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> EmployeeCostRate:
        """Create a new employee cost rate record.

        Historical preservation: always creates a new record, never
        overwrites existing rates. The effective_to of prior rates
        is not automatically closed — callers manage date ranges.
        """
        actor = self._require_authenticated_actor(actor_id, [Role.MANAGER, Role.ADMINISTRATOR])
        if actor.company_id != company_id:
            raise PermissionError(
                f"Actor company {actor.company_id} does not match target company {company_id}."
            )
        if hourly_cost_aud < 0:
            raise ValueError("Hourly cost rate must be non-negative.")

        import secrets

        rate = EmployeeCostRate(
            id=f"ecr-{secrets.token_urlsafe(8)}",
            member_id=member_id,
            company_id=company_id,
            hourly_cost_aud=hourly_cost_aud,
            effective_from=effective_from,
            effective_to=effective_to,
            created_by=actor.id,
            created_at=datetime.now(timezone.utc).isoformat(),
            notes=notes,
        )
        self.db.upsert_employee_cost_rate(rate)

        self.db.record_financial_audit_event(
            actor_id=actor.id,
            actor_company_id=actor.company_id,
            action="set_cost_rate",
            entity_type="employee_cost_rate",
            entity_id=rate.id,
            previous_values=None,
            new_values={
                "member_id": member_id,
                "hourly_cost_aud": str(hourly_cost_aud),
                "effective_from": effective_from,
                "effective_to": effective_to,
            },
        )

        return rate

    def get_effective_cost_rate(
        self, member_id: str, company_id: str, at: str
    ) -> Optional[EmployeeCostRate]:
        """Get the cost rate effective for a member at a given timestamp."""
        return self.db.get_effective_employee_cost_rate(member_id, company_id, at)

    def list_cost_rates(
        self, member_id: Optional[str] = None, company_id: Optional[str] = None
    ) -> list[EmployeeCostRate]:
        return self.db.list_employee_cost_rates(member_id=member_id, company_id=company_id)

    # ------------------------------------------------------------------
    # Billing rates
    # ------------------------------------------------------------------

    def set_billing_rate(
        self,
        member_id: str,
        company_id: str,
        hourly_billing_aud: Decimal,
        effective_from: str,
        actor_id: str | None = None,
        effective_to: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> EmployeeBillingRate:
        """Create a new employee billing rate record."""
        actor = self._require_authenticated_actor(actor_id, [Role.MANAGER, Role.ADMINISTRATOR])
        if actor.company_id != company_id:
            raise PermissionError(
                f"Actor company {actor.company_id} does not match target company {company_id}."
            )
        if hourly_billing_aud < 0:
            raise ValueError("Hourly billing rate must be non-negative.")

        import secrets

        rate = EmployeeBillingRate(
            id=f"ebr-{secrets.token_urlsafe(8)}",
            member_id=member_id,
            company_id=company_id,
            hourly_billing_aud=hourly_billing_aud,
            effective_from=effective_from,
            effective_to=effective_to,
            created_by=actor.id,
            created_at=datetime.now(timezone.utc).isoformat(),
            notes=notes,
        )
        self.db.upsert_employee_billing_rate(rate)

        self.db.record_financial_audit_event(
            actor_id=actor.id,
            actor_company_id=actor.company_id,
            action="set_billing_rate",
            entity_type="employee_billing_rate",
            entity_id=rate.id,
            previous_values=None,
            new_values={
                "member_id": member_id,
                "hourly_billing_aud": str(hourly_billing_aud),
                "effective_from": effective_from,
                "effective_to": effective_to,
            },
        )

        return rate

    def get_effective_billing_rate(
        self, member_id: str, company_id: str, at: str
    ) -> Optional[EmployeeBillingRate]:
        """Get the billing rate effective for a member at a given timestamp."""
        return self.db.get_effective_employee_billing_rate(member_id, company_id, at)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_authenticated_actor(
        self, actor_id: Optional[str], allowed_roles: list[Role]
    ) -> Actor:
        actor = current_auth.actor
        if actor is None:
            raise PermissionError("No authenticated actor.")
        if actor_id is not None and actor.id != actor_id:
            raise PermissionError(
                f"Actor {actor.id} does not match requested actor_id {actor_id}."
            )
        if actor.role not in allowed_roles:
            raise PermissionError(
                f"Actor {actor.id} with role {actor.role.value} not authorized "
                f"for financial configuration (requires {[r.value for r in allowed_roles]})."
            )
        return actor


class BudgetService:
    """Service for managing project budgets and revisions.

    Original budget is preserved; current budget reflects revisions.
    All changes are auditable through budget_revisions table.
    Only managers and administrators can create/modify budgets.
    """

    def __init__(self, db: Database):
        self.db = db

    def create_budget(
        self,
        project_id: str,
        company_id: str,
        original_budget_aud: Decimal,
        effective_from: str,
        actor_id: str | None = None,
        budget_currency: str = "AUD",
        project_status: str = "active",
        budget_owner_id: Optional[str] = None,
        effective_to: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> ProjectBudget:
        """Create a new project budget.

        Original budget equals current budget on creation.
        """
        actor = self._require_authenticated_actor(actor_id, [Role.MANAGER, Role.ADMINISTRATOR])
        if actor.company_id != company_id:
            raise PermissionError(
                f"Actor company {actor.company_id} does not match target company {company_id}."
            )
        if original_budget_aud < 0:
            raise ValueError("Original budget must be non-negative.")

        import secrets

        budget = ProjectBudget(
            id=f"pb-{secrets.token_urlsafe(8)}",
            project_id=project_id,
            company_id=company_id,
            original_budget_aud=original_budget_aud,
            current_budget_aud=original_budget_aud,
            budget_currency=budget_currency,
            project_status=project_status,
            budget_owner_id=budget_owner_id,
            effective_from=effective_from,
            effective_to=effective_to,
            created_by=actor.id,
            created_at=datetime.now(timezone.utc).isoformat(),
            notes=notes,
        )
        self.db.upsert_project_budget(budget)

        self.db.record_financial_audit_event(
            actor_id=actor.id,
            actor_company_id=actor.company_id,
            action="create_budget",
            entity_type="project_budget",
            entity_id=budget.id,
            previous_values=None,
            new_values={
                "project_id": project_id,
                "original_budget_aud": str(original_budget_aud),
                "current_budget_aud": str(original_budget_aud),
                "currency": budget_currency,
            },
        )

        return budget

    def revise_budget(
        self,
        project_budget_id: str,
        new_budget_aud: Decimal,
        revision_reason: str,
        actor_id: str | None = None,
    ) -> BudgetRevision:
        """Revise a project budget, creating an auditable revision record.

        Previous current_budget_aud is preserved in the revision history.
        """
        actor = self._require_authenticated_actor(actor_id, [Role.MANAGER, Role.ADMINISTRATOR])
        if new_budget_aud < 0:
            raise ValueError("New budget must be non-negative.")

        budget = self.db.get_project_budget(project_budget_id)
        if budget is None:
            raise FinancialDomainError(f"Project budget {project_budget_id} not found.")
        if actor.company_id != budget.company_id:
            raise PermissionError(
                f"Actor company {actor.company_id} does not match budget company {budget.company_id}."
            )

        previous_budget = budget.current_budget_aud

        import secrets

        revision = BudgetRevision(
            id=f"br-{secrets.token_urlsafe(8)}",
            project_budget_id=project_budget_id,
            revision_number=len(self.db.list_budget_revisions(project_budget_id)) + 1,
            previous_budget_aud=previous_budget,
            new_budget_aud=new_budget_aud,
            revision_reason=revision_reason,
            created_by=actor.id,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.db.upsert_budget_revision(revision)

        # Update current budget
        budget.current_budget_aud = new_budget_aud
        self.db.upsert_project_budget(budget)

        self.db.record_financial_audit_event(
            actor_id=actor.id,
            actor_company_id=actor.company_id,
            action="revise_budget",
            entity_type="project_budget",
            entity_id=project_budget_id,
            previous_values={
                "current_budget_aud": str(previous_budget),
            },
            new_values={
                "current_budget_aud": str(new_budget_aud),
                "revision_reason": revision_reason,
            },
        )

        return revision

    def get_current_budget(
        self, project_id: str, company_id: str, at: Optional[str] = None
    ) -> Optional[ProjectBudget]:
        """Get the current budget for a project at a given timestamp."""
        return self.db.get_current_project_budget(project_id, company_id, at)

    def list_budgets(
        self, project_id: Optional[str] = None, company_id: Optional[str] = None
    ) -> list[ProjectBudget]:
        return self.db.list_project_budgets(
            project_id=project_id, company_id=company_id
        )

    def list_revisions(self, project_budget_id: str) -> list[BudgetRevision]:
        return self.db.list_budget_revisions(project_budget_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_authenticated_actor(
        self, actor_id: Optional[str], allowed_roles: list[Role]
    ) -> Actor:
        actor = current_auth.actor
        if actor is None:
            raise PermissionError("No authenticated actor.")
        if actor_id is not None and actor.id != actor_id:
            raise PermissionError(
                f"Actor {actor.id} does not match requested actor_id {actor_id}."
            )
        if actor.role not in allowed_roles:
            raise PermissionError(
                f"Actor {actor.id} with role {actor.role.value} not authorized "
                f"for budget management (requires {[r.value for r in allowed_roles]})."
            )
        return actor


class FinancialService:
    """Service for financial calculations on approved time entries.

    Calculates actual labour costs, budget consumption, forecasting,
    and profitability using approved time entries only.

    Never includes rejected, pending, or submitted time in calculations.
    """

    def __init__(self, db: Database):
        self.db = db

    # ------------------------------------------------------------------
    # Approved time financial eligibility
    # ------------------------------------------------------------------

    def get_approved_entries_for_project(
        self, project_id: str, company_id: str
    ) -> list[TimeEntry]:
        """Get all approved time entries for a project in a company.

        Only APPROVED state entries are included — never pending,
        submitted, rejected, or billed (unless billed is also approved).
        """
        entries = self.db.list_time_entries(state=TimeEntryState.APPROVED)
        return [
            e for e in entries
            if e.project_id == project_id and e.company_id == company_id
        ]

    def get_approved_entries_by_user(
        self, user_id: str, company_id: str
    ) -> list[TimeEntry]:
        """Get all approved time entries for a user in a company."""
        entries = self.db.list_time_entries(state=TimeEntryState.APPROVED)
        return [
            e for e in entries
            if e.user_id == user_id and e.company_id == company_id
        ]

    # ------------------------------------------------------------------
    # Actual labour cost calculation
    # ------------------------------------------------------------------

    def calculate_approved_labour_cost(
        self, project_id: str, company_id: str, at: Optional[str] = None
    ) -> Decimal:
        """Calculate total approved labour cost for a project.

        Formula: sum(approved_minutes / 60 * applicable_cost_rate)
        Uses the cost rate effective at each entry's created_at time.

        R1-07 requirement: only approved time contributes to cost.
        """
        if at is None:
            at = datetime.now(timezone.utc).isoformat()

        entries = self.get_approved_entries_for_project(project_id, company_id)
        total = Decimal("0")

        for entry in entries:
            cost_rate = self.db.get_effective_employee_cost_rate(
                entry.user_id, company_id, entry.created_at or at
            )
            rate = cost_rate.hourly_cost_aud if cost_rate else Decimal("0")
            # minutes / 60 * hourly rate, rounded to minor units (cents)
            entry_cost = (Decimal(str(entry.minutes)) / Decimal("60")) * rate
            total += entry_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return total

    def calculate_approved_labour_cost_by_user(
        self, project_id: str, company_id: str
    ) -> dict[str, Decimal]:
        """Calculate approved labour cost grouped by user."""
        entries = self.get_approved_entries_for_project(project_id, company_id)
        at = datetime.now(timezone.utc).isoformat()
        totals: dict[str, Decimal] = {}

        for entry in entries:
            cost_rate = self.db.get_effective_employee_cost_rate(
                entry.user_id, company_id, entry.created_at or at
            )
            rate = cost_rate.hourly_cost_aud if cost_rate else Decimal("0")
            entry_cost = (Decimal(str(entry.minutes)) / Decimal("60")) * rate
            entry_cost = entry_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            totals[entry.user_id] = totals.get(entry.user_id, Decimal("0")) + entry_cost

        return totals

    def calculate_billing_value(
        self, project_id: str, company_id: str, at: Optional[str] = None
    ) -> Decimal:
        """Calculate approved billing value (approved hours * billing rates).

        This is NOT invoiced revenue — it's the charge-out value of
        approved time. Use only for margin estimation.
        """
        if at is None:
            at = datetime.now(timezone.utc).isoformat()

        entries = self.get_approved_entries_for_project(project_id, company_id)
        total = Decimal("0")

        for entry in entries:
            billing_rate = self.db.get_effective_employee_billing_rate(
                entry.user_id, company_id, entry.created_at or at
            )
            rate = billing_rate.hourly_billing_aud if billing_rate else Decimal("0")
            entry_value = (Decimal(str(entry.minutes)) / Decimal("60")) * rate
            total += entry_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return total

    # ------------------------------------------------------------------
    # Budget consumption
    # ------------------------------------------------------------------

    def get_financial_summary(
        self, project_id: str, company_id: str
    ) -> FinancialSummary:
        """Compute a complete financial summary for a project.

        Returns all financial metrics: budget, actual cost, remaining,
        utilization, variance, billing value, gross margin.
        """
        project = self.db.get_project(project_id)
        if project is None:
            raise FinancialDomainError(f"Project {project_id} not found.")
        # Company scoping is enforced at the time_entry level, not project level.
        # Projects are shared resources; company isolation comes from entry data.

        budget = self.db.get_current_project_budget(project_id, company_id)
        if budget is None:
            # No budget configured — return zero-based summary
            return FinancialSummary(
                project_id=project_id,
                project_name=project.name,
                company_id=company_id,
                original_budget_aud=Decimal("0"),
                current_budget_aud=Decimal("0"),
                approved_labour_cost_aud=Decimal("0"),
                remaining_budget_aud=Decimal("0"),
                budget_utilization_percent=0.0,
                budget_variance_aud=Decimal("0"),
                is_over_budget=False,
                approved_hours=0.0,
                billing_value_aud=Decimal("0"),
                gross_margin_aud=Decimal("0"),
                last_updated=datetime.now(timezone.utc).isoformat(),
            )

        labour_cost = self.calculate_approved_labour_cost(project_id, company_id)
        billing_value = self.calculate_billing_value(project_id, company_id)
        approved_entries = self.get_approved_entries_for_project(project_id, company_id)
        approved_hours = sum(e.minutes for e in approved_entries) / 60.0

        current_budget = budget.current_budget_aud
        remaining = current_budget - labour_cost
        variance = labour_cost - current_budget  # positive = over budget
        utilization = float(labour_cost / current_budget * 100) if current_budget > 0 else 0.0
        is_over_budget = labour_cost > current_budget

        return FinancialSummary(
            project_id=project_id,
            project_name=project.name,
            company_id=company_id,
            original_budget_aud=budget.original_budget_aud,
            current_budget_aud=current_budget,
            approved_labour_cost_aud=labour_cost,
            remaining_budget_aud=remaining,
            budget_utilization_percent=round(utilization, 2),
            budget_variance_aud=variance.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            is_over_budget=is_over_budget,
            approved_hours=round(approved_hours, 2),
            billing_value_aud=billing_value,
            gross_margin_aud=(billing_value - labour_cost).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ),
            last_updated=datetime.now(timezone.utc).isoformat(),
        )

    def get_all_financial_summaries(self, company_id: str) -> list[FinancialSummary]:
        """Get financial summaries for all projects in a company."""
        projects = [p for p in self.db.list_projects()
                    if p.company_id == company_id]
        return [self.get_financial_summary(p.id, company_id) for p in projects]

    # ------------------------------------------------------------------
    # Forecasting (deterministic, no AI)
    # ------------------------------------------------------------------

    def forecast_cost_at_completion(
        self, project_id: str, company_id: str
    ) -> dict[str, Decimal]:
        """Deterministic forecast of cost at completion.

        Methodology:
          - actual_cost = approved labour cost to date
          - remaining_budget = current budget - actual cost
          - burn_rate = actual cost / approved hours (cost per hour)
          - If burn_rate > 0 and remaining_budget > 0:
              forecast_remaining_hours = remaining_budget / burn_rate
              forecast_cost_at_completion = actual_cost + remaining_budget
          - Otherwise: forecast = actual_cost

        Returns actuals vs forecast clearly distinguished.
        """
        summary = self.get_financial_summary(project_id, company_id)
        actual_cost = summary.approved_labour_cost_aud
        remaining_budget = summary.remaining_budget_aud
        approved_hours = Decimal(str(summary.approved_hours))

        if approved_hours > 0 and remaining_budget > 0:
            burn_rate = actual_cost / approved_hours
            # Forecast: actual cost + remaining budget consumed at same rate
            forecast_cost = actual_cost + remaining_budget
        else:
            burn_rate = Decimal("0")
            forecast_cost = actual_cost

        forecast_variance = forecast_cost - summary.current_budget_aud

        return {
            "actual_cost_to_date": actual_cost,
            "remaining_budget": remaining_budget,
            "burn_rate_per_hour": burn_rate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            "forecast_cost_at_completion": forecast_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            "forecast_budget_variance": forecast_variance.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            "methodology": "linear_burn_rate",
        }

    # ------------------------------------------------------------------
    # Financial adjustments
    # ------------------------------------------------------------------

    def create_adjustment(
        self,
        project_id: str,
        company_id: str,
        adjustment_type: AdjustmentType,
        amount_aud: Decimal,
        adjustment_date: str,
        actor_id: str | None = None,
        entry_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> FinancialAdjustment:
        """Create a manual financial adjustment.

        Manager/administrator only. Adjustments are auditable and
        traceable to the actor and company.
        """
        actor = self._require_authenticated_actor(actor_id, [Role.MANAGER, Role.ADMINISTRATOR])
        if actor.company_id != company_id:
            raise PermissionError(
                f"Actor company {actor.company_id} does not match target company {company_id}."
            )
        if amount_aud < 0:
            raise ValueError("Adjustment amount must be non-negative.")

        # Verify project belongs to company
        project = self.db.get_project(project_id)
        if project is None:
            raise FinancialDomainError(f"Project {project_id} not found.")
        if project.company_id is not None and project.company_id != company_id:
            raise PermissionError(
                f"Project {project_id} is not in company {company_id}."
            )

        import secrets

        adj = FinancialAdjustment(
            id=f"fa-{secrets.token_urlsafe(8)}",
            entry_id=entry_id,
            project_id=project_id,
            company_id=company_id,
            adjustment_type=adjustment_type,
            amount_aud=amount_aud,
            adjustment_date=adjustment_date,
            created_by=actor.id,
            created_at=datetime.now(timezone.utc).isoformat(),
            notes=notes,
        )
        self.db.upsert_financial_adjustment(adj)

        self.db.record_financial_audit_event(
            actor_id=actor.id,
            actor_company_id=actor.company_id,
            action="create_financial_adjustment",
            entity_type="financial_adjustment",
            entity_id=adj.id,
            previous_values=None,
            new_values={
                "project_id": project_id,
                "adjustment_type": adjustment_type.value,
                "amount_aud": str(amount_aud),
            },
        )

        return adj

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_authenticated_actor(
        self, actor_id: Optional[str], allowed_roles: list[Role]
    ) -> Actor:
        actor = current_auth.actor
        if actor is None:
            raise PermissionError("No authenticated actor.")
        if actor_id is not None and actor.id != actor_id:
            raise PermissionError(
                f"Actor {actor.id} does not match requested actor_id {actor_id}."
            )
        if actor.role not in allowed_roles:
            raise PermissionError(
                f"Actor {actor.id} with role {actor.role.value} not authorized "
                f"for financial operations (requires {[r.value for r in allowed_roles]})."
            )
        return actor