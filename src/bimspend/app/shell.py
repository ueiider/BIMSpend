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
from tkinter import ttk, messagebox, simpledialog
from typing import Any, Optional

from bimspend.app.design import (
    register_styles,
    get_visible_nav_items,
    NAV_CONFIG,
    APP_BG,
    SIDEBAR_BG,
    CARD_BG,
    HEADER_BG,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    ACCENT_BLUE,
    ACCENT_TEAL,
)
from bimspend.db import Database
from bimspend.models import Project, ActivityEvent, TimeEntryState
from bimspend.dashboard import all_projects_summary
from bimspend.auth import SessionManager
from bimspend.identity import Actor, Role, current_auth


def _fixture(name: str) -> str:
    """Resolve path to a synthetic fixture file."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "data", "synthetic", name)
    return os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "synthetic", name)


class BIMSpendApp:
    """Main BIMSpend application window.

    Provides:
      - Left rail: workspace logo/name, role-aware navigation, user profile
      - Top bar: workspace name, breadcrumbs, search, user menu
      - Main content: screen canvas with page header and content
      - Status bar: capture state and sync state indicators

    Authentication:
      - Login required before any screen is shown
      - Session validated via current_auth (fail-closed)
      - Role-based navigation visibility
    """

    def __init__(self, root: tk.Tk | None = None, db_path: str = "bimspend.db"):
        self.root = root or tk.Tk()
        self.root.title("BIMSpend — Project Time & Cost Intelligence")
        self.root.geometry("1400x900")
        self.root.minsize(1100, 750)

        # High-DPI awareness for Windows
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:  # noqa: BLE001
            pass  # Non-Windows or older Windows

        # Domain layer
        self.db = Database(db_path)
        self.current_user: str | None = None
        self.current_actor: Optional[Actor] = None
        self.current_project: Project | None = None
        self.authenticated = False

        # Navigation breadcrumb stack
        self._breadcrumb_stack: list[tuple[str, str]] = []  # (screen_id, label)

        # Style
        self.style = ttk.Style(self.root)
        register_styles(self.style)

        # Layout (login first, then shell after auth)
        self._build_login()

        # Load data (available regardless of auth state for testing)
        self._load_data()

        # Navigation state (populated by _build_shell after login)
        self.nav_buttons: dict[str, ttk.Button] = {}

        # Screens (lazy, created on first show)
        self.screens: dict[str, Any] = {}
        self.current_screen: str | None = None

    # ------------------------------------------------------------------
    # Login flow
    # ------------------------------------------------------------------

    def _build_login(self) -> None:
        """Build the login screen."""
        self.login_frame = ttk.Frame(self.root, style="App.TFrame")
        self.login_frame.pack(fill="both", expand=True)

        # Center container
        center = ttk.Frame(self.login_frame, style="App.TFrame")
        center.place(relx=0.5, rely=0.5, anchor="center")

        # Card
        card = ttk.Frame(center, style="Card.TFrame")
        card.pack(padx=40, pady=40)

        ttk.Label(
            card,
            text="BIMSpend",
            font=("Segoe UI", 28, "bold"),
            foreground=ACCENT_BLUE,
            background=CARD_BG,
        ).pack(anchor="w", pady=(0, 4))
        ttk.Label(
            card,
            text="Time & Cost Intelligence",
            font=("Segoe UI", 12),
            foreground=TEXT_SECONDARY,
            background=CARD_BG,
        ).pack(anchor="w", pady=(0, 24))

        # Company
        ttk.Label(card, text="Company", font=("Segoe UI", 10), background=CARD_BG).pack(anchor="w")
        self.login_company_var = tk.StringVar()
        company_combo = ttk.Combobox(
            card,
            textvariable=self.login_company_var,
            state="readonly",
            width=40,
        )
        company_combo.pack(fill="x", pady=(4, 16))
        self._populate_companies(company_combo)

        # Username
        ttk.Label(card, text="Username", font=("Segoe UI", 10), background=CARD_BG).pack(anchor="w")
        self.login_user_var = tk.StringVar()
        ttk.Entry(card, textvariable=self.login_user_var, width=40).pack(fill="x", pady=(4, 16))

        # Password
        ttk.Label(card, text="Password", font=("Segoe UI", 10), background=CARD_BG).pack(anchor="w")
        self.login_pass_var = tk.StringVar()
        ttk.Entry(card, textvariable=self.login_pass_var, show="•", width=40).pack(fill="x", pady=(4, 24))

        # Buttons
        btn_frame = ttk.Frame(card, style="App.TFrame")
        btn_frame.pack(fill="x")
        ttk.Button(
            btn_frame,
            text="Cancel",
            command=self.root.quit,
        ).pack(side="right", padx=(8, 0))
        ttk.Button(
            btn_frame,
            text="Sign In",
            command=self._attempt_login,
        ).pack(side="right")

        # Bind Enter key
        self.root.bind("<Return>", lambda _: self._attempt_login())

    def _populate_companies(self, combo: ttk.Combobox) -> None:
        """Populate company dropdown."""
        companies = self.db.list_companies()
        values = [f"{c['name']} ({c['id']})" for c in companies]
        combo["values"] = values
        if values:
            combo.current(0)
        self._company_map = {f"{c['name']} ({c['id']})": c["id"] for c in companies}

    def _attempt_login(self) -> None:
        """Attempt to authenticate the user."""
        company_selection = self.login_company_var.get()
        company_id = self._company_map.get(company_selection) if hasattr(self, "_company_map") else None
        username = self.login_user_var.get().strip()
        password = self.login_pass_var.get()

        if not company_id:
            messagebox.showerror("Login Error", "Please select a company.")
            return
        if not username:
            messagebox.showerror("Login Error", "Please enter a username.")
            return
        if not password:
            messagebox.showerror("Login Error", "Please enter a password.")
            return

        try:
            sm = SessionManager(self.db)
            actor = sm.login(username, password, company_id=company_id)
            self.current_actor = actor
            self.current_user = actor.id
            self.authenticated = True

            # Build the main shell
            self.login_frame.destroy()
            self._build_shell()
            self._load_data()
            self.show_screen("overview")

        except (ValueError, PermissionError) as exc:
            messagebox.showerror("Login Error", str(exc))

    # ------------------------------------------------------------------
    # Shell layout (after authentication)
    # ------------------------------------------------------------------

    def _build_shell(self) -> None:
        """Build the main application shell after login."""
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
            background=SIDEBAR_BG,
            font=("Segoe UI", 18, "bold"),
        )
        self.logo_label.pack(anchor="w")

        self.subtitle_label = ttk.Label(
            self.logo_frame,
            text="Time & Cost Intelligence",
            foreground="#A9B8C4",
            background=SIDEBAR_BG,
            font=("Segoe UI", 10),
        )
        self.subtitle_label.pack(anchor="w", pady=(4, 0))

        # Session info
        self._build_sidebar_session()

        # Navigation divider
        ttk.Separator(self.sidebar, orient="horizontal").pack(fill="x", padx=20, pady=16)

        # Navigation heading
        ttk.Label(
            self.sidebar,
            text="Navigation",
            foreground="#A9B8C4",
            background=SIDEBAR_BG,
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", padx=20, pady=(0, 8))

        # Navigation buttons
        self.nav_frame = ttk.Frame(self.sidebar, style="Sidebar.TFrame")
        self.nav_frame.pack(fill="x", padx=4, pady=4)

        self.nav_buttons: dict[str, ttk.Button] = {}
        role = self.current_actor.role.value if self.current_actor else "designer"
        nav_items = get_visible_nav_items(role)

        for item in nav_items:
            screen_id = item["id"]
            label = item["label"]
            icon = item.get("icon", "")
            btn_text = f"{icon}  {label}" if icon else label
            btn = ttk.Button(
                self.nav_frame,
                text=btn_text,
                style="Nav.TButton",
                command=lambda sid=screen_id: self.show_screen(sid),
            )
            btn.pack(fill="x", pady=2)
            self.nav_buttons[screen_id] = btn

        # Bottom section: Settings / help / logout
        ttk.Separator(self.sidebar, orient="horizontal").pack(fill="x", padx=20, pady=20)

        self.settings_btn = ttk.Button(
            self.nav_frame,
            text="⚙️  Settings",
            style="Nav.TButton",
            command=self._show_settings,
        )
        self.settings_btn.pack(fill="x", pady=2)

        self.logout_btn = ttk.Button(
            self.nav_frame,
            text="🚪  Sign Out",
            style="Nav.TButton",
            command=self._logout,
        )
        self.logout_btn.pack(fill="x", pady=2)

        # Main content area
        self.content = ttk.Frame(self.container, style="App.TFrame")
        self.content.pack(side="right", fill="both", expand=True)

        # Header bar
        self.header = ttk.Frame(self.content, style="Header.TFrame")
        self.header.pack(fill="x", padx=0, pady=0)

        # Breadcrumbs
        self.breadcrumb_frame = ttk.Frame(self.header, style="Header.TFrame")
        self.breadcrumb_frame.pack(fill="x", padx=24, pady=(16, 4))
        self.breadcrumb_label = ttk.Label(
            self.breadcrumb_frame,
            text="",
            font=("Segoe UI", 9),
            foreground=TEXT_SECONDARY,
            background=HEADER_BG,
        )
        self.breadcrumb_label.pack(anchor="w")

        # Page title
        self.page_title = ttk.Label(
            self.header, text="Executive Dashboard", style="Title.TLabel"
        )
        self.page_title.pack(anchor="w", padx=24, pady=(0, 4))

        # Page subtitle + search
        header_right = ttk.Frame(self.header, style="Header.TFrame")
        header_right.pack(fill="x", padx=24, pady=(0, 20))

        self.page_subtitle = ttk.Label(
            header_right, text="Synthetic data — demonstration mode", style="Subtitle.TLabel"
        )
        self.page_subtitle.pack(side="left")

        # Search
        search_frame = ttk.Frame(header_right, style="Header.TFrame")
        search_frame.pack(side="right")
        ttk.Label(
            search_frame,
            text="🔍",
            font=("Segoe UI", 10),
            background=HEADER_BG,
        ).pack(side="left", padx=(0, 4))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(
            search_frame,
            textvariable=self.search_var,
            width=25,
            style="App.TEntry",
        )
        self.search_entry.pack(side="left")
        self.search_entry.bind("<KeyRelease>", lambda _: self._on_search())

        # Dev preview banner
        ttk.Label(
            self.header,
            text="SYNTHETIC DATA — DEVELOPMENT PREVIEW",
            foreground="#9B2C2C",
            background="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", padx=24, pady=(0, 8))

        # Screen container
        self.screen_container = ttk.Frame(self.content, style="App.TFrame")
        self.screen_container.pack(fill="both", expand=True, padx=24, pady=24)

    def _build_sidebar_session(self) -> None:
        """Build the session info area in the sidebar."""
        frame = ttk.Frame(self.sidebar, style="Sidebar.TFrame")
        frame.pack(fill="x", padx=20, pady=(0, 16))

        actor = current_auth.actor
        if actor:
            ttk.Label(
                frame,
                text=f"{actor.id}",
                foreground="#FFFFFF",
                background=SIDEBAR_BG,
                font=("Segoe UI", 10, "bold"),
            ).pack(anchor="w")
            ttk.Label(
                frame,
                text=f"{actor.role.value} · {actor.company_id}",
                foreground="#A9B8C4",
                background=SIDEBAR_BG,
                font=("Segoe UI", 9),
            ).pack(anchor="w", pady=(2, 0))
        else:
            ttk.Label(
                frame,
                text="Not authenticated",
                foreground="#A9B8C4",
                background=SIDEBAR_BG,
                font=("Segoe UI", 10),
            ).pack(anchor="w")

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_data(self) -> None:
        """Load projects and activity events into the domain layer."""
        self.projects = self.db.list_projects()

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

        existing_events = self.db.list_events()
        if not existing_events:
            try:
                with open(_fixture("events.json"), encoding="utf-8") as fixture:
                    events = [ActivityEvent.from_dict(row) for row in json.load(fixture)]
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

        self._seed_demo_auth_and_financials()

    def _seed_demo_auth_and_financials(self) -> None:
        """Seed synthetic demo auth and financial data if not already present.

        This ensures the Windows preview has working login credentials and
        representative financial data (approved time, budgets, cost/billing
        rates) so all screens can be demonstrated. Data is synthetic only;
        no real employee, client, or financial information is used.
        """
        from bimspend.auth import hash_password
        from bimspend.identity import Role
        from datetime import datetime, timezone
        from decimal import Decimal
        import json

        # Only seed if no companies exist yet (fresh database).
        if self.db.list_companies():
            return

        try:
            now = datetime.now(timezone.utc).isoformat()

            # --- Companies ---
            self.db.upsert_company("demo_co", "BIMSpend Demo Company", is_active=True)

            # --- Team members ---
            self.db.upsert_member(__import__("bimspend.models", fromlist=["TeamMember"]).TeamMember(
                "alice_demo", "Alice Designer", "designer", 55.00, True
            ))
            self.db.upsert_member(__import__("bimspend.models", fromlist=["TeamMember"]).TeamMember(
                "bob_demo", "Bob Manager", "manager", 95.00, True
            ))
            self.db.upsert_member(__import__("bimspend.models", fromlist=["TeamMember"]).TeamMember(
                "carol_demo", "Carol Admin", "administrator", 120.00, True
            ))

            # --- Company memberships ---
            self.db.upsert_company_member("demo_co", "alice_demo", "designer")
            self.db.upsert_company_member("demo_co", "bob_demo", "manager")
            self.db.upsert_company_member("demo_co", "carol_demo", "administrator")

            # --- User credentials (hashed passwords) ---
            demo_hash = hash_password("DemoPass123!")
            self.db.upsert_user_credential("alice_demo", "alice_demo", demo_hash)
            self.db.upsert_user_credential("bob_demo", "bob_demo", demo_hash)
            self.db.upsert_user_credential("carol_demo", "carol_demo", demo_hash)

            # --- Employee cost and billing rates ---
            from bimspend.financial import CostRateService, BudgetService
            crs = CostRateService(self.db)
            bs = BudgetService(self.db)

            # Cost rates (effective from start of data range)
            crs.set_cost_rate(
                member_id="alice_demo", company_id="demo_co",
                hourly_cost_aud=Decimal("55.00"),
                effective_from="2026-10-01T00:00:00Z",
                actor_id="carol_demo",
                notes="Synthetic demo rate",
            )
            crs.set_cost_rate(
                member_id="bob_demo", company_id="demo_co",
                hourly_cost_aud=Decimal("95.00"),
                effective_from="2026-10-01T00:00:00Z",
                actor_id="carol_demo",
                notes="Synthetic demo rate",
            )

            # Billing rates
            crs.set_billing_rate(
                member_id="alice_demo", company_id="demo_co",
                hourly_billing_aud=Decimal("120.00"),
                effective_from="2026-10-01T00:00:00Z",
                actor_id="carol_demo",
                notes="Synthetic demo rate",
            )
            crs.set_billing_rate(
                member_id="bob_demo", company_id="demo_co",
                hourly_billing_aud=Decimal("150.00"),
                effective_from="2026-10-01T00:00:00Z",
                actor_id="carol_demo",
                notes="Synthetic demo rate",
            )

            # --- Project budgets ---
            bs.create_budget(
                project_id="proj_001", company_id="demo_co",
                original_budget_aud=Decimal("15000.00"),
                effective_from="2026-10-01T00:00:00Z",
                actor_id="carol_demo",
                notes="Synthetic demo budget",
            )
            bs.create_budget(
                project_id="proj_002", company_id="demo_co",
                original_budget_aud=Decimal("20000.00"),
                effective_from="2026-10-01T00:00:00Z",
                actor_id="carol_demo",
                notes="Synthetic demo budget",
            )
            bs.create_budget(
                project_id="proj_003", company_id="demo_co",
                original_budget_aud=Decimal("12000.00"),
                effective_from="2026-10-01T00:00:00Z",
                actor_id="carol_demo",
                notes="Synthetic demo budget",
            )

            # --- Approved time entries for financial screens ---
            from bimspend.models import AttributedTime, TimeEntry, TimeEntryState
            # Attributed time for proj_001 (alice: 2 hours approved)
            at1 = AttributedTime(
                id="at_demo_001", activity_event_id="evt_001",
                project_id="proj_001", attributed_minutes=120.0,
                confidence=1.0, correlation_method="synthetic_demo",
                created_at="2026-10-05T11:00:00Z",
            )
            self.db.upsert_attributed_time(at1)
            entry1 = TimeEntry(
                id="entry_demo_001", attributed_time_id="at_demo_001",
                project_id="proj_001", user_id="alice_demo",
                minutes=120.0, state=TimeEntryState.APPROVED,
                standard_rate=150.0, loaded_cost_rate=55.0,
                billed_minutes=0.0, company_id="demo_co",
                submitted_by="alice_demo", submitted_at="2026-10-05T11:30:00Z",
                reviewed_by="bob_demo", reviewed_at="2026-10-05T14:00:00Z",
                created_at="2026-10-05T11:00:00Z",
            )
            self.db.upsert_time_entry(entry1, actor_id="alice_demo")

            # Approved time for proj_002 (alice: 1.75 hours approved)
            at2 = AttributedTime(
                id="at_demo_002", activity_event_id="evt_002",
                project_id="proj_002", attributed_minutes=105.0,
                confidence=1.0, correlation_method="synthetic_demo",
                created_at="2026-10-05T13:00:00Z",
            )
            self.db.upsert_attributed_time(at2)
            entry2 = TimeEntry(
                id="entry_demo_002", attributed_time_id="at_demo_002",
                project_id="proj_002", user_id="alice_demo",
                minutes=105.0, state=TimeEntryState.APPROVED,
                standard_rate=175.0, loaded_cost_rate=55.0,
                billed_minutes=0.0, company_id="demo_co",
                submitted_by="alice_demo", submitted_at="2026-10-05T13:30:00Z",
                reviewed_by="bob_demo", reviewed_at="2026-10-05T16:00:00Z",
                created_at="2026-10-05T13:00:00Z",
            )
            self.db.upsert_time_entry(entry2, actor_id="alice_demo")

            # Pending time for proj_003 (bob: 1.5 hours pending review)
            at3 = AttributedTime(
                id="at_demo_003", activity_event_id="evt_006",
                project_id="proj_003", attributed_minutes=90.0,
                confidence=0.9, correlation_method="synthetic_demo",
                created_at="2026-10-06T12:30:00Z",
            )
            self.db.upsert_attributed_time(at3)
            entry3 = TimeEntry(
                id="entry_demo_003", attributed_time_id="at_demo_003",
                project_id="proj_003", user_id="bob_demo",
                minutes=90.0, state=TimeEntryState.PENDING_REVIEW,
                standard_rate=160.0, loaded_cost_rate=95.0,
                billed_minutes=0.0, company_id="demo_co",
                submitted_by=None, submitted_at=None,
                reviewed_by=None, reviewed_at=None,
                created_at="2026-10-06T12:30:00Z",
            )
            self.db.upsert_time_entry(entry3, actor_id="bob_demo")

        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(
                "Seed Data Error",
                f"Failed to seed demo auth and financial data: {exc}",
            )

    # ------------------------------------------------------------------
    # Breadcrumb management
    # ------------------------------------------------------------------

    def _add_breadcrumb(self, screen_id: str, label: str) -> None:
        """Add a breadcrumb entry."""
        # Avoid duplicates
        self._breadcrumb_stack = [(sid, lbl) for sid, lbl in self._breadcrumb_stack if sid != screen_id]
        self._breadcrumb_stack.append((screen_id, label))
        self._update_breadcrumbs()

    def _update_breadcrumbs(self) -> None:
        """Update the breadcrumb display."""
        parts = []
        for i, (sid, label) in enumerate(self._breadcrumb_stack):
            if i > 0:
                parts.append(" › ")
            parts.append(label)
        self.breadcrumb_label.config(text="".join(parts))

    def _on_search(self) -> None:
        """Handle search input changes."""
        query = self.search_var.get().strip().lower()
        if self.current_screen and self.current_screen in self.screens:
            screen = self.screens[self.current_screen]
            if hasattr(screen, "filter_by_search"):
                screen.filter_by_search(query)

    # ------------------------------------------------------------------
    # Screen management
    # ------------------------------------------------------------------

    def show_screen(self, screen_id: str) -> None:
        """Switch to the given screen."""
        # Highlight active nav button (only if shell is built)
        if self.nav_buttons:
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
            # Ensure screen_container exists (created by _build_shell after login;
            # for testing, create a minimal one)
            if not hasattr(self, "screen_container") or self.screen_container is None:
                self.screen_container = ttk.Frame(
                    self.root, style="App.TFrame"
                )
            self.screens[screen_id] = self._create_screen(screen_id)

        # Update breadcrumbs (only if shell is built)
        label = NAV_CONFIG.get(screen_id, {}).get("label", screen_id)
        if screen_id != "overview" and hasattr(self, "breadcrumb_label"):
            self._add_breadcrumb(screen_id, label)
        elif screen_id == "overview" and hasattr(self, "breadcrumb_label"):
            self._breadcrumb_stack = []
            self._update_breadcrumbs()

        self.screens[screen_id].show()
        self.current_screen = screen_id

        # Update page title/subtitle (only if shell is built)
        if hasattr(self, "page_title"):
            label = NAV_CONFIG.get(screen_id, {}).get("label", screen_id)
            self.page_title.config(text=label)
            if screen_id == "overview":
                self.page_subtitle.config(text="Company overview — approved time and budget consumption")
            else:
                actor = current_auth.actor
                if actor:
                    self.page_subtitle.config(text=f"Company: {actor.company_id}  ·  Role: {actor.role.value}")
                else:
                    self.page_subtitle.config(text="")

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
        if screen_id == "designer_review":
            from .screens.designer_review import DesignerReviewScreen
            return DesignerReviewScreen(self.screen_container, self)
        if screen_id == "manager_approval":
            from .screens.manager_approval import ManagerApprovalScreen
            return ManagerApprovalScreen(self.screen_container, self)
        if screen_id == "financial_dashboard":
            from .screens.financial_dashboard import FinancialDashboardScreen
            return FinancialDashboardScreen(self.screen_container, self)
        if screen_id == "project_financial_detail":
            from .screens.project_financial_detail import ProjectFinancialDetailScreen
            return ProjectFinancialDetailScreen(self.screen_container, self)
        if screen_id == "financial_reports":
            from .screens.financial_reports import FinancialReportsScreen
            return FinancialReportsScreen(self.screen_container, self)
        raise ValueError(f"Unknown screen: {screen_id}")

    def set_project(self, project: Project | None) -> None:
        """Set the current project context."""
        self.current_project = project
        if project:
            self.page_title.config(text=project.name)
            self.page_subtitle.config(text=f"Client: {project.client}  ·  Project ID: {project.id}")
        else:
            self.page_title.config(text="Executive Dashboard")
            self.page_subtitle.config(text="Company overview — approved time and budget consumption")

    def run(self) -> None:
        self.root.mainloop()

    def _show_settings(self) -> None:
        messagebox.showinfo(
            "Settings",
            "BIMSpend Settings\n\n"
            "Local synthetic data mode.\n"
            "No employee monitoring active.\n"
            "No remote synchronization.\n"
            f"Current user: {self.current_user or 'N/A'}\n"
            f"Company: {self.current_actor.company_id if self.current_actor else 'N/A'}",
        )

    def _logout(self) -> None:
        """Clear the current session and return to login."""
        if messagebox.askyesno("Sign Out", "Are you sure you want to sign out?"):
            sm = SessionManager(self.db)
            sm.logout()
            self.current_user = None
            self.current_actor = None
            self.authenticated = False
            self.current_screen = None
            self.screens.clear()

            # Rebuild login
            for widget in self.root.winfo_children():
                widget.destroy()
            self._build_login()

    def destroy(self) -> None:
        self.db.close()
        self.root.destroy()


def main() -> None:
    app = BIMSpendApp()
    app.run()


if __name__ == "__main__":
    main()
