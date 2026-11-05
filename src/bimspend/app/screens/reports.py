"""Local project, team, timesheet and cost reports."""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from bimspend.app.screens.base import BaseScreen
from bimspend.reporting import HEADERS, aggregate, build_report, export_csv


class ReportsScreen(BaseScreen):
    def on_show(self) -> None:
        for widget in self.winfo_children():
            widget.destroy()
        self._section_header("Reports", "Synthetic data; local CSV export")
        filters = ttk.Frame(self, style="App.TFrame")
        filters.pack(fill="x", pady=8)
        self.section = tk.StringVar(value="Timesheets")
        ttk.Combobox(filters, textvariable=self.section,
                     values=["Timesheets", "Projects", "Team", "Costs"],
                     state="readonly", width=16).pack(side="left", padx=4)
        self.start = tk.StringVar()
        self.end = tk.StringVar()
        for label, var in (("From YYYY-MM-DD", self.start),
                           ("To YYYY-MM-DD", self.end)):
            ttk.Label(filters, text=label).pack(side="left", padx=4)
            ttk.Entry(filters, textvariable=var, width=13).pack(side="left")
        ttk.Button(filters, text="Generate", command=self._generate).pack(side="left", padx=4)
        ttk.Button(filters, text="Export CSV", command=self._export).pack(side="left")
        columns = ("project_name", "user_id", "work_date", "state",
                   "confirmed_hours", "approved_hours", "billed_hours",
                   "labor_cost_aud", "billed_value_aud", "budget_aud")
        self.columns = columns
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=16)
        for col in columns:
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=115)
        self.tree.pack(fill="both", expand=True)
        self.rows = []
        self._generate()

    def _generate(self) -> None:
        try:
            rows = build_report(self.db, self.start.get().strip() or None,
                                self.end.get().strip() or None)
            self.rows = rows if self.section.get() == "Timesheets" else aggregate(
                rows, self.section.get())
            for item in self.tree.get_children():
                self.tree.delete(item)
            for row in self.rows:
                self.tree.insert("", "end",
                                 values=[row.get(c, "") if row.get(c) is not None else ""
                                         for c in self.columns])
        except ValueError as exc:
            messagebox.showerror("Report filter", str(exc))

    def _export(self) -> None:
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if filename:
            export_csv(filename, self.rows)
            messagebox.showinfo("Report", "CSV saved locally.")
