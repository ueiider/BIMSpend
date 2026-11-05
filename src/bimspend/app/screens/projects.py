"""Projects screen.

Lists all projects with key metrics. Clicking a project opens the
project detail view.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from bimspend.app.screens.base import BaseScreen
from bimspend.app.shell import BIMSpendApp
from bimspend.models import Project, TimeEntry, TimeEntryState


class ProjectsScreen(BaseScreen):
    """Projects list screen."""

    def __init__(self, parent: ttk.Widget, app: BIMSpendApp):
        super().__init__(parent, app)

    def on_show(self) -> None:
        for widget in self.winfo_children():
            widget.destroy()
        self._build_ui()

    def _build_ui(self) -> None:
        app = self.app

        # Header
        self._section_header("Projects", "Authorized projects with time and budget summary")

        # Action bar
        action_frame = ttk.Frame(self, style="App.TFrame")
        action_frame.pack(fill="x", pady=(0, 16))

        ttk.Button(
            action_frame,
            text="+ New Project",
            style="Nav.TButton",
            command=self._new_project,
        ).pack(side="left")

        # Projects table
        self._build_projects_table()

    def _build_projects_table(self) -> None:
        entries = self.app.db.list_time_entries()
        projects = self.app.projects

        # Table container with scrollbar
        container = ttk.Frame(self, style="App.TFrame")
        container.pack(fill="both", expand=True)

        # Treeview
        columns = ("name", "client", "status", "observed", "attributed", "approved", "billed")
        self.tree = ttk.Treeview(container, columns=columns, show="tree headings", height=15)

        self.tree.heading("#0", text="Project")
        self.tree.heading("name", text="Name")
        self.tree.heading("client", text="Client")
        self.tree.heading("status", text="Status")
        self.tree.heading("observed", text="Observed (h)")
        self.tree.heading("attributed", text="Attributed (h)")
        self.tree.heading("approved", text="Approved (h)")
        self.tree.heading("billed", text="Billed (h)")

        self.tree.column("#0", width=150)
        self.tree.column("name", width=200)
        self.tree.column("client", width=150)
        self.tree.column("status", width=100)
        self.tree.column("observed", width=100)
        self.tree.column("attributed", width=100)
        self.tree.column("approved", width=100)
        self.tree.column("billed", width=100)

        # Scrollbar
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bind double-click to open project detail
        self.tree.bind("<Double-1>", self._on_project_double_click)

        # Populate rows
        for project in projects:
            project_entries = [e for e in entries if e.project_id == project.id]
            approved_e = [e for e in project_entries if e.state == TimeEntryState.APPROVED]
            billed_e = [e for e in project_entries if e.state == TimeEntryState.BILLED]

            attributed = [a for a in self.db.list_attributed_time() if a.project_id == project.id]
            attr_minutes = sum(a.attributed_minutes for a in attributed) / 60.0

            approved_hours = sum(e.minutes for e in approved_e) / 60.0
            billed_hours = sum(e.billed_minutes for e in billed_e) / 60.0

            # Observed = attributed as proxy in demo
            obs_hours = attr_minutes

            status = "Active" if project.is_billable else "Internal"

            self.tree.insert(
                "",
                "end",
                text=project.name,
                values=(
                    project.name,
                    project.client,
                    status,
                    f"{obs_hours:.1f}",
                    f"{attr_minutes:.1f}",
                    f"{approved_hours:.1f}",
                    f"{billed_hours:.1f}",
                ),
                tags=(project.id,),
            )

    def _on_project_double_click(self, event: Any) -> None:
        """Open project detail when double-clicked."""
        selection = self.tree.selection()
        if not selection:
            return
        item = self.tree.item(selection[0])
        project_id = item["tags"][0] if item["tags"] else None
        if project_id:
            project = self.app.db.get_project(project_id)
            if project:
                self.app.set_project(project)
                self.app.show_screen("project_detail")

    def _new_project(self) -> None:
        """Placeholder for new project creation."""
        from tkinter import messagebox
        messagebox.showinfo(
            "New Project",
            "Project creation form\n\n(Placeholder — full CRUD in later phase)\n\n"
            "Fields would include: project name, client, standard rate, "
            "loaded cost rate, budget hours, status.",
        )
