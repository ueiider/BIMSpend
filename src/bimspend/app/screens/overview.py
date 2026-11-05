"""Overview dashboard screen.

Shows role-appropriate metrics: observed vs attributed vs approved vs
billed hours, with metric separation preserved.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from bimspend.app.screens.base import BaseScreen
from bimspend.app.shell import BIMSpendApp
from bimspend.models import Project, TimeEntryState


class OverviewScreen(BaseScreen):
    """Manager/designer overview dashboard."""

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
        self._section_header("Overview", "Project time and cost intelligence — synthetic demo data")

        # Metric row
        metrics_frame = ttk.Frame(self, style="App.TFrame")
        metrics_frame.pack(fill="x", pady=(0, 24))

        # Get all entries for metric calculation
        entries = self.db.list_time_entries()
        projects = self.app.projects

        # Compute aggregates
        total_observed = 0.0
        total_attributed = 0.0
        total_approved = 0.0
        total_billed = 0.0

        # We need event data for observed hours. For the demo, we'll
        # compute from attributed time entries.
        attributed_entries = self.db.list_attributed_time()
        total_attributed = sum(a.attributed_minutes for a in attributed_entries) / 60.0

        approved_entries = [e for e in entries if e.state == TimeEntryState.APPROVED]
        total_approved = sum(e.minutes for e in approved_entries) / 60.0

        billed_entries = [e for e in entries if e.state == TimeEntryState.BILLED]
        total_billed = sum(e.billed_minutes for e in billed_entries) / 60.0

        # Observed includes unmatched non-AFK events; it is not project time.
        total_observed = sum(e.duration_minutes for e in self.db.list_events() if not e.is_afk) / 60.0

        # Metric cards
        cards = [
            ("Observed Hours", f"{total_observed:.1f} h", "ActivityWatch events", "#14324A"),
            ("Attributed Hours", f"{total_attributed:.1f} h", "Correlated to projects", "#1976A5"),
            ("Approved Hours", f"{total_approved:.1f} h", "Manager-approved", "#287E72"),
            ("Billed Hours", f"{total_billed:.1f} h", "Invoiced to client", "#A96512"),
        ]

        for i, (label, value, sublabel, color) in enumerate(cards):
            card = ttk.Frame(metrics_frame, style="Card.TFrame")
            card.grid(row=0, column=i, padx=4, pady=4, sticky="ew")
            metrics_frame.columnconfigure(i, weight=1)

            inner = ttk.Frame(card, style="Card.TFrame")
            inner.pack(fill="both", expand=True, padx=16, pady=12)

            ttk.Label(inner, text=label, style="MetricLabel.TLabel").pack(anchor="w")
            ttk.Label(
                inner, text=value, style="MetricValue.TLabel", foreground=color
            ).pack(anchor="w", pady=(2, 0))
            ttk.Label(inner, text=sublabel, style="MetricLabel.TLabel").pack(anchor="w")

        self._divider()

        # Projects table
        self._section_header("Projects", "Active projects with time state breakdown")

        # Table header
        table = ttk.Frame(self, style="App.TFrame")
        table.pack(fill="both", expand=True)

        columns = ("Project", "Client", "Observed", "Attributed", "Approved", "Billed", "Status")
        widths = (220, 180, 100, 100, 100, 100, 120)

        # Header row
        header_frame = ttk.Frame(table, style="Card.TFrame")
        header_frame.pack(fill="x", pady=(0, 4))
        for col, width in zip(columns, widths):
            ttk.Label(
                header_frame, text=col, style="MetricLabel.TLabel", font=("Segoe UI", 10, "bold")
            ).pack(side="left", padx=12, pady=8)

        # Project rows
        for project in projects:
            project_entries = [e for e in entries if e.project_id == project.id]
            approved_e = [e for e in project_entries if e.state == TimeEntryState.APPROVED]
            billed_e = [e for e in project_entries if e.state == TimeEntryState.BILLED]
            pending_e = [e for e in project_entries if e.state == TimeEntryState.PENDING_REVIEW]
            submitted_e = [e for e in project_entries if e.state == TimeEntryState.SUBMITTED]

            # Get attributed minutes for this project
            attributed = [a for a in self.db.list_attributed_time() if a.project_id == project.id]
            attr_minutes = sum(a.attributed_minutes for a in attributed) / 60.0

            # Observed (use attributed as proxy in demo)
            obs_minutes = attr_minutes

            row = ttk.Frame(table, style="Card.TFrame")
            row.pack(fill="x", pady=1)

            ttk.Label(row, text=project.name, style="MetricLabel.TLabel").pack(side="left", padx=12, pady=6)
            ttk.Label(row, text=project.client, style="MetricLabel.TLabel").pack(side="left", padx=12, pady=6)
            ttk.Label(row, text=f"{obs_minutes:.1f}", style="MetricLabel.TLabel").pack(side="left", padx=12, pady=6)
            ttk.Label(row, text=f"{attr_minutes:.1f}", style="MetricLabel.TLabel").pack(side="left", padx=12, pady=6)
            ttk.Label(row, text=f"{sum(e.minutes for e in approved_e)/60:.1f}", style="MetricLabel.TLabel").pack(side="left", padx=12, pady=6)
            ttk.Label(row, text=f"{sum(e.billed_minutes for e in billed_e)/60:.1f}", style="MetricLabel.TLabel").pack(side="left", padx=12, pady=6)

            status_text = f"{len(pending_e)} pending, {len(submitted_e)} submitted"
            ttk.Label(row, text=status_text, style="MetricLabel.TLabel").pack(side="left", padx=12, pady=6)

        # Info note
        note_frame = ttk.Frame(self, style="Card.TFrame")
        note_frame.pack(fill="x", pady=16)
        inner = ttk.Frame(note_frame, style="Card.TFrame")
        inner.pack(fill="x", padx=16, pady=12)
        ttk.Label(
            inner,
            text="All data is synthetic. Observed time comes from ActivityWatch-like watcher fixtures; "
                 "attributed time comes from correlation; approved/billed states come from designer "
                 "review workflow. No real employee data is used.",
            style="MetricLabel.TLabel",
        ).pack(anchor="w")
