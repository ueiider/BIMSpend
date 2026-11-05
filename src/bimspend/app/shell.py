"""BIMSpend desktop application shell.

Main window with sidebar navigation, header/workspace context, and
screen manager. All navigation and actions route through the domain
layer (models, db, adapters, correlation, review, dashboard).

Design tokens follow the UI specification in docs/product-design/.
"""

from __future__ import annotations

import json
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any

from bimspend.db import Database
from bimspend.models import Project, ActivityEvent, TimeEntryState
from bimspend.dashboard import all_projects_summary


def _fixture(name: str) -> str:
    """Resolve path to a synthetic fixture file."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "data", "synthetic", name)
    return os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "synthetic", name)


class BIMSpendApp:
    """Main BIMSpend application window.

    Provides:
      - Left rail: workspace logo/name, role-aware navigation, Settings
      - Top bar: workspace name, breadcrumbs, user menu
      - Main content: screen canvas with page header and content
      - Status bar: capture state and sync state indicators
    """

    def __init__(self, root: tk.Tk | None = None, db_path: str = "bimspend.db"):
        self.root = root or tk.Tk()
        self.root.title("BIMSpend — Project Time & Cost Intelligence")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)

        # Domain layer
        self.db = Database(db_path)
        self.current_user = "designer_01"  # provisional; real auth later
        self.current_project: Project | None = None

        # Style
        self._setup_styles()

        # Layout
        self._build_shell()

        # Load data
        self._load_data()

        # Show overview screen
        self.show_screen("overview")

    # ------------------------------------------------------------------
    # Styling
    # ------------------------------------------------------------------
    def _setup_styles(self) -> None:
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # Design tokens (from UI spec)
        self.style.configure("App.TFrame", background="#F4F7F9")
        self.style.configure("Sidebar.TFrame", background="#14324A")
        self.style.configure("Header.TFrame", background="#FFFFFF")
        self.style.configure("Card.TFrame", background="#FFFFFF", relief="solid", borderwidth=1)

        self.style.configure(
            "Nav.TButton",
            background="#14324A",
            foreground="#FFFFFF",
            borderwidth=0,
            focuscolor="#1976A5",
            anchor="w",
            padding=(16, 10),
            font=("Segoe UI", 11),
        )
        self.style.map(
            "Nav.TButton",
            background=[("active", "#1976A5"), ("pressed", "#0E2A3A")],
            foreground=[("active", "#FFFFFF"), ("pressed", "#FFFFFF")],
        )

        self.style.configure("Title.TLabel", background="#F4F7F9", foreground="#172B3A", font=("Segoe UI", 20, "bold"))
        self.style.configure("Subtitle.TLabel", background="#F4F7F9", foreground="#4A6572", font=("Segoe UI", 12))
        self.style.configure("MetricValue.TLabel", background="#FFFFFF", foreground="#14324A", font=("Segoe UI", 24, "bold"))
        self.style.configure("MetricLabel.TLabel", background="#FFFFFF", foreground="#4A6572", font=("Segoe UI", 10))
        self.style.configure("Status.TLabel", background="#FFFFFF", foreground="#287E72", font=("Segoe UI", 10, "bold"))

    # ------------------------------------------------------------------
    # Shell layout
    # ------------------------------------------------------------------
    def _build_shell(self) -> None:
        # Container
        self.container = ttk.Frame(self.root, style="App.TFrame")
        self.container.pack(fill="both", expand=True)

        # Sidebar
        self.sidebar = ttk.Frame(self.container, style="Sidebar.TFrame", width=260)
        self.sidebar.pack(side="left", fill="y", padx=0, pady=0)
        self.sidebar.pack_propagate(False)

        # Logo / workspace
        self.logo_frame = ttk.Frame(self.sidebar, style="Sidebar.TFrame")
        self.logo_frame.pack(fill="x", padx=20, pady=(24, 16))

        self.logo_label = ttk.Label(
            self.logo_frame,
            text="BIMSpend",
            foreground="#FFFFFF",
            background="#14324A",
            font=("Segoe UI", 18, "bold"),
        )
        self.logo_label.pack(anchor="w")

        self.subtitle_label = ttk.Label(
            self.logo_frame,
            text="Time & Cost Intelligence",
            foreground="#A9B8C4",
            background="#14324A",
            font=("Segoe UI", 10),
        )
        self.subtitle_label.pack(anchor="w", pady=(4, 0))

        # Navigation divider
        ttk.Separator(self.sidebar, orient="horizontal").pack(fill="x", padx=20, pady=12)

        # Navigation buttons
        self.nav_frame = ttk.Frame(self.sidebar, style="Sidebar.TFrame")
        self.nav_frame.pack(fill="x", padx=4, pady=4)

        self.nav_buttons: dict[str, ttk.Button] = {}
        nav_items = [
            ("overview", "Overview", "Overview"),
            ("projects", "Projects", "Projects"),
            ("project_detail", "Project Detail", "Project Details"),
            ("activity_timeline", "Activity Timeline", "Activity Timeline"),
            ("integrations", "Integrations", "Integrations"),
            ("timesheet_review", "Timesheet Review", "Timesheet Review"),
            ("team", "Team", "Team"),
            ("reports", "Reports", "Reports"),
            ("estimating", "Historical Estimating", "Historical Estimating"),
        ]

        for screen_id, label, _ in nav_items:
            btn = ttk.Button(
                self.nav_frame,
                text=label,
                style="Nav.TButton",
                command=lambda sid=screen_id: self.show_screen(sid),
            )
            btn.pack(fill="x", pady=2)
            self.nav_buttons[screen_id] = btn

        # Bottom section: Settings / help
        ttk.Separator(self.sidebar, orient="horizontal").pack(fill="x", padx=20, pady=20)

        self.settings_btn = ttk.Button(
            self.nav_frame,
            text="Settings",
            style="Nav.TButton",
            command=self._show_settings,
        )
        self.settings_btn.pack(fill="x", pady=2)

        # Main content area
        self.content = ttk.Frame(self.container, style="App.TFrame")
        self.content.pack(side="right", fill="both", expand=True)

        # Header bar
        self.header = ttk.Frame(self.content, style="Header.TFrame")
        self.header.pack(fill="x", padx=0, pady=0)

        self.page_title = ttk.Label(
            self.header, text="Overview", style="Title.TLabel"
        )
        self.page_title.pack(anchor="w", padx=24, pady=(20, 4))

        self.page_subtitle = ttk.Label(
            self.header, text="Synthetic data — demonstration mode", style="Subtitle.TLabel"
        )
        self.page_subtitle.pack(anchor="w", padx=24, pady=(0, 20))
        ttk.Label(self.header, text="SYNTHETIC DATA — DEVELOPMENT PREVIEW",
                  foreground="#9B2C2C", background="#FFFFFF",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=24, pady=(0, 8))

        # Screen container (pages stack here)
        self.screen_container = ttk.Frame(self.content, style="App.TFrame")
        self.screen_container.pack(fill="both", expand=True, padx=24, pady=24)

        # Initialize screens (lazy, created on first show)
        self.screens: dict[str, Any] = {}
        self.current_screen: str | None = None

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------
    def _load_data(self) -> None:
        """Load projects and activity events into the domain layer.

        Seeds synthetic fixtures on first run so the app works
        out-of-the-box without real employee data.
        """
        self.projects = self.db.list_projects()

        # Seed projects fixture if empty
        if not self.projects:
            try:
                with open(_fixture("projects.json"), encoding="utf-8") as fixture:
                    projects = [Project.from_dict(row) for row in json.load(fixture)]
                for p in projects:
                    self.db.upsert_project(p)
                self.projects = projects
            except Exception as exc:  # noqa: BLE001
                self.projects = []
                messagebox.showerror(
                    "Seed Data Error",
                    f"Failed to load synthetic project fixtures: {exc}",
                )

        # Seed activity events fixture if empty
        existing_events = self.db.list_events()
        if not existing_events:
            try:
                with open(_fixture("events.json"), encoding="utf-8") as fixture:
                    events = [ActivityEvent.from_dict(row) for row in json.load(fixture)]
                # Correlate synthetic titles in memory before the privacy boundary.
                # Persistence keeps hashed titles and drops untrusted raw payloads.
                from bimspend.correlation import correlate_events
                from bimspend.review import suggest_entry
                ingested = [ev for ev in events if self.db.ingest_event(ev)]
                suggestions = correlate_events(ingested, self.projects)
                by_id = {ev.id: ev for ev in ingested}
                for suggestion in suggestions:
                    self.db.upsert_attributed_time(suggestion)
                    if suggestion.project_id is None:
                        continue
                    project = self.db.get_project(suggestion.project_id)
                    if project is None or project.is_archived:
                        continue
                    entry = suggest_entry(suggestion, project, by_id[suggestion.activity_event_id].user_id)
                    if self.db.get_time_entry(entry.id) is None:
                        self.db.upsert_time_entry(entry)
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror(
                    "Seed Data Error",
                    f"Failed to load synthetic event fixtures: {exc}",
                )

    # ------------------------------------------------------------------
    # Screen management
    # ------------------------------------------------------------------
    def show_screen(self, screen_id: str) -> None:
        """Switch to the given screen."""
        # Highlight active nav button
        for sid, btn in self.nav_buttons.items():
            if sid == screen_id:
                btn.state(["pressed"])
            else:
                btn.state(["!pressed"])

        # Hide current screen
        if self.current_screen and self.current_screen in self.screens:
            self.screens[self.current_screen].hide()

        # Create screen if needed
        if screen_id not in self.screens:
            self.screens[screen_id] = self._create_screen(screen_id)

        self.screens[screen_id].show()
        self.current_screen = screen_id

    def _create_screen(self, screen_id: str) -> Any:
        """Factory for screen instances (lazy imports to avoid circular deps)."""
        if screen_id == "overview":
            from .screens.overview import OverviewScreen
            return OverviewScreen(self.screen_container, self)
        if screen_id == "projects":
            from .screens.projects import ProjectsScreen
            return ProjectsScreen(self.screen_container, self)
        if screen_id == "project_detail":
            from .screens.project_detail import ProjectDetailScreen
            return ProjectDetailScreen(self.screen_container, self)
        if screen_id == "activity_timeline":
            from .screens.activity_timeline import ActivityTimelineScreen
            return ActivityTimelineScreen(self.screen_container, self)
        if screen_id == "integrations":
            from .screens.integrations import IntegrationsScreen
            return IntegrationsScreen(self.screen_container, self)
        if screen_id == "timesheet_review":
            from .screens.timesheet_review import TimesheetReviewScreen
            return TimesheetReviewScreen(self.screen_container, self)
        if screen_id == "team":
            from .screens.team import TeamScreen
            return TeamScreen(self.screen_container, self)
        if screen_id == "reports":
            from .screens.reports import ReportsScreen
            return ReportsScreen(self.screen_container, self)
        if screen_id == "estimating":
            from .screens.estimating import EstimatingScreen
            return EstimatingScreen(self.screen_container, self)
        raise ValueError(f"Unknown screen: {screen_id}")

    def set_project(self, project: Project | None) -> None:
        """Set the current project context."""
        self.current_project = project
        if project:
            self.page_title.config(text=project.name)
            self.page_subtitle.config(text=f"Client: {project.client}  ·  Project ID: {project.id}")
        else:
            self.page_title.config(text="Overview")
            self.page_subtitle.config(text="Synthetic data — demonstration mode")

    def run(self) -> None:
        self.root.mainloop()

    def _show_settings(self) -> None:
        messagebox.showinfo(
            "Settings",
            "Settings panel\n\nLocal synthetic data mode.\nNo employee monitoring active.\nNo remote synchronization.",
        )

    def destroy(self) -> None:
        self.db.close()
        self.root.destroy()


def main() -> None:
    app = BIMSpendApp()
    app.run()


if __name__ == "__main__":
    main()
