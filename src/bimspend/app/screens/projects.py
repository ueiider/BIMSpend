"""Projects screen - BIMSpend R1-08.

Lists all projects with key metrics. Clicking a project opens the
project detail view. Supports create/edit/archive via dialogs.
Uses the BIMSpend design system.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Any

from bimspend.app.design import (
    ACCENT_BLUE,
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
from bimspend.models import Project, TimeEntry, TimeEntryState


class ProjectsScreen(BaseScreen):
    """Projects list screen with create/edit/archive."""

    def __init__(self, parent: ttk.Widget, app: BIMSpendApp):
        super().__init__(parent, app)
        self.tree: ttk.Treeview | None = None

    def on_show(self) -> None:
        for widget in self.winfo_children():
            widget.destroy()
        self._build_ui()

    def _build_ui(self) -> None:
        app = self.app

        # Header
        self._section_header(
            "Projects", "Authorized projects with time and budget summary"
        )

        # Action bar
        action_frame = ttk.Frame(self, style="App.TFrame")
        action_frame.pack(fill="x", pady=(0, 16))

        ttk.Button(
            action_frame,
            text="+ New Project",
            command=self._new_project,
        ).pack(side="left")

        # Projects table
        self._build_projects_table()

    def _build_projects_table(self) -> None:
        entries = self.app.db.list_time_entries()
        projects = [p for p in self.app.projects if not p.is_archived]

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
        self.tree = ttk.Treeview(
            container,
            columns=columns,
            show="tree headings",
            height=15,
            style="App.Treeview",
        )

        self.tree.heading("#0", text="Project")
        self.tree.heading("name", text="Name")
        self.tree.heading("client", text="Client")
        self.tree.heading("status", text="Status")
        self.tree.heading("observed", text="Observed")
        self.tree.heading("attributed", text="Attributed")
        self.tree.heading("approved", text="Approved")
        self.tree.heading("billed", text="Billed")

        self.tree.column("#0", width=0, stretch=False)
        self.tree.column("name", width=200)
        self.tree.column("client", width=150)
        self.tree.column("status", width=100)
        self.tree.column("observed", width=90)
        self.tree.column("attributed", width=90)
        self.tree.column("approved", width=90)
        self.tree.column("billed", width=90)

        scrollbar = ttk.Scrollbar(
            container, orient="vertical", command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bind double-click to open project detail
        self.tree.bind("<Double-1>", self._on_project_double_click)

        # Bind right-click for context menu
        self.tree.bind("<Button-3>", self._on_project_right_click)

        # Populate rows
        self._populate_projects(projects, entries)

    def _populate_projects(
        self, projects: list[Project], entries: list[TimeEntry]
    ) -> None:
        """Populate the treeview with project rows."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        for project in projects:
            project_entries = [e for e in entries if e.project_id == project.id]
            approved_e = [
                e
                for e in project_entries
                if e.state in (TimeEntryState.APPROVED, TimeEntryState.BILLED)
            ]
            billed_e = [e for e in project_entries if e.state == TimeEntryState.BILLED]

            attributed = [
                a
                for a in self.db.list_attributed_time()
                if a.project_id == project.id
            ]
            attr_minutes = sum(a.attributed_minutes for a in attributed) / 60.0

            approved_hours = sum(e.minutes for e in approved_e) / 60.0
            billed_hours = sum(e.billed_minutes for e in billed_e) / 60.0
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
                    format_minutes(obs_hours * 60),
                    format_minutes(attr_minutes * 60),
                    format_minutes(approved_hours * 60),
                    format_minutes(billed_hours * 60),
                ),
                tags=(project.id, status.lower()),
            )

        # Configure status tag colors
        self.tree.tag_configure("active", foreground="#287E72")
        self.tree.tag_configure("internal", foreground="#8A97A5")

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
                self.app.show_screen("project_financial_detail")

    def _on_project_right_click(self, event: Any) -> None:
        """Show context menu on right-click."""
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)

        menu = tk.Menu(self, tearoff=0)
        project_id = self.tree.item(item, "tags")[0]
        project = self.app.db.get_project(project_id)

        menu.add_command(
            label="Edit Project", command=lambda: self._edit_project(project_id)
        )
        menu.add_command(
            label="Archive Project", command=lambda: self._archive_project(project_id)
        )
        menu.add_separator()
        menu.add_command(
            label="Open Detail",
            command=lambda: self._open_project(project_id),
        )

        menu.tk_popup(event.x_root, event.y_root)

    def _open_project(self, project_id: str) -> None:
        project = self.app.db.get_project(project_id)
        if project:
            self.app.set_project(project)
            self.app.show_screen("project_financial_detail")

    def _new_project(self) -> None:
        """Create a new project via dialog."""
        dialog = ProjectDialog(self, self.app)
        if dialog.result:
            project = dialog.result
            self.db.upsert_project(project)
            self.app.projects = self.db.list_projects()
            self._populate_projects(
                self.app.projects, self.app.db.list_time_entries()
            )

    def _edit_project(self, project_id: str) -> None:
        """Edit an existing project."""
        project = self.app.db.get_project(project_id)
        if not project:
            return
        dialog = ProjectDialog(self, self.app, project)
        if dialog.result:
            self.db.upsert_project(dialog.result)
            self.app.projects = self.db.list_projects()
            self._populate_projects(
                self.app.projects, self.app.db.list_time_entries()
            )

    def _archive_project(self, project_id: str) -> None:
        """Archive (soft-delete) a project."""
        project = self.app.db.get_project(project_id)
        if not project:
            return

        confirm = messagebox.askyesno(
            "Archive Project",
            f"Archive project '{project.name}'?\n\n"
            "Archived projects are hidden from the active list but "
            "their time entries are preserved.",
        )
        if not confirm:
            return

        project.is_archived = True
        self.db.upsert_project(project)
        self.app.projects = self.db.list_projects()
        self._populate_projects(
            self.app.projects, self.app.db.list_time_entries()
        )


class ProjectDialog(tk.Toplevel):
    """Dialog for creating or editing a project."""

    def __init__(
        self, parent: ttk.Widget, app: BIMSpendApp, project: Project | None = None
    ):
        super().__init__(parent)
        self.app = app
        self.project = project
        self.result: Project | None = None

        self.title("New Project" if project is None else "Edit Project")
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        if project:
            self._load_project(project)

        self.wait_window(self)

    def _build_ui(self) -> None:
        frame = ttk.Frame(self, style="App.TFrame")
        frame.pack(fill="both", expand=True, padx=24, pady=24)

        ttk.Label(
            frame, text="Project Name", style="MetricLabel.TLabel"
        ).pack(anchor="w")
        self.name_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.name_var, width=40).pack(
            fill="x", pady=(4, 12)
        )

        ttk.Label(frame, text="Client", style="MetricLabel.TLabel").pack(anchor="w")
        self.client_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.client_var, width=40).pack(
            fill="x", pady=(4, 12)
        )

        ttk.Label(
            frame, text="Standard Rate (A$/hour)", style="MetricLabel.TLabel"
        ).pack(anchor="w")
        self.rate_var = tk.StringVar(value="150.00")
        ttk.Entry(frame, textvariable=self.rate_var, width=40).pack(
            fill="x", pady=(4, 12)
        )

        ttk.Label(
            frame, text="Loaded Cost Rate (A$/hour)", style="MetricLabel.TLabel"
        ).pack(anchor="w")
        self.cost_var = tk.StringVar(value="85.00")
        ttk.Entry(frame, textvariable=self.cost_var, width=40).pack(
            fill="x", pady=(4, 12)
        )

        ttk.Label(
            frame, text="Labor Budget (AUD, optional)", style="MetricLabel.TLabel"
        ).pack(anchor="w")
        self.budget_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.budget_var, width=40).pack(
            fill="x", pady=(4, 12)
        )

        self.is_billable_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame,
            text="Billable project",
            variable=self.is_billable_var,
        ).pack(anchor="w", pady=(12, 0))

        btn_frame = ttk.Frame(frame, style="App.TFrame")
        btn_frame.pack(fill="x", pady=(24, 0))

        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(
            side="right", padx=(8, 0)
        )
        ttk.Button(btn_frame, text="Save", command=self._save).pack(side="right")

    def _load_project(self, project: Project) -> None:
        self.name_var.set(project.name)
        self.client_var.set(project.client)
        self.rate_var.set(f"{project.standard_rate:.2f}")
        self.cost_var.set(f"{project.loaded_cost_rate:.2f}")
        self.is_billable_var.set(project.is_billable)
        self.budget_var.set(
            "" if project.budget_aud is None else f"{project.budget_aud:.2f}"
        )

    def _save(self) -> None:
        name = self.name_var.get().strip()
        client = self.client_var.get().strip()

        if not name:
            messagebox.showerror("Validation Error", "Project name is required.")
            return
        if not client:
            messagebox.showerror("Validation Error", "Client is required.")
            return

        try:
            rate = float(self.rate_var.get())
            cost = float(self.cost_var.get())
            budget = (
                float(self.budget_var.get())
                if self.budget_var.get().strip()
                else None
            )
        except ValueError:
            messagebox.showerror("Validation Error", "Rate and cost must be numeric.")
            return

        import math

        if (
            not math.isfinite(rate)
            or not math.isfinite(cost)
            or rate < 0
            or cost < 0
            or (budget is not None and (not math.isfinite(budget) or budget < 0))
        ):
            messagebox.showerror("Validation Error", "Rates must not be negative.")
            return

        if self.project:
            self.project.name = name
            self.project.client = client
            self.project.standard_rate = rate
            self.project.loaded_cost_rate = cost
            self.project.is_billable = self.is_billable_var.get()
            self.project.budget_aud = budget
            self.result = self.project
        else:
            import uuid

            self.result = Project(
                id=f"proj_{uuid.uuid4().hex}",
                name=name,
                client=client,
                standard_rate=rate,
                loaded_cost_rate=cost,
                is_billable=self.is_billable_var.get(),
                budget_aud=budget,
            )

        self.destroy()
