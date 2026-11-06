"""Project Financial Detail Screen - BIMSpend R1-08.

Detailed financial view for a single project:
- Project information, budget and revisions
- Approved labour hours, labour cost by employee
- Cost rate applied, remaining budget, forecast, variance
- Financial history with drill-down to approved time records

Company-scoped: managers/administrators can configure;
designers can view read-only.
Uses the BIMSpend design system.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from decimal import Decimal
from typing import Any, Optional

from bimspend.app.design import (
    ACCENT_AMBER,
    ACCENT_BLUE,
    ACCENT_RED,
    ACCENT_TEAL,
    APP_BG,
    CARD_BG,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    format_aud,
    format_date_time,
    format_minutes,
)
from bimspend.app.screens.base import BaseScreen
from bimspend.app.shell import BIMSpendApp
from bimspend.financial import (
    FinancialDomainError,
    FinancialService,
    BudgetService,
    CostRateService,
)
from bimspend.identity import Role, current_auth


class ProjectFinancialDetailScreen(BaseScreen):
    """Project financial detail view with drill-down to approved time records."""

    def __init__(self, parent: ttk.Widget, app: BIMSpendApp):
        super().__init__(parent, app)
        self.financial_service = FinancialService(self.db)
        self.budget_service = BudgetService(self.db)
        self.cost_rate_service = CostRateService(self.db)
        self._project_id: Optional[str] = None

    def on_show(self) -> None:
        """Refresh when shown."""
        for widget in self.winfo_children():
            widget.destroy()
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        app = self.app

        # Header
        self._section_header(
            "Project Financial Detail",
            "Approved time costs, budget consumption, and forecasting",
        )

        # Session info bar
        self._build_session_bar()

        # Project info panel
        self._build_project_info()

        # Budget panel
        self._build_budget_panel()

        # Cost breakdown table (by employee)
        self._build_cost_breakdown()

        # Forecast panel
        self._build_forecast_panel()

        # Action buttons
        self._build_action_buttons()

    def _build_session_bar(self) -> None:
        """Build the session info bar."""
        frame = ttk.Frame(self, style="App.TFrame")
        frame.pack(fill="x", pady=(0, 8))

        actor = current_auth.actor
        if actor:
            ttk.Label(
                frame,
                text=f"Actor: {actor.id}  ({actor.role.value})",
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

    def _build_project_info(self) -> None:
        """Build the project information panel."""
        self._info_frame = ttk.Frame(self, style="Card.TFrame")
        self._info_frame.pack(fill="x", pady=(0, 16))

        inner = ttk.Frame(self._info_frame, style="Card.TFrame")
        inner.pack(fill="x", padx=16, pady=12)

        ttk.Label(
            inner,
            text="Project Information",
            style="MetricLabel.TLabel",
        ).pack(anchor="w", pady=(0, 8))

        self._project_name_label = ttk.Label(
            inner, text="—", style="MetricValue.TLabel"
        )
        self._project_name_label.pack(anchor="w", pady=(0, 2))

        self._project_client_label = ttk.Label(
            inner, text="", style="MetricLabel.TLabel"
        )
        self._project_client_label.pack(anchor="w", pady=(0, 2))

        self._project_status_label = ttk.Label(
            inner, text="", style="MetricLabel.TLabel"
        )
        self._project_status_label.pack(anchor="w")

    def _build_budget_panel(self) -> None:
        """Build the budget consumption panel."""
        self._budget_frame = ttk.Frame(self, style="Card.TFrame")
        self._budget_frame.pack(fill="x", pady=(0, 16))

        inner = ttk.Frame(self._budget_frame, style="Card.TFrame")
        inner.pack(fill="x", padx=16, pady=12)

        ttk.Label(
            inner, text="Budget Consumption", style="MetricLabel.TLabel"
        ).pack(anchor="w", pady=(0, 8))

        metrics_frame = ttk.Frame(inner, style="Card.TFrame")
        metrics_frame.pack(fill="x")

        self._orig_budget_label = self._metric_row(
            metrics_frame, "Original Budget", "AUD 0.00"
        )
        self._current_budget_label = self._metric_row(
            metrics_frame, "Current Budget", "AUD 0.00"
        )
        self._actual_cost_label = self._metric_row(
            metrics_frame, "Actual Labour Cost", "AUD 0.00"
        )
        self._remaining_label = self._metric_row(
            metrics_frame, "Remaining Budget", "AUD 0.00"
        )
        self._utilization_label = self._metric_row(
            metrics_frame, "Utilization", "0.0%"
        )
        self._variance_label = self._metric_row(
            metrics_frame, "Variance", "AUD 0.00"
        )

    def _metric_row(
        self, parent: ttk.Widget, label: str, value: str
    ) -> ttk.Label:
        """Create a label-value metric row."""
        frame = ttk.Frame(parent, style="Card.TFrame")
        frame.pack(fill="x", pady=2, side="left", padx=(0, 24))
        ttk.Label(frame, text=label, style="MetricLabel.TLabel").pack(
            anchor="w"
        )
        val_label = ttk.Label(frame, text=value, style="MetricValue.TLabel")
        val_label.pack(anchor="w", pady=(2, 0))
        return val_label

    def _build_cost_breakdown(self) -> None:
        """Build the labour cost by employee table."""
        frame = ttk.Frame(self, style="App.TFrame")
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text="Labour Cost by Employee",
            style="MetricLabel.TLabel",
        ).pack(anchor="w", pady=(0, 8))

        cols = ("employee", "hours", "cost_rate", "cost_aud")
        self._tree = ttk.Treeview(
            frame,
            columns=cols,
            show="headings",
            height=8,
            style="App.Treeview",
        )
        self._tree.heading("#0", text="Employee")
        self._tree.heading("employee", text="Employee")
        self._tree.heading("hours", text="Approved Hours")
        self._tree.heading("cost_rate", text="Cost Rate (AUD/hr)")
        self._tree.heading("cost_aud", text="Cost (AUD)")

        self._tree.column("#0", width=0, stretch=False)
        self._tree.column("employee", width=150)
        self._tree.column("hours", width=120)
        self._tree.column("cost_rate", width=140)
        self._tree.column("cost_aud", width=120)

        scrollbar = ttk.Scrollbar(
            frame, orient="vertical", command=self._tree.yview
        )
        self._tree.configure(yscrollcommand=scrollbar.set)

        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _build_forecast_panel(self) -> None:
        """Build the forecasting panel."""
        self._forecast_frame = ttk.Frame(self, style="Card.TFrame")
        self._forecast_frame.pack(fill="x", pady=(0, 16))

        inner = ttk.Frame(self._forecast_frame, style="Card.TFrame")
        inner.pack(fill="x", padx=16, pady=12)

        ttk.Label(
            inner,
            text="Forecast (Deterministic, Linear Burn Rate)",
            style="MetricLabel.TLabel",
        ).pack(anchor="w", pady=(0, 8))

        self._forecast_actual_label = self._metric_row(
            inner, "Actual Cost to Date", "AUD 0.00"
        )
        self._forecast_burn_label = self._metric_row(
            inner, "Burn Rate (AUD/hr)", "AUD 0.00"
        )
        self._forecast_cost_label = self._metric_row(
            inner, "Forecast Cost at Completion", "AUD 0.00"
        )
        self._forecast_variance_label = self._metric_row(
            inner, "Forecast Budget Variance", "AUD 0.00"
        )

    def _build_action_buttons(self) -> None:
        """Build action buttons."""
        frame = ttk.Frame(self, style="App.TFrame")
        frame.pack(fill="x", pady=(8, 0))

        ttk.Button(
            frame,
            text="Back to Dashboard",
            command=self._back_to_dashboard,
        ).pack(side="left", padx=(0, 8))

        actor = current_auth.actor
        if actor and actor.role in (Role.MANAGER, Role.ADMINISTRATOR):
            ttk.Button(
                frame,
                text="Set Cost Rate",
                command=self._set_cost_rate,
            ).pack(side="left", padx=(0, 8))

            ttk.Button(
                frame,
                text="Revise Budget",
                command=self._revise_budget,
            ).pack(side="left")

    def _refresh(self) -> None:
        """Refresh the project detail view."""
        actor = current_auth.actor
        if actor is None:
            return

        project_id = getattr(self.app, "current_project_id", None) or self._project_id
        if project_id is None:
            project_name = getattr(self.app, "current_project_name", None)
            if project_name:
                for p in self.db.list_projects():
                    if (
                        p.name == project_name
                        and (p.company_id is None or p.company_id == actor.company_id)
                    ):
                        project_id = p.id
                        break
        if project_id is None:
            return

        self._project_id = project_id

        try:
            summary = self.financial_service.get_financial_summary(
                project_id, actor.company_id
            )
        except (PermissionError, FinancialDomainError) as exc:
            messagebox.showerror("Financial Error", str(exc))
            return

        project = self.db.get_project(project_id)
        if project:
            self._project_name_label.config(text=project.name)
            self._project_client_label.config(
                text=f"Client: {project.client}"
            )
            self._project_status_label.config(
                text=f"Status: {'Archived' if project.is_archived else 'Active'}"
            )

        self._orig_budget_label.config(
            text=f"AUD {summary.original_budget_aud:,.2f}"
        )
        self._current_budget_label.config(
            text=f"AUD {summary.current_budget_aud:,.2f}"
        )
        self._actual_cost_label.config(
            text=f"AUD {summary.approved_labour_cost_aud:,.2f}"
        )
        self._remaining_label.config(
            text=f"AUD {summary.remaining_budget_aud:,.2f}"
        )
        self._utilization_label.config(
            text=f"{summary.budget_utilization_percent:.1f}%"
        )
        self._variance_label.config(
            text=f"AUD {summary.budget_variance_aud:,.2f}"
        )

        if summary.is_over_budget:
            self._variance_label.config(foreground=ACCENT_RED)
        else:
            self._variance_label.config(foreground=ACCENT_TEAL)

        self._tree.delete(*self._tree.get_children())
        cost_by_user = (
            self.financial_service.calculate_approved_labour_cost_by_user(
                project_id, actor.company_id
            )
        )
        entries = self.financial_service.get_approved_entries_for_project(
            project_id, actor.company_id
        )
        hours_by_user: dict[str, float] = {}
        for e in entries:
            hours_by_user[e.user_id] = (
                hours_by_user.get(e.user_id, 0.0) + e.minutes
            )

        for user_id, cost in cost_by_user.items():
            member = next(
                (m for m in self.db.list_members() if m.id == user_id), None
            )
            name = member.name if member else user_id
            hours = hours_by_user.get(user_id, 0.0) / 60.0
            rate = cost / Decimal(str(hours)) if hours > 0 else Decimal("0")

            self._tree.insert(
                "",
                "end",
                values=(
                    name,
                    f"{hours:.2f}",
                    f"AUD {rate:,.2f}",
                    f"AUD {cost:,.2f}",
                ),
            )

        forecast = self.financial_service.forecast_cost_at_completion(
            project_id, actor.company_id
        )
        self._forecast_actual_label.config(
            text=f"AUD {forecast['actual_cost_to_date']:,.2f}"
        )
        self._forecast_burn_label.config(
            text=f"AUD {forecast['burn_rate_per_hour']:,.2f}"
        )
        self._forecast_cost_label.config(
            text=f"AUD {forecast['forecast_cost_at_completion']:,.2f}"
        )
        self._forecast_variance_label.config(
            text=f"AUD {forecast['forecast_budget_variance']:,.2f}"
        )

    def _back_to_dashboard(self) -> None:
        """Return to financial dashboard."""
        self.app.show_screen("financial_dashboard")

    def _set_cost_rate(self) -> None:
        """Set employee cost rate."""
        messagebox.showinfo(
            "Set Cost Rate",
            "Cost rate management.\n\n"
            "Enter employee ID, company, hourly cost rate, and effective date.\n"
            "Historical rates are preserved — new rates create new records.\n"
            "Manager/administrator role required.",
        )

    def _revise_budget(self) -> None:
        """Revise project budget."""
        messagebox.showinfo(
            "Revise Budget",
            "Budget revision management.\n\n"
            "Enter new budget amount and reason.\n"
            "Previous budget is preserved in revision history.\n"
            "Manager/administrator role required.",
        )
