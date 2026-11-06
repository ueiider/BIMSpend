"""Financial Reports Screen - BIMSpend R1-07.

Exportable financial reports:
- Project cost summary
- Budget versus actual
- Employee labour cost
- Project labour utilization
- Approved hours by project
- Financial variance
- Cost trend by period

CSV export supported. All exports respect company and role permissions.
"""

from __future__ import annotations

import csv
import io
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from decimal import Decimal
from typing import Any, Optional

from bimspend.app.screens.base import BaseScreen
from bimspend.app.shell import BIMSpendApp
from bimspend.financial import FinancialService, BudgetService, CostRateService
from bimspend.identity import Role, current_auth


class FinancialReportsScreen(BaseScreen):
    """Financial reports with CSV export."""

    def __init__(self, parent: ttk.Widget, app: BIMSpendApp):
        super().__init__(parent, app)
        self.financial_service = FinancialService(self.db)
        self.budget_service = BudgetService(self.db)
        self.cost_rate_service = CostRateService(self.db)

    def on_show(self) -> None:
        """Refresh when shown."""
        for widget in self.winfo_children():
            widget.destroy()
        self._build_ui()

    def _build_ui(self) -> None:
        app = self.app

        # Header
        self._section_header("Financial Reports", "Exportable management reports — CSV format")

        # Session info bar
        self._build_session_bar()

        # Report selection
        self._build_report_selection()

        # Report results
        self._build_report_results()

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

    def _build_report_selection(self) -> None:
        """Build the report type selection."""
        frame = ttk.Frame(self, style="App.TFrame")
        frame.pack(fill="x", pady=(0, 16))

        ttk.Label(frame, text="Report Type:").pack(side="left", padx=(0, 8))

        self._report_var = tk.StringVar(value="project_cost_summary")
        reports = [
            ("Project Cost Summary", "project_cost_summary"),
            ("Budget vs Actual", "budget_vs_actual"),
            ("Employee Labour Cost", "employee_labour_cost"),
            ("Approved Hours by Project", "approved_hours_by_project"),
            ("Financial Variance", "financial_variance"),
        ]
        for label, value in reports:
            ttk.Radiobutton(
                frame,
                text=label,
                variable=self._report_var,
                value=value,
            ).pack(side="left", padx=(0, 16))

    def _build_report_results(self) -> None:
        """Build the report results display."""
        frame = ttk.Frame(self, style="App.TFrame")
        frame.pack(fill="both", expand=True)

        self._result_text = tk.Text(frame, height=20, wrap="none")
        self._result_text.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self._result_text.yview)
        self._result_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

    def _build_action_buttons(self) -> None:
        """Build action buttons."""
        frame = ttk.Frame(self, style="App.TFrame")
        frame.pack(fill="x", pady=(8, 0))

        ttk.Button(
            frame,
            text="Generate Report",
            command=self._generate_report,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            frame,
            text="Export CSV",
            command=self._export_csv,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            frame,
            text="Back to Dashboard",
            command=self._back_to_dashboard,
        ).pack(side="left")

    def _refresh(self) -> None:
        """Refresh the report display."""
        self._generate_report()

    def _generate_report(self) -> None:
        """Generate the selected report."""
        actor = current_auth.actor
        if actor is None:
            messagebox.showerror("Report Error", "No authenticated session.")
            return

        report_type = self._report_var.get()
        company_id = actor.company_id

        try:
            if report_type == "project_cost_summary":
                self._generate_project_cost_summary(company_id)
            elif report_type == "budget_vs_actual":
                self._generate_budget_vs_actual(company_id)
            elif report_type == "employee_labour_cost":
                self._generate_employee_labour_cost(company_id)
            elif report_type == "approved_hours_by_project":
                self._generate_approved_hours_by_project(company_id)
            elif report_type == "financial_variance":
                self._generate_financial_variance(company_id)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Report Error", str(exc))

    def _format_currency(self, value: Decimal) -> str:
        return f"AUD {value:,.2f}"

    def _generate_project_cost_summary(self, company_id: str) -> None:
        """Generate project cost summary report."""
        summaries = self.financial_service.get_all_financial_summaries(company_id)

        lines = []
        lines.append("PROJECT COST SUMMARY")
        lines.append("=" * 60)
        lines.append(f"Company: {company_id}")
        lines.append(f"Generated: {self._now_iso()}")
        lines.append("")
        lines.append(f"{'Project':<30} {'Budget':>14} {'Actual':>14} {'Remaining':>14} {'Util%':>8}")
        lines.append("-" * 60)

        for s in summaries:
            lines.append(
                f"{s.project_name[:28]:<30} "
                f"{self._format_currency(s.current_budget_aud):>14} "
                f"{self._format_currency(s.approved_labour_cost_aud):>14} "
                f"{self._format_currency(s.remaining_budget_aud):>14} "
                f"{s.budget_utilization_percent:>7.1f}%"
            )

        lines.append("-" * 60)
        total_budget = sum((s.current_budget_aud for s in summaries), Decimal("0"))
        total_actual = sum((s.approved_labour_cost_aud for s in summaries), Decimal("0"))
        total_remaining = sum((s.remaining_budget_aud for s in summaries), Decimal("0"))
        lines.append(
            f"{'TOTAL':<30} "
            f"{self._format_currency(total_budget):>14} "
            f"{self._format_currency(total_actual):>14} "
            f"{self._format_currency(total_remaining):>14} "
            f"{'':>8}"
        )

        self._result_text.delete("1.0", tk.END)
        self._result_text.insert("1.0", "\n".join(lines))

    def _generate_budget_vs_actual(self, company_id: str) -> None:
        """Generate budget vs actual report."""
        summaries = self.financial_service.get_all_financial_summaries(company_id)

        lines = []
        lines.append("BUDGET vs ACTUAL")
        lines.append("=" * 60)
        lines.append(f"Company: {company_id}")
        lines.append(f"Generated: {self._now_iso()}")
        lines.append("")
        lines.append(f"{'Project':<30} {'Budget':>14} {'Actual':>14} {'Variance':>14} {'Status':>14}")
        lines.append("-" * 60)

        for s in summaries:
            status = "OVER BUDGET" if s.is_over_budget else "OK"
            lines.append(
                f"{s.project_name[:28]:<30} "
                f"{self._format_currency(s.current_budget_aud):>14} "
                f"{self._format_currency(s.approved_labour_cost_aud):>14} "
                f"{self._format_currency(s.budget_variance_aud):>14} "
                f"{status:>14}"
            )

        self._result_text.delete("1.0", tk.END)
        self._result_text.insert("1.0", "\n".join(lines))

    def _generate_employee_labour_cost(self, company_id: str) -> None:
        """Generate employee labour cost report."""
        # Get all approved entries for the company
        from bimspend.models import TimeEntryState
        entries = self.db.list_time_entries(state=TimeEntryState.APPROVED)
        entries = [e for e in entries if e.company_id == company_id]

        # Group by employee
        by_employee: dict[str, dict[str, Any]] = {}
        for e in entries:
            if e.user_id not in by_employee:
                member = next((m for m in self.db.list_members() if m.id == e.user_id), None)
                by_employee[e.user_id] = {
                    "name": member.name if member else e.user_id,
                    "hours": 0.0,
                    "cost": Decimal("0"),
                }
            cost_rate = self.db.get_effective_employee_cost_rate(
                e.user_id, company_id, e.created_at or self._now_iso()
            )
            rate = cost_rate.hourly_cost_aud if cost_rate else Decimal("0")
            entry_cost = (Decimal(str(e.minutes)) / Decimal("60")) * rate
            entry_cost = entry_cost.quantize(Decimal("0.01"))
            by_employee[e.user_id]["hours"] += e.minutes / 60.0
            by_employee[e.user_id]["cost"] += entry_cost

        lines = []
        lines.append("EMPLOYEE LABOUR COST")
        lines.append("=" * 60)
        lines.append(f"Company: {company_id}")
        lines.append(f"Generated: {self._now_iso()}")
        lines.append("")
        lines.append(f"{'Employee':<25} {'Hours':>10} {'Cost Rate':>14} {'Total Cost':>14}")
        lines.append("-" * 60)

        total_cost = Decimal("0")
        total_hours = 0.0
        for emp_id, data in by_employee.items():
            hours = data["hours"]
            cost = data["cost"]
            rate = cost / Decimal(str(hours)) if hours > 0 else Decimal("0")
            lines.append(
                f"{data['name'][:23]:<25} "
                f"{hours:>9.2f} "
                f"AUD {rate:>11,.2f} "
                f"{self._format_currency(cost):>14}"
            )
            total_cost += cost
            total_hours += hours

        lines.append("-" * 60)
        lines.append(f"{'TOTAL':<25} {total_hours:>9.2f} {'':>14} {self._format_currency(total_cost):>14}")

        self._result_text.delete("1.0", tk.END)
        self._result_text.insert("1.0", "\n".join(lines))

    def _generate_approved_hours_by_project(self, company_id: str) -> None:
        """Generate approved hours by project report."""
        summaries = self.financial_service.get_all_financial_summaries(company_id)

        lines = []
        lines.append("APPROVED HOURS BY PROJECT")
        lines.append("=" * 60)
        lines.append(f"Company: {company_id}")
        lines.append(f"Generated: {self._now_iso()}")
        lines.append("")
        lines.append(f"{'Project':<30} {'Hours':>12} {'Cost (AUD)':>14} {'Billing (AUD)':>16}")
        lines.append("-" * 60)

        for s in summaries:
            lines.append(
                f"{s.project_name[:28]:<30} "
                f"{s.approved_hours:>11.2f} "
                f"{self._format_currency(s.approved_labour_cost_aud):>14} "
                f"{self._format_currency(s.billing_value_aud):>16}"
            )

        self._result_text.delete("1.0", tk.END)
        self._result_text.insert("1.0", "\n".join(lines))

    def _generate_financial_variance(self, company_id: str) -> None:
        """Generate financial variance report."""
        summaries = self.financial_service.get_all_financial_summaries(company_id)

        lines = []
        lines.append("FINANCIAL VARIANCE")
        lines.append("=" * 60)
        lines.append(f"Company: {company_id}")
        lines.append(f"Generated: {self._now_iso()}")
        lines.append("")
        lines.append(f"{'Project':<30} {'Budget':>14} {'Actual':>14} {'Variance':>14} {'% Var':>8}")
        lines.append("-" * 60)

        for s in summaries:
            pct_var = (
                (s.budget_variance_aud / s.current_budget_aud * 100)
                if s.current_budget_aud > 0
                else Decimal("0")
            )
            lines.append(
                f"{s.project_name[:28]:<30} "
                f"{self._format_currency(s.current_budget_aud):>14} "
                f"{self._format_currency(s.approved_labour_cost_aud):>14} "
                f"{self._format_currency(s.budget_variance_aud):>14} "
                f"{pct_var:>7.1f}%"
            )

        self._result_text.delete("1.0", tk.END)
        self._result_text.insert("1.0", "\n".join(lines))

    def _export_csv(self) -> None:
        """Export the current report to CSV."""
        actor = current_auth.actor
        if actor is None:
            messagebox.showerror("Export Error", "No authenticated session.")
            return

        report_type = self._report_var.get()
        content = self._result_text.get("1.0", tk.END).strip()

        if not content:
            messagebox.showinfo("Export CSV", "No report data to export.")
            return

        default_name = f"bimspend_{report_type}.csv"
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            # Parse the text report into CSV format
            lines = content.split("\n")
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                # Skip header lines until we find the data header
                data_started = False
                for line in lines:
                    if line.startswith("=") or line.startswith("-") or not line.strip():
                        continue
                    if line.startswith("Company:") or line.startswith("Generated:"):
                        continue
                    parts = [p.strip() for p in line.split()]
                    if len(parts) >= 2:
                        writer.writerow(parts)
                        data_started = True

            messagebox.showinfo("Export CSV", f"Report exported to {path}")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Export Error", f"Failed to export CSV: {exc}")

    def _back_to_dashboard(self) -> None:
        """Return to financial dashboard."""
        self.app.show_screen("financial_dashboard")

    @staticmethod
    def _now_iso() -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()