"""Financial Dashboard Screen - BIMSpend R1-07.

Management dashboard showing project financial summaries:
- Active projects, total budget, actual labour cost, remaining budget
- Projects approaching budget limits, over-budget projects
- Cost trends, project financial summaries

All data derived from approved time entries only.
Company-scoped: managers/administrators only.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from decimal import Decimal
from typing import Any, Optional

from bimspend.app.screens.base import BaseScreen
from bimspend.app.shell import BIMSpendApp
from bimspend.financial import FinancialService, BudgetService, CostRateService
from bimspend.identity import Role, current_auth


class FinancialDashboardScreen(BaseScreen):
    """Management financial dashboard showing project financial summaries."""

    def __init__(self, parent: ttk.Widget, app: BIMSpendApp):
        super().__init__(parent, app)
        self.financial_service = FinancialService(self.db)
        self.budget_service = BudgetService(self.db)
        self.cost_rate_service = CostRateService(self.db)
        self._summary_cards: list[ttk.Frame] = []

    def on_show(self) -> None:
        """Refresh when shown."""
        for widget in self.winfo_children():
            widget.destroy()
        self._build_ui()

    def _build_ui(self) -> None:
        app = self.app

        # Header
        self._section_header("Financial Dashboard", "Project costing and budget consumption — approved time only")

        # Session info bar
        self._build_session_bar()

        # Metric row
        self._build_metric_row()

        # Project financial summaries table
        self._build_project_table()

        # Action buttons
        self._build_action_buttons()

        # Populate
        self._refresh()

    def _build_session_bar(self) -> None:
        """Build the session info bar."""
        frame = ttk.Frame(self, style="App.TFrame")
        frame.pack(fill="x", pady=(0, 8))

        actor = current_auth.actor
        if actor:
            ttk.Label(
                frame,
                text=f"Actor: {actor.id} ({actor.role.value})",
                style="MetricLabel.TLabel",
            ).pack(side="left", padx=(0, 16))
            ttk.Label(
                frame,
                text=f"Company: {actor.company_id}",
                style="MetricLabel.TLabel",
            ).pack(side="left", padx=(0, 16))
        else:
            ttk.Label(
                frame,
                text="No authenticated session",
                style="MetricLabel.TLabel",
            ).pack(side="left", padx=(0, 16))

        ttk.Button(
            frame,
            text="Refresh",
            command=self._refresh,
        ).pack(side="right")

    def _build_metric_row(self) -> None:
        """Build the top metric cards."""
        frame = ttk.Frame(self, style="App.TFrame")
        frame.pack(fill="x", pady=(0, 16))

        self._total_budget_card = self._metric_card(
            frame, "Total Current Budget", "AUD 0.00", "All projects"
        )
        self._actual_cost_card = self._metric_card(
            frame, "Actual Approved Labour Cost", "AUD 0.00", "From approved entries"
        )
        self._remaining_card = self._metric_card(
            frame, "Remaining Budget", "AUD 0.00", "Budget minus actual cost"
        )
        self._over_budget_card = self._metric_card(
            frame, "Over-Budget Projects", "0", "Projects exceeding budget"
        )

    def _build_project_table(self) -> None:
        """Build the project financial summaries table."""
        frame = ttk.Frame(self, style="App.TFrame")
        frame.pack(fill="both", expand=True)

        cols = (
            "project",
            "budget",
            "actual_cost",
            "remaining",
            "utilization",
            "status",
        )
        self._tree = ttk.Treeview(
            frame, columns=cols, show="headings", height=12
        )
        self._tree.heading("#0", text="Project")
        self._tree.heading("project", text="Project")
        self._tree.heading("budget", text="Budget (AUD)")
        self._tree.heading("actual_cost", text="Actual Cost (AUD)")
        self._tree.heading("remaining", text="Remaining (AUD)")
        self._tree.heading("utilization", text="Utilization %")
        self._tree.heading("status", text="Status")

        self._tree.column("#0", width=0, stretch=False)
        self._tree.column("project", width=200)
        self._tree.column("budget", width=120)
        self._tree.column("actual_cost", width=120)
        self._tree.column("remaining", width=120)
        self._tree.column("utilization", width=100)
        self._tree.column("status", width=100)

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)

        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _build_action_buttons(self) -> None:
        """Build action buttons."""
        frame = ttk.Frame(self, style="App.TFrame")
        frame.pack(fill="x", pady=(8, 0))

        ttk.Button(
            frame,
            text="Project Detail",
            command=self._view_project_detail,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            frame,
            text="Manage Rates",
            command=self._manage_rates,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            frame,
            text="Manage Budgets",
            command=self._manage_budgets,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            frame,
            text="Reports",
            command=self._view_reports,
        ).pack(side="left")

    def _refresh(self) -> None:
        """Refresh the dashboard."""
        actor = current_auth.actor
        if actor is None:
            return

        # Clear metric cards
        for card in self._summary_cards:
            card.destroy()
        self._summary_cards.clear()

        # Clear tree
        self._tree.delete(*self._tree.get_children())

        # Get all financial summaries for this company
        summaries = self.financial_service.get_all_financial_summaries(actor.company_id)

        total_budget = Decimal("0")
        total_actual = Decimal("0")
        total_remaining = Decimal("0")
        over_budget_count = 0

        for summary in summaries:
            total_budget += summary.current_budget_aud
            total_actual += summary.approved_labour_cost_aud
            total_remaining += summary.remaining_budget_aud
            if summary.is_over_budget:
                over_budget_count += 1

            # Determine status color
            if summary.is_over_budget:
                status = "OVER BUDGET"
                status_color = "#9B2C2C"
            elif summary.budget_utilization_percent > 80:
                status = "APPROACHING LIMIT"
                status_color = "#B8860B"
            else:
                status = "ON TRACK"
                status_color = "#287E72"

            self._tree.insert(
                "",
                "end",
                values=(
                    summary.project_name,
                    f"{summary.current_budget_aud:,.2f}",
                    f"{summary.approved_labour_cost_aud:,.2f}",
                    f"{summary.remaining_budget_aud:,.2f}",
                    f"{summary.budget_utilization_percent:.1f}",
                    status,
                ),
                tags=(status_color,),
            )

        # Update metric cards
        self._total_budget_card.winfo_children()[1].winfo_children()[1].config(
            text=f"AUD {total_budget:,.2f}"
        )
        self._actual_cost_card.winfo_children()[1].winfo_children()[1].config(
            text=f"AUD {total_actual:,.2f}"
        )
        self._remaining_card.winfo_children()[1].winfo_children()[1].config(
            text=f"AUD {total_remaining:,.2f}"
        )
        self._over_budget_card.winfo_children()[1].winfo_children()[1].config(
            text=str(over_budget_count)
        )

        # Configure status tag colors
        self._tree.tag_configure("#9B2C2C", foreground="#9B2C2C")
        self._tree.tag_configure("#B8860B", foreground="#B8860B")
        self._tree.tag_configure("#287E72", foreground="#287E72")

    def _view_project_detail(self) -> None:
        """View financial detail for selected project."""
        selection = self._tree.selection()
        if not selection:
            messagebox.showinfo("Project Detail", "Select a project to view details.")
            return

        item = self._tree.item(selection[0])
        project_name = item["values"][0]

        # Navigate to project detail screen
        self.app.show_screen("project_financial_detail")
        # The detail screen would need to know which project — we set it via app
        self.app.current_project_name = project_name

    def _manage_rates(self) -> None:
        """Manage employee cost/billing rates."""
        messagebox.showinfo(
            "Manage Rates",
            "Employee cost and billing rate management.\n\n"
            "Use the Rates screen to view and set historical rates.\n"
            "Manager/administrator role required.",
        )

    def _manage_budgets(self) -> None:
        """Manage project budgets."""
        messagebox.showinfo(
            "Manage Budgets",
            "Project budget management.\n\n"
            "Use the Budgets screen to create and revise budgets.\n"
            "Manager/administrator role required.",
        )

    def _view_reports(self) -> None:
        """View financial reports."""
        self.app.show_screen("financial_reports")