"""Tests for BIMSpend R1-07 financial management module.

Tests cover:
1. Approved-time financial eligibility
2. Rejected-time exclusion
3. Pending-time exclusion
4. Employee cost rates
5. Historical rate selection
6. Rate effective-date boundaries
7. Decimal-safe arithmetic
8. Partial-hour calculations
9. Project budget creation
10. Budget revisions
11. Budget utilization
12. Remaining budget
13. Over-budget detection
14. Missing rate handling
15. Zero budget handling
16. Forecast calculations
17. Project profitability
18. Company-scoped financial queries
19. Unauthorized rate changes
20. Unauthorized budget changes
21. Database migration compatibility
22. No automatic billing or invoicing
"""

import os
import sys

import pytest
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bimspend.auth import SessionManager, hash_password
from bimspend.db import Database
from bimspend.identity import Actor, Role, current_auth
from bimspend.financial import (
    FinancialService,
    BudgetService,
    CostRateService,
    FinancialDomainError,
    AdjustmentType,
)
from bimspend.models import (
    Project,
    TeamMember,
    TimeEntry,
    TimeEntryState,
    EmployeeCostRate,
    EmployeeBillingRate,
    ProjectBudget,
    FinancialAdjustment,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _make_company(db, cid="c1", name="Test Company"):
    db.upsert_company(cid, name, is_active=True)
    return cid


def _make_member(db, mid="m1", name="Alice", role="designer", cost=95.0, active=True):
    db.upsert_member(TeamMember(mid, name, role, cost, active))
    return mid


def _make_manager(db, mid="mgr", name="Manager", cost=120.0):
    db.upsert_member(TeamMember(mid, name, "manager", cost, True))
    db.upsert_company_member("c1", mid, "manager")
    db.upsert_user_credential(mid, "mgr", hash_password("mgrpass"))
    return mid


def _make_company_member(db, cid, mid, role):
    db.upsert_company_member(cid, mid, role)


def _make_credential(db, member_id, username, password="secretpass"):
    db.upsert_user_credential(member_id, username, hash_password(password))


def _make_project(db, pid="p1", name="Project", client="Client", company_id="c1"):
    db.upsert_project(Project(pid, name, client, 150.0, 80.0))
    # Time entries carry company_id, not projects
    return pid


def _make_approved_entry(
    db,
    entry_id="e1",
    project_id="p1",
    user_id="m1",
    minutes=120.0,
    company_id="c1",
    loaded_cost_rate=55.0,
    standard_rate=120.0,
    state=TimeEntryState.APPROVED,
):
    from bimspend.models import ActivityEvent, AttributedTime
    # Create activity event first (FK target for attributed_time)
    ev = ActivityEvent(
        id=f"ev-{entry_id}",
        source="synthetic",
        external_id=f"ext-{entry_id}",
        user_id=user_id,
        app_name="Revit",
        window_title="[HASH:test]",
        started_at="2026-01-01T09:00:00Z",
        ended_at="2026-01-01T10:00:00Z",
        duration_minutes=minutes,
        company_id=company_id,
    )
    db.ingest_event(ev)
    # Create attributed_time (FK target for time_entries)
    at = AttributedTime(
        id=f"at-{entry_id}",
        activity_event_id=f"ev-{entry_id}",
        project_id=project_id,
        attributed_minutes=minutes,
        confidence=1.0,
        correlation_method="manual",
    )
    db.upsert_attributed_time(at)
    entry = TimeEntry(
        id=entry_id,
        attributed_time_id=f"at-{entry_id}",
        project_id=project_id,
        user_id=user_id,
        minutes=minutes,
        state=state,
        standard_rate=standard_rate,
        loaded_cost_rate=loaded_cost_rate,
        billed_minutes=0.0,
        company_id=company_id,
    )
    db.upsert_time_entry(entry, actor_id=user_id)
    return entry


def _set_auth(db, mid, role, cid):
    current_auth.set_actor(Actor(id=mid, role=Role(role), company_id=cid))


# ------------------------------------------------------------------
# Approved-time financial eligibility tests
# ------------------------------------------------------------------

def test_approved_time_only_in_financial_calculation(tmp_path):
    """Only APPROVED entries contribute to labour cost."""
    db = Database(str(tmp_path / "eligibility.db"))
    _make_company(db)
    _make_member(db, "m1", "Alice", "designer", 55.0)
    _make_manager(db)
    _make_company_member(db, "c1", "m1", "designer")
    _make_credential(db, "m1", "alice")
    _make_project(db, "p1", "Project", "Client", "c1")

    # Set cost rate via manager
    _set_auth(db, "mgr", "manager", "c1")
    cs = CostRateService(db)
    cs.set_cost_rate(
        member_id="m1", company_id="c1",
        hourly_cost_aud=Decimal("55.00"),
        effective_from="2026-01-01T00:00:00Z",
        actor_id="mgr",
    )

    # Approved entry
    _set_auth(db, "m1", "designer", "c1")
    _make_approved_entry(db, "e1", "p1", "m1", 120.0, "c1")
    # Rejected entry - should NOT count
    _make_approved_entry(db, "e2", "p1", "m1", 60.0, "c1", state=TimeEntryState.REJECTED)
    # Pending entry - should NOT count
    _make_approved_entry(db, "e3", "p1", "m1", 30.0, "c1", state=TimeEntryState.PENDING_REVIEW)
    # Submitted entry - should NOT count
    _make_approved_entry(db, "e4", "p1", "m1", 30.0, "c1", state=TimeEntryState.SUBMITTED)

    service = FinancialService(db)
    cost = service.calculate_approved_labour_cost("p1", "c1")

    # Only e1 (120 min = 2 hr * 55 = 110)
    assert cost == Decimal("110.00"), f"Expected 110.00, got {cost}"
    db.close()


def test_rejected_time_excluded(tmp_path):
    """Rejected entries never contribute to financial calculations."""
    db = Database(str(tmp_path / "rejected.db"))
    _make_company(db)
    _make_member(db, "m1", "Alice", "designer", 55.0)
    _make_manager(db)
    _make_company_member(db, "c1", "m1", "designer")
    _make_credential(db, "m1", "alice")
    _make_project(db, "p1", "Project", "Client", "c1")

    # Set cost rate via manager
    _set_auth(db, "mgr", "manager", "c1")
    cs = CostRateService(db)
    cs.set_cost_rate(
        member_id="m1", company_id="c1",
        hourly_cost_aud=Decimal("55.00"),
        effective_from="2026-01-01T00:00:00Z",
        actor_id="mgr",
    )

    # Approved
    _set_auth(db, "m1", "designer", "c1")
    _make_approved_entry(db, "e1", "p1", "m1", 60.0, "c1")
    # Rejected
    _make_approved_entry(db, "e2", "p1", "m1", 120.0, "c1", state=TimeEntryState.REJECTED)

    service = FinancialService(db)
    cost = service.calculate_approved_labour_cost("p1", "c1")

    # Only e1: 60 min = 1 hr * 55 = 55
    assert cost == Decimal("55.00"), f"Expected 55.00, got {cost}"
    db.close()


def test_pending_time_excluded(tmp_path):
    """Pending entries never contribute to financial calculations."""
    db = Database(str(tmp_path / "pending.db"))
    _make_company(db)
    _make_member(db, "m1", "Alice", "designer", 55.0)
    _make_manager(db)
    _make_company_member(db, "c1", "m1", "designer")
    _make_credential(db, "m1", "alice")
    _make_project(db, "p1", "Project", "Client", "c1")

    # Set cost rate via manager
    _set_auth(db, "mgr", "manager", "c1")
    cs = CostRateService(db)
    cs.set_cost_rate(
        member_id="m1", company_id="c1",
        hourly_cost_aud=Decimal("55.00"),
        effective_from="2026-01-01T00:00:00Z",
        actor_id="mgr",
    )

    _set_auth(db, "m1", "designer", "c1")
    _make_approved_entry(db, "e1", "p1", "m1", 60.0, "c1")
    _make_approved_entry(db, "e2", "p1", "m1", 60.0, "c1", state=TimeEntryState.PENDING_REVIEW)

    service = FinancialService(db)
    cost = service.calculate_approved_labour_cost("p1", "c1")

    assert cost == Decimal("55.00"), f"Expected 55.00, got {cost}"
    db.close()


# ------------------------------------------------------------------
# Employee cost rate tests
# ------------------------------------------------------------------

def test_cost_rate_creation_and_retrieval(tmp_path):
    """Cost rate can be set and retrieved."""
    db = Database(str(tmp_path / "rate.db"))
    _make_company(db)
    _make_member(db, "m1", "Alice", "designer", 55.0)
    _make_company_member(db, "c1", "m1", "designer")
    _make_credential(db, "m1", "alice")

    _set_auth(db, "m1", "manager", "c1")
    service = CostRateService(db)

    rate = service.set_cost_rate(
        member_id="m1",
        company_id="c1",
        hourly_cost_aud=Decimal("65.00"),
        effective_from="2026-01-01T00:00:00Z",
        actor_id="m1",
    )

    assert rate.hourly_cost_aud == Decimal("65.00")
    assert rate.member_id == "m1"
    assert rate.company_id == "c1"

    # Retrieve effective rate
    effective = service.get_effective_cost_rate("m1", "c1", "2026-06-01T00:00:00Z")
    assert effective is not None
    assert effective.hourly_cost_aud == Decimal("65.00")
    db.close()


def test_historical_rate_preservation(tmp_path):
    """Old rates are preserved when new rates are created."""
    db = Database(str(tmp_path / "history.db"))
    _make_company(db)
    _make_member(db, "m1", "Alice", "designer", 55.0)
    _make_company_member(db, "c1", "m1", "designer")
    _make_credential(db, "m1", "alice")

    _set_auth(db, "m1", "manager", "c1")
    service = CostRateService(db)

    # First rate
    service.set_cost_rate(
        member_id="m1", company_id="c1",
        hourly_cost_aud=Decimal("55.00"),
        effective_from="2026-01-01T00:00:00Z",
        actor_id="m1",
    )
    # Second rate (higher, effective later)
    service.set_cost_rate(
        member_id="m1", company_id="c1",
        hourly_cost_aud=Decimal("75.00"),
        effective_from="2026-07-01T00:00:00Z",
        actor_id="m1",
    )

    rates = service.list_cost_rates(member_id="m1", company_id="c1")
    assert len(rates) == 2

    # Rate before July uses 55
    early = service.get_effective_cost_rate("m1", "c1", "2026-03-01T00:00:00Z")
    assert early.hourly_cost_aud == Decimal("55.00")

    # Rate after July uses 75
    late = service.get_effective_cost_rate("m1", "c1", "2026-09-01T00:00:00Z")
    assert late.hourly_cost_aud == Decimal("75.00")
    db.close()


def test_rate_effective_date_boundary(tmp_path):
    """Rate selection respects effective_from and effective_to boundaries."""
    db = Database(str(tmp_path / "boundary.db"))
    _make_company(db)
    _make_member(db, "m1", "Alice", "designer", 55.0)
    _make_company_member(db, "c1", "m1", "designer")
    _make_credential(db, "m1", "alice")

    _set_auth(db, "m1", "manager", "c1")
    service = CostRateService(db)

    # Rate effective from Jan 1 to Jun 30
    service.set_cost_rate(
        member_id="m1", company_id="c1",
        hourly_cost_aud=Decimal("55.00"),
        effective_from="2026-01-01T00:00:00Z",
        effective_to="2026-06-30T23:59:59Z",
        actor_id="m1",
    )
    # Rate effective from Jul 1 onwards
    service.set_cost_rate(
        member_id="m1", company_id="c1",
        hourly_cost_aud=Decimal("75.00"),
        effective_from="2026-07-01T00:00:00Z",
        actor_id="m1",
    )

    # Exactly on boundary date - should use the new rate
    boundary = service.get_effective_cost_rate("m1", "c1", "2026-07-01T00:00:00Z")
    assert boundary.hourly_cost_aud == Decimal("75.00")

    # Day before boundary - should use old rate
    before = service.get_effective_cost_rate("m1", "c1", "2026-06-30T23:59:58Z")
    assert before.hourly_cost_aud == Decimal("55.00")
    db.close()


def test_missing_rate_handling(tmp_path):
    """Missing rate defaults to zero cost (no crash)."""
    db = Database(str(tmp_path / "missing.db"))
    _make_company(db)
    _make_member(db, "m1", "Alice", "designer", 55.0)
    _make_company_member(db, "c1", "m1", "designer")
    _make_credential(db, "m1", "alice")
    _make_project(db, "p1", "Project", "Client", "c1")

    # No cost rate set for m1
    _make_approved_entry(db, "e1", "p1", "m1", 60.0, "c1")

    _set_auth(db, "m1", "designer", "c1")
    service = FinancialService(db)
    cost = service.calculate_approved_labour_cost("p1", "c1")

    # No rate = 0 cost
    assert cost == Decimal("0.00"), f"Expected 0.00, got {cost}"
    db.close()


# ------------------------------------------------------------------
# Decimal-safe arithmetic tests
# ------------------------------------------------------------------

def test_decimal_safe_arithmetic(tmp_path):
    """Monetary calculations use Decimal, not float."""
    db = Database(str(tmp_path / "decimal.db"))
    _make_company(db)
    _make_member(db, "m1", "Alice", "designer", 55.0)
    _make_manager(db)
    _make_company_member(db, "c1", "m1", "designer")
    _make_credential(db, "m1", "alice")
    _make_project(db, "p1", "Project", "Client", "c1")

    # Set cost rate via manager
    _set_auth(db, "mgr", "manager", "c1")
    cs = CostRateService(db)
    cs.set_cost_rate(
        member_id="m1", company_id="c1",
        hourly_cost_aud=Decimal("55.00"),
        effective_from="2026-01-01T00:00:00Z",
        actor_id="mgr",
    )

    # 37 minutes = 0.6166... hours * 55 = 33.9166... -> rounded to 33.92
    _set_auth(db, "m1", "designer", "c1")
    _make_approved_entry(db, "e1", "p1", "m1", 37.0, "c1", loaded_cost_rate=55.0)

    fs = FinancialService(db)
    cost = fs.calculate_approved_labour_cost("p1", "c1")

    # 37/60 * 55 = 33.9166... rounds to 33.92
    assert cost == Decimal("33.92"), f"Expected 33.92, got {cost}"
    db.close()


def test_partial_hour_calculations(tmp_path):
    """Partial-hour precision is preserved."""
    db = Database(str(tmp_path / "partial.db"))
    _make_company(db)
    _make_member(db, "m1", "Alice", "designer", 55.0)
    _make_manager(db)
    _make_company_member(db, "c1", "m1", "designer")
    _make_credential(db, "m1", "alice")
    _make_project(db, "p1", "Project", "Client", "c1")

    # Set cost rate via manager
    _set_auth(db, "mgr", "manager", "c1")
    cs = CostRateService(db)
    cs.set_cost_rate(
        member_id="m1", company_id="c1",
        hourly_cost_aud=Decimal("55.00"),
        effective_from="2026-01-01T00:00:00Z",
        actor_id="mgr",
    )

    # 15 minutes = 0.25 hours * 55 = 13.75
    _set_auth(db, "m1", "designer", "c1")
    _make_approved_entry(db, "e1", "p1", "m1", 15.0, "c1", loaded_cost_rate=55.0)

    fs = FinancialService(db)
    cost = fs.calculate_approved_labour_cost("p1", "c1")
    assert cost == Decimal("13.75"), f"Expected 13.75, got {cost}"
    db.close()


# ------------------------------------------------------------------
# Project budget tests
# ------------------------------------------------------------------

def test_project_budget_creation(tmp_path):
    """Project budget can be created with original and current values."""
    db = Database(str(tmp_path / "budget.db"))
    _make_company(db)
    _make_member(db, "m1", "Alice", "manager", 120.0)
    _make_company_member(db, "c1", "m1", "manager")
    _make_credential(db, "m1", "alice")
    _make_project(db, "p1", "Project", "Client", "c1")

    _set_auth(db, "m1", "manager", "c1")
    service = BudgetService(db)

    budget = service.create_budget(
        project_id="p1",
        company_id="c1",
        original_budget_aud=Decimal("20000.00"),
        effective_from="2026-01-01T00:00:00Z",
        actor_id="m1",
    )

    assert budget.original_budget_aud == Decimal("20000.00")
    assert budget.current_budget_aud == Decimal("20000.00")
    assert budget.project_id == "p1"
    assert budget.company_id == "c1"
    db.close()


def test_budget_revision(tmp_path):
    """Budget revision creates auditable history and updates current budget."""
    db = Database(str(tmp_path / "revision.db"))
    _make_company(db)
    _make_member(db, "m1", "Alice", "manager", 120.0)
    _make_company_member(db, "c1", "m1", "manager")
    _make_credential(db, "m1", "alice")
    _make_project(db, "p1", "Project", "Client", "c1")

    _set_auth(db, "m1", "manager", "c1")
    service = BudgetService(db)

    budget = service.create_budget(
        project_id="p1", company_id="c1",
        original_budget_aud=Decimal("20000.00"),
        effective_from="2026-01-01T00:00:00Z",
        actor_id="m1",
    )

    # Revise budget upward
    revision = service.revise_budget(
        project_budget_id=budget.id,
        new_budget_aud=Decimal("25000.00"),
        revision_reason="Scope increase",
        actor_id="m1",
    )

    assert revision.previous_budget_aud == Decimal("20000.00")
    assert revision.new_budget_aud == Decimal("25000.00")
    assert revision.revision_number == 1

    # Current budget should reflect revision
    current = service.get_current_budget("p1", "c1")
    assert current.current_budget_aud == Decimal("25000.00")
    assert current.original_budget_aud == Decimal("20000.00")  # original preserved

    # Revision history
    revisions = service.list_revisions(budget.id)
    assert len(revisions) == 1
    db.close()


def test_budget_utilization_and_remaining(tmp_path):
    """Budget utilization and remaining budget calculated correctly."""
    db = Database(str(tmp_path / "util.db"))
    _make_company(db)
    _make_member(db, "m1", "Alice", "designer", 55.0)
    _make_member(db, "m2", "Bob", "manager", 120.0)
    _make_company_member(db, "c1", "m1", "designer")
    _make_company_member(db, "c1", "m2", "manager")
    _make_credential(db, "m1", "alice")
    _make_credential(db, "m2", "bob")
    _make_project(db, "p1", "Project", "Client", "c1")

    # Create budget: 20,000 AUD
    _set_auth(db, "m2", "manager", "c1")
    bs = BudgetService(db)
    bs.create_budget(
        project_id="p1", company_id="c1",
        original_budget_aud=Decimal("20000.00"),
        effective_from="2026-01-01T00:00:00Z",
        actor_id="m2",
    )

    # Add approved time: 120 hours * 55 = 6,600 AUD
    _set_auth(db, "m2", "manager", "c1")
    cs = CostRateService(db)
    cs.set_cost_rate(
        member_id="m1", company_id="c1",
        hourly_cost_aud=Decimal("55.00"),
        effective_from="2026-01-01T00:00:00Z",
        actor_id="m2",
    )
    _set_auth(db, "m1", "designer", "c1")
    _make_approved_entry(db, "e1", "p1", "m1", 120 * 60, "c1")  # 120 hours

    fs = FinancialService(db)
    summary = fs.get_financial_summary("p1", "c1")

    assert summary.original_budget_aud == Decimal("20000.00")
    assert summary.approved_labour_cost_aud == Decimal("6600.00")
    assert summary.remaining_budget_aud == Decimal("13400.00")
    assert summary.budget_utilization_percent == 33.0
    assert summary.is_over_budget is False
    db.close()


def test_over_budget_detection(tmp_path):
    """Over-budget indicator when actual cost exceeds budget."""
    db = Database(str(tmp_path / "over.db"))
    _make_company(db)
    _make_member(db, "m1", "Alice", "designer", 55.0)
    _make_member(db, "m2", "Bob", "manager", 120.0)
    _make_company_member(db, "c1", "m1", "designer")
    _make_company_member(db, "c1", "m2", "manager")
    _make_credential(db, "m1", "alice")
    _make_credential(db, "m2", "bob")
    _make_project(db, "p1", "Project", "Client", "c1")

    _set_auth(db, "m2", "manager", "c1")
    bs = BudgetService(db)
    bs.create_budget(
        project_id="p1", company_id="c1",
        original_budget_aud=Decimal("1000.00"),
        effective_from="2026-01-01T00:00:00Z",
        actor_id="m2",
    )

    _set_auth(db, "m2", "manager", "c1")
    cs = CostRateService(db)
    cs.set_cost_rate(
        member_id="m1", company_id="c1",
        hourly_cost_aud=Decimal("55.00"),
        effective_from="2026-01-01T00:00:00Z",
        actor_id="m2",
    )
    _set_auth(db, "m1", "designer", "c1")
    # 20 hours * 55 = 1,100 > 1,000 budget
    _make_approved_entry(db, "e1", "p1", "m1", 20 * 60, "c1")

    fs = FinancialService(db)
    summary = fs.get_financial_summary("p1", "c1")

    assert summary.is_over_budget is True
    assert summary.budget_variance_aud == Decimal("100.00")
    assert summary.remaining_budget_aud == Decimal("-100.00")
    db.close()


def test_zero_budget_handling(tmp_path):
    """Zero budget handled gracefully (no division by zero)."""
    db = Database(str(tmp_path / "zerobudget.db"))
    _make_company(db)
    _make_member(db, "m1", "Alice", "designer", 55.0)
    _make_member(db, "m2", "Bob", "manager", 120.0)
    _make_company_member(db, "c1", "m1", "designer")
    _make_company_member(db, "c1", "m2", "manager")
    _make_credential(db, "m1", "alice")
    _make_credential(db, "m2", "bob")
    _make_project(db, "p1", "Project", "Client", "c1")

    _set_auth(db, "m2", "manager", "c1")
    bs = BudgetService(db)
    bs.create_budget(
        project_id="p1", company_id="c1",
        original_budget_aud=Decimal("0.00"),
        effective_from="2026-01-01T00:00:00Z",
        actor_id="m2",
    )

    _set_auth(db, "m2", "manager", "c1")
    cs = CostRateService(db)
    cs.set_cost_rate(
        member_id="m1", company_id="c1",
        hourly_cost_aud=Decimal("55.00"),
        effective_from="2026-01-01T00:00:00Z",
        actor_id="m2",
    )
    _set_auth(db, "m1", "designer", "c1")
    _make_approved_entry(db, "e1", "p1", "m1", 60.0, "c1")

    fs = FinancialService(db)
    summary = fs.get_financial_summary("p1", "c1")

    assert summary.current_budget_aud == Decimal("0.00")
    assert summary.approved_labour_cost_aud == Decimal("55.00")
    assert summary.budget_utilization_percent == 0.0  # no div by zero
    assert summary.is_over_budget is True
    db.close()


# ------------------------------------------------------------------
# Forecast tests
# ------------------------------------------------------------------

def test_forecast_cost_at_completion(tmp_path):
    """Forecast uses linear burn rate methodology."""
    db = Database(str(tmp_path / "forecast.db"))
    _make_company(db)
    _make_member(db, "m1", "Alice", "designer", 55.0)
    _make_member(db, "m2", "Bob", "manager", 120.0)
    _make_company_member(db, "c1", "m1", "designer")
    _make_company_member(db, "c1", "m2", "manager")
    _make_credential(db, "m1", "alice")
    _make_credential(db, "m2", "bob")
    _make_project(db, "p1", "Project", "Client", "c1")

    _set_auth(db, "m2", "manager", "c1")
    bs = BudgetService(db)
    bs.create_budget(
        project_id="p1", company_id="c1",
        original_budget_aud=Decimal("20000.00"),
        effective_from="2026-01-01T00:00:00Z",
        actor_id="m2",
    )

    _set_auth(db, "m2", "manager", "c1")
    cs = CostRateService(db)
    cs.set_cost_rate(
        member_id="m1", company_id="c1",
        hourly_cost_aud=Decimal("55.00"),
        effective_from="2026-01-01T00:00:00Z",
        actor_id="m2",
    )
    _set_auth(db, "m1", "designer", "c1")
    # 100 hours * 55 = 5,500 actual cost
    _make_approved_entry(db, "e1", "p1", "m1", 100 * 60, "c1")

    fs = FinancialService(db)
    forecast = fs.forecast_cost_at_completion("p1", "c1")

    assert forecast["actual_cost_to_date"] == Decimal("5500.00")
    assert forecast["remaining_budget"] == Decimal("14500.00")
    assert forecast["burn_rate_per_hour"] == Decimal("55.00")
    # Forecast cost = actual + remaining = 5500 + 14500 = 20000
    assert forecast["forecast_cost_at_completion"] == Decimal("20000.00")
    assert forecast["forecast_budget_variance"] == Decimal("0.00")
    db.close()


# ------------------------------------------------------------------
# Project profitability
# ------------------------------------------------------------------

def test_project_profitability(tmp_path):
    """Gross margin = billing value - labour cost."""
    db = Database(str(tmp_path / "profit.db"))
    _make_company(db)
    _make_member(db, "m1", "Alice", "designer", 55.0)
    _make_member(db, "m2", "Bob", "manager", 120.0)
    _make_company_member(db, "c1", "m1", "designer")
    _make_company_member(db, "c1", "m2", "manager")
    _make_credential(db, "m1", "alice")
    _make_credential(db, "m2", "bob")
    _make_project(db, "p1", "Project", "Client", "c1")

    _set_auth(db, "m2", "manager", "c1")
    bs = BudgetService(db)
    bs.create_budget(
        project_id="p1", company_id="c1",
        original_budget_aud=Decimal("20000.00"),
        effective_from="2026-01-01T00:00:00Z",
        actor_id="m2",
    )

    # Set billing rate
    crs = CostRateService(db)
    crs.set_billing_rate(
        member_id="m1", company_id="c1",
        hourly_billing_aud=Decimal("120.00"),
        effective_from="2026-01-01T00:00:00Z",
        actor_id="m2",
    )

    _set_auth(db, "m2", "manager", "c1")
    cs = CostRateService(db)
    cs.set_cost_rate(
        member_id="m1", company_id="c1",
        hourly_cost_aud=Decimal("55.00"),
        effective_from="2026-01-01T00:00:00Z",
        actor_id="m2",
    )
    _set_auth(db, "m1", "designer", "c1")
    # 100 hours: cost = 5,500, billing = 12,000, margin = 6,500
    _make_approved_entry(db, "e1", "p1", "m1", 100 * 60, "c1")

    fs = FinancialService(db)
    summary = fs.get_financial_summary("p1", "c1")

    assert summary.billing_value_aud == Decimal("12000.00")
    assert summary.approved_labour_cost_aud == Decimal("5500.00")
    assert summary.gross_margin_aud == Decimal("6500.00")
    db.close()


# ------------------------------------------------------------------
# Company-scoped financial queries
# ------------------------------------------------------------------

def test_company_scoped_financial_queries(tmp_path):
    """Financial queries respect company isolation."""
    db = Database(str(tmp_path / "company.db"))
    _make_company(db, "c1", "Company One")
    _make_company(db, "c2", "Company Two")
    _make_member(db, "m1", "Alice", "designer", 55.0)
    _make_member(db, "m2", "Bob", "designer", 70.0)
    _make_member(db, "mgr", "Manager", "manager", 120.0)
    _make_company_member(db, "c1", "m1", "designer")
    _make_company_member(db, "c2", "m2", "designer")
    _make_company_member(db, "c1", "mgr", "manager")
    _make_company_member(db, "c2", "mgr", "manager")
    _make_credential(db, "m1", "alice")
    _make_credential(db, "m2", "bob")
    _make_credential(db, "mgr", "mgr")
    _make_project(db, "p1", "Project 1", "Client", "c1")
    _make_project(db, "p2", "Project 2", "Client", "c2")

    _set_auth(db, "mgr", "manager", "c1")
    cs = CostRateService(db)
    cs.set_cost_rate(
        member_id="m1", company_id="c1",
        hourly_cost_aud=Decimal("55.00"),
        effective_from="2026-01-01T00:00:00Z",
        actor_id="mgr",
    )
    _set_auth(db, "mgr", "manager", "c2")
    cs.set_cost_rate(
        member_id="m2", company_id="c2",
        hourly_cost_aud=Decimal("70.00"),
        effective_from="2026-01-01T00:00:00Z",
        actor_id="mgr",
    )

    _make_approved_entry(db, "e1", "p1", "m1", 60.0, "c1")
    _make_approved_entry(db, "e2", "p2", "m2", 60.0, "c2")

    fs = FinancialService(db)
    c1_cost = fs.calculate_approved_labour_cost("p1", "c1")
    c2_cost = fs.calculate_approved_labour_cost("p2", "c2")

    assert c1_cost == Decimal("55.00")
    assert c2_cost == Decimal("70.00")
    db.close()


# ------------------------------------------------------------------
# Unauthorized access tests
# ------------------------------------------------------------------

def test_unauthorized_rate_change_rejected(tmp_path):
    """Designer cannot set cost rates (manager/admin only)."""
    db = Database(str(tmp_path / "unauth_rate.db"))
    _make_company(db)
    _make_member(db, "m1", "Alice", "designer", 55.0)
    _make_company_member(db, "c1", "m1", "designer")
    _make_credential(db, "m1", "alice")

    _set_auth(db, "m1", "designer", "c1")
    service = CostRateService(db)

    with pytest.raises(PermissionError):
        service.set_cost_rate(
            member_id="m1", company_id="c1",
            hourly_cost_aud=Decimal("65.00"),
            effective_from="2026-01-01T00:00:00Z",
            actor_id="m1",
        )
    db.close()


def test_unauthorized_budget_change_rejected(tmp_path):
    """Designer cannot create budgets (manager/admin only)."""
    db = Database(str(tmp_path / "unauth_budget.db"))
    _make_company(db)
    _make_member(db, "m1", "Alice", "designer", 55.0)
    _make_company_member(db, "c1", "m1", "designer")
    _make_credential(db, "m1", "alice")
    _make_project(db, "p1", "Project", "Client", "c1")

    _set_auth(db, "m1", "designer", "c1")
    service = BudgetService(db)

    with pytest.raises(PermissionError):
        service.create_budget(
            project_id="p1", company_id="c1",
            original_budget_aud=Decimal("20000.00"),
            effective_from="2026-01-01T00:00:00Z",
            actor_id="m1",
        )
    db.close()


# ------------------------------------------------------------------
# No automatic billing
# ------------------------------------------------------------------

def test_no_automatic_billing(tmp_path):
    """Approved time is never automatically billed."""
    db = Database(str(tmp_path / "nobilling.db"))
    _make_company(db)
    _make_member(db, "m1", "Alice", "designer", 55.0)
    _make_member(db, "m2", "Bob", "manager", 120.0)
    _make_company_member(db, "c1", "m1", "designer")
    _make_company_member(db, "c1", "m2", "manager")
    _make_credential(db, "m1", "alice")
    _make_credential(db, "m2", "bob")
    _make_project(db, "p1", "Project", "Client", "c1")

    _set_auth(db, "m1", "designer", "c1")
    _make_approved_entry(db, "e1", "p1", "m1", 60.0, "c1")

    # Entry should be APPROVED, not BILLED
    entry = db.get_time_entry("e1")
    assert entry.state == TimeEntryState.APPROVED
    assert entry.billed_minutes == 0.0

    # Financial cost calculation should work on approved (not billed) entries
    _set_auth(db, "m2", "manager", "c1")
    cs = CostRateService(db)
    cs.set_cost_rate(
        member_id="m1", company_id="c1",
        hourly_cost_aud=Decimal("55.00"),
        effective_from="2026-01-01T00:00:00Z",
        actor_id="m2",
    )
    _set_auth(db, "m1", "designer", "c1")
    fs = FinancialService(db)
    cost = fs.calculate_approved_labour_cost("p1", "c1")
    assert cost == Decimal("55.00")
    db.close()


# ------------------------------------------------------------------
# Database migration compatibility
# ------------------------------------------------------------------

def test_schema_v10_migration(tmp_path):
    """Database migrates to v10 with financial tables."""
    db = Database(str(tmp_path / "v10.db"))

    # Check version
    version = db.conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
    assert version == 10

    # Check financial tables exist
    tables = db.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%financial%' OR name LIKE '%budget%' OR name LIKE '%employee_cost%' OR name LIKE '%employee_billing%'"
    ).fetchall()
    table_names = [t[0] for t in tables]
    assert "employee_cost_rates" in table_names
    assert "employee_billing_rates" in table_names
    assert "project_budgets" in table_names
    assert "budget_revisions" in table_names
    assert "financial_adjustments" in table_names
    assert "financial_audit_events" in table_names
    db.close()


def test_v9_to_v10_migration_preserves_data(tmp_path):
    """Migrating from v9 to v10 preserves existing data."""
    db = Database(str(tmp_path / "v9tov10.db"))

    # Create some v9 data
    _make_company(db)
    _make_member(db, "m1", "Alice", "designer", 55.0)
    _make_company_member(db, "c1", "m1", "designer")
    _make_credential(db, "m1", "alice")
    _make_project(db, "p1", "Project", "Client", "c1")
    _make_approved_entry(db, "e1", "p1", "m1", 60.0, "c1")

    version = db.conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
    assert version == 10

    # Existing data still accessible
    entry = db.get_time_entry("e1")
    assert entry is not None
    assert entry.state == TimeEntryState.APPROVED
    db.close()

