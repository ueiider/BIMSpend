"""Reports and Analytics screen - BIMSpend R1-08.

Local project, team, timesheet and cost reports.
Uses the BIMSpend design system.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

from bimspend.app.design import (
    APP_BG,
    CARD_BG,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from bimspend.app.screens.base import BaseScreen
from bimspend.app.shell import BIMSpendApp
from bimspend.reporting import HEADERS, aggregate, build_report, export_csv


class ReportsScreen(BaseScreen):
    """Reports and analytics with CSV export."""

    def __init__(self, parent: ttk.Widget, app: BIMSpendApp):
        super().__init__(parent, app)

    def on_show(self) -> None:
        for widget in self.winfo_children():
            widget.destroy()
        self._section_header(
            "Reports", "Synthetic data; local CSV export"
        )
        self._build_filters()
        self._build_table()
        self._generate()

    def _build_filters(self) -> None:
        filters = ttk.Frame(self, style="App.TFrame")
        filters.pack(fill="x", pady=8)

        self.section = tk.StringVar(value="Timesheets")
        ttk.Combobox(
            filters,
            textvariable=self.section,
            values=["Timesheets", "Projects", "Team", "Costs"],
            state="readonly",
            width=16,
        ).pack(side="left", padx=4)

        self.start = tk.StringVar()
        self.end = tk.StringVar()
        for label, var in (("From YYYY-MM-DD", self.start),
                           ("To YYYY-MM-DD", self.end)):
            ttk.Label(filters, text=label).pack(side="left", padx=4)
            ttk.Entry(filters, textvariable=var, width=13).pack(side="left")

        ttk.Button(
            filters, text="Generate", command=self._generate
        ).pack(side="left", padx=4)
        ttk.Button(
            filters, text="Export CSV", command=self._export
        ).pack(side="left")

    def _build_table(self) -> None:
        columns = (
            "project_name", "user_id", "work_date", "state",
            "confirmed_hours", "approved_hours", "billed_hours",
            "labor_cost_aud", "billed_value_aud", "budget_aud",
        )
        self.columns = columns
        self.tree = ttk.Treeview(
            self,
            columns=columns,
            show="headings",
            height=16,
            style="App.Treeview",
        )
        for col in columns:
            self.tree.heading(
                col, text=col.replace("_", " ").title()
            )
            self.tree.column(col, width=115)
        self.tree.pack(fill="both", expand=True)
        self.rows = []

    def _generate(self) -> None:
        try:
            rows = build_report(
                self.db,
                self.start.get().strip() or None,
                self.end.get().strip() or None,
            )
            self.rows = rows if self.section.get() == "Timesheets" else aggregate(
                rows, self.section.get()
            )
            for item in self.tree.get_children():
                self.tree.delete(item)
            for row in self.rows:
                self.tree.insert(
                    "",
                    "end",
                    values=[
                        row.get(c, "") if row.get(c) is not None else ""
                        for c in self.columns
                    ],
                )
        except ValueError as exc:
            messagebox.showerror("Report filter", str(exc))

    def _export(self) -> None:
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
        )
        if filename:
            export_csv(filename, self.rows)
            messagebox.showinfo("Report", "CSV saved locally.")
