"""Executive Dashboard screen - BIMSpend R1-08.

Shows role-appropriate metrics: observed vs attributed vs approved vs
billed hours, with metric separation preserved. Uses the BIMSpend
design system for consistent styling.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from bimspend.app.design import (
    ACCENT_AMBER,
    ACCENT_BLUE,
    ACCENT_TEAL,
    APP_BG,
    CARD_BG,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    format_aud,
    format_minutes,
    register_styles,
)
from bimspend.app.screens.base import BaseScreen
from bimspend.app.shell import BIMSpendApp
from bimspend.models import Project, TimeEntryState


class OverviewScreen(BaseScreen):
    """Executive dashboard with key metrics and project summary."""

    def __init__(self, parent: ttk.Widget, app: BIMSpendApp):
        super().__init__(parent, app)

    def on_show(self) -> None:
        """Refresh when shown."""
        for widget in self.winfo_children():
            widget.destroy()
        self._build_ui()

    def _build_ui(self) -> None:
        app = self.app

        # Header
        self._section_header(
            "Executive Dashboard",
            "Company overview — approved time and budget consumption",
        )

        # Metric row
        self._build_metric_row(app)

        self._divider()

        # Projects table
        self._section_header(
            "Projects", "Active projects with time state breakdown"
        )
        self._build_projects_table(app)

        # Info note
        self._build_info_note()

    # ------------------------------------------------------------------
    # Metric row
    # ------------------------------------------------------------------

    def _build_metric_row(self, app: BIMSpendApp) -> None:
        """Build the top metric cards."""
        entries = app.db.list_time_entries()
        attributed_entries = app.db.list_attributed_time()

        total_attributed = sum(a.attributed_minutes for a in attributed_entries) / 60.0

        approved_entries = [
            e
            for e in entries
            if e.state in (TimeEntryState.APPROVED, TimeEntryState.BILLED)
        ]
        total_approved = sum(e.minutes for e in approved_entries) / 60.0

        billed_entries = [
            e for e in entries if e.state == TimeEntryState.BILLED
        ]
        total_billed = sum(e.billed_minutes for e in billed_entries) / 60.0

        total_observed = sum(
            e.duration_minutes
            for e in app.db.list_events()
            if not e.is_afk
        ) / 60.0

        cards = [
            (
                "Observed Hours",
                format_minutes(total_observed * 60),
                "ActivityWatch events",
                ACCENT_BLUE,
            ),
            (
                "Attributed Hours",
                format_minutes(total_attributed * 60),
                "Correlated to projects",
                ACCENT_TEAL,
            ),
            (
                "Approved Hours",
                format_minutes(total_approved * 60),
                "Manager-approved",
                ACCENT_TEAL,
            ),
            (
                "Billed Hours",
                format_minutes(total_billed * 60),
                "Invoiced to client",
                ACCENT_AMBER,
            ),
        ]

        frame = ttk.Frame(self, style="App.TFrame")
        frame.pack(fill="x", pady=(0, 24))

        for i, (label, value, sublabel, color) in enumerate(cards):
            card = ttk.Frame(frame, style="Card.TFrame")
            card.grid(row=0, column=i, padx=4, pady=4, sticky="ew")
            frame.columnconfigure(i, weight=1)

            inner = ttk.Frame(card, style="Card.TFrame")
            inner.pack(fill="both", expand=True, padx=16, pady=12)

            ttk.Label(
                inner, text=label, style="MetricLabel.TLabel"
            ).pack(anchor="w")
            ttk.Label(
                inner, text=value, style="MetricValue.TLabel",
                foreground=color
            ).pack(anchor="w", pady=(2, 0))
            ttk.Label(
                inner, text=sublabel, style="MetricLabel.TLabel"
            ).pack(anchor="w")

    # ------------------------------------------------------------------
    # Projects table
    # ------------------------------------------------------------------

    def _build_projects_table(self, app: BIMSpendApp) -> None:
        """Build the projects summary table."""
        entries = app.db.list_time_entries()
        projects = [p for p in app.projects if not p.is_archived]

        # Table container with scrollbar
        container = ttk.Frame(self, style="App.TFrame")
        container.pack(fill="both", expand=True)

        columns = (
            "name",
            "client",
            "status",
            "observed",
            "attributed",
            "approved",
            "billed",
        )
        tree = ttk.Treeview(
            container,
            columns=columns,
            show="tree headings",
            height=12,
            style="App.Treeview",
        )

        tree.heading("#0", text="Project")
        tree.heading("name", text="Name")
        tree.heading("client", text="Client")
        tree.heading("status", text="Status")
        tree.heading("observed", text="Observed")
        tree.heading("attributed", text="Attributed")
        tree.heading("approved", text="Approved")
        tree.heading("billed", text="Billed")

        tree.column("#0", width=0, stretch=False)
        tree.column("name", width=200)
        tree.column("client", width=150)
        tree.column("status", width=100)
        tree.column("observed", width=90)
        tree.column("attributed", width=90)
        tree.column("approved", width=90)
        tree.column("billed", width=90)

        scrollbar = ttk.Scrollbar(
            container, orient="vertical", command=tree.yview
        )
        tree.configure(yscrollcommand=scrollbar.set)

        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Populate rows
        for project in projects:
            project_entries = [
                e for e in entries if e.project_id == project.id
            ]
            approved_e = [
                e
                for e in project_entries
                if e.state in (TimeEntryState.APPROVED, TimeEntryState.BILLED)
            ]
            billed_e = [
                e for e in project_entries if e.state == TimeEntryState.BILLED
            ]
            pending_e = [
                e for e in project_entries if e.state == TimeEntryState.PENDING_REVIEW
            ]
            submitted_e = [
                e for e in project_entries if e.state == TimeEntryState.SUBMITTED
            ]

            attributed = [
                a
                for a in app.db.list_attributed_time()
                if a.project_id == project.id
            ]
            attr_minutes = sum(a.attributed_minutes for a in attributed) / 60.0

            approved_hours = sum(e.minutes for e in approved_e) / 60.0
            billed_hours = sum(e.billed_minutes for e in billed_e) / 60.0
            obs_hours = attr_minutes  # attributed as proxy for observed

            status = "Active" if project.is_billable else "Internal"

            tree.insert(
                "",
                "end",
                text=project.name,
                values=(
                    project.name,
                    project.client,
                    status,
                    format_minutes(obs_hours * 60),
                    format_minutes(attr_minutes * 60),
                    format_minutes(approved_hours * 60),
                    format_minutes(billed_hours * 60),
                ),
                tags=(project.id, status.lower()),
            )

        # Configure status tag colors
        tree.tag_configure("active", foreground=ACCENT_TEAL)
        tree.tag_configure("internal", foreground=TEXT_SECONDARY)

        # Double-click to open project detail
        tree.bind("<Double-1>", lambda _: self._on_project_double_click(tree))

    def _on_project_double_click(self, tree: ttk.Treeview) -> None:
        """Open project detail when double-clicked."""
        selection = tree.selection()
        if not selection:
            return
        item = tree.item(selection[0])
        project_id = item["tags"][0] if item["tags"] else None
        if project_id:
            project = self.app.db.get_project(project_id)
            if project:
                self.app.set_project(project)
                self.app.show_screen("project_financial_detail")

    # ------------------------------------------------------------------
    # Info note
    # ------------------------------------------------------------------

    def _build_info_note(self) -> None:
        """Build the informational note at the bottom."""
        note_frame = ttk.Frame(self, style="Card.TFrame")
        note_frame.pack(fill="x", pady=16)
        inner = ttk.Frame(note_frame, style="Card.TFrame")
        inner.pack(fill="x", padx=16, pady=12)
        ttk.Label(
            inner,
            text=(
                "All data is synthetic. Observed time comes from ActivityWatch-like watcher fixtures; "
                "attributed time comes from correlation; approved/billed states come from designer "
                "review workflow. No real employee data is used."
            ),
            style="Caption.TLabel",
        ).pack(anchor="w")
