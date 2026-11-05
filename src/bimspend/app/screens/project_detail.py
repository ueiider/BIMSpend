"""Project detail screen.

Shows project summary with budget vs actual, time breakdown by state,
and recent activity.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from bimspend.app.screens.base import BaseScreen
from bimspend.app.shell import BIMSpendApp
from bimspend.models import Project, TimeEntry, TimeEntryState
from bimspend.dashboard import project_summary


class ProjectDetailScreen(BaseScreen):
    """Project detail view with metrics, timeline, and review."""

    def __init__(self, parent: ttk.Widget, app: BIMSpendApp):
        super().__init__(parent, app)
        self.current_project: Project | None = None

    def on_show(self) -> None:
        for widget in self.winfo_children():
            widget.destroy()
        self._build_ui()

    def _build_ui(self) -> None:
        app = self.app
        project = app.current_project

        if not project:
            ttk.Label(
                self, text="No project selected", style="Title.TLabel"
            ).pack(expand=True)
            return

        self.current_project = project

        # Header
        self._section_header(project.name, f"Client: {project.client}  ·  ID: {project.id}")

        # Back button
        ttk.Button(
            self,
            text="← Back to Projects",
            command=lambda: app.show_screen("projects"),
        ).pack(anchor="w", pady=(0, 16))

        # Metric row
        entries = app.db.list_time_entries()
        project_entries = [e for e in entries if e.project_id == project.id]

        attributed = [a for a in app.db.list_attributed_time() if a.project_id == project.id]
        attr_minutes = sum(a.attributed_minutes for a in attributed)

        # Observed (use attributed as proxy in demo)
        obs_minutes = attr_minutes

        summary = project_summary(
            project, obs_minutes, attr_minutes, project_entries
        )

        # Metric cards row
        metrics_frame = ttk.Frame(self, style="App.TFrame")
        metrics_frame.pack(fill="x", pady=(0, 24))

        cards = [
            ("Observed Hours", f"{summary['observed_hours']}", "ActivityWatch"),
            ("Attributed Hours", f"{summary['attributed_hours']}", "Correlated"),
            ("Approved Hours", f"{summary['approved_hours']}", "Manager-approved"),
            ("Billed Hours", f"{summary['billed_hours']}", "Invoiced"),
            ("Labor Cost", f"A${summary['labor_cost_aud']}", "Internal loaded cost"),
            ("Labor Budget", ("A$" + format(summary["budget_aud"], ".2f")) if summary["budget_aud"] is not None else "Not set", "Approved cost basis"),
            ("Budget Remaining", ("A$" + format(summary["budget_remaining_aud"], ".2f")) if summary["budget_remaining_aud"] is not None else "Not set", "May be negative"),
            ("Standard Value", f"A${summary['standard_value_aud']}", "Client charge value"),
        ]

        for i, (label, value, sublabel) in enumerate(cards):
            card = ttk.Frame(metrics_frame, style="Card.TFrame")
            card.grid(row=0, column=i, padx=4, pady=4, sticky="ew")
            metrics_frame.columnconfigure(i, weight=1)

            inner = ttk.Frame(card, style="Card.TFrame")
            inner.pack(fill="both", expand=True, padx=14, pady=10)

            ttk.Label(inner, text=label, style="MetricLabel.TLabel").pack(anchor="w")
            ttk.Label(
                inner, text=value, style="MetricValue.TLabel", foreground="#14324A"
            ).pack(anchor="w", pady=(2, 0))
            ttk.Label(inner, text=sublabel, style="MetricLabel.TLabel").pack(anchor="w")

        self._divider()

        # Time entries table
        self._section_header("Time Entries", f"Entries for {project.name}")

        entries_table = ttk.Frame(self, style="App.TFrame")
        entries_table.pack(fill="both", expand=True)

        cols = ("Date", "User", "Minutes", "State", "Standard Rate", "Loaded Cost")
        self.entries_tree = ttk.Treeview(entries_table, columns=cols, show="headings", height=10)

        for col in cols:
            self.entries_tree.heading(col, text=col)
            self.entries_tree.column(col, width=120)

        scrollbar = ttk.Scrollbar(entries_table, orient="vertical", command=self.entries_tree.yview)
        self.entries_tree.configure(yscrollcommand=scrollbar.set)

        self.entries_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Populate entries
        for entry in sorted(project_entries, key=lambda e: e.created_at or "", reverse=True):
            self.entries_tree.insert(
                "",
                "end",
                values=(
                    entry.created_at[:10] if entry.created_at else "",
                    entry.user_id,
                    f"{entry.minutes:.0f}",
                    entry.state.value.replace("_", " ").title(),
                    f"A${entry.standard_rate:.0f}/h",
                    f"A${entry.loaded_cost_rate:.0f}/h",
                ),
            )

    def _divider(self) -> ttk.Separator:
        sep = ttk.Separator(self, orient="horizontal")
        sep.pack(fill="x", pady=16)
        return sep
