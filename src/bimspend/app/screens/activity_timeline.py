"""Activity Timeline screen.

Shows observed activity events with project attribution suggestions.
Designer can confirm, correct, or reject attributions. AFK and
unattributed events are clearly marked.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from bimspend.app.screens.base import BaseScreen
from bimspend.app.shell import BIMSpendApp
from bimspend.models import ActivityEvent, AttributedTime


class ActivityTimelineScreen(BaseScreen):
    """Activity timeline with project attribution suggestions."""

    def __init__(self, parent: ttk.Widget, app: BIMSpendApp):
        super().__init__(parent, app)

    def on_show(self) -> None:
        for widget in self.winfo_children():
            widget.destroy()
        self._build_ui()

    def _build_ui(self) -> None:
        app = self.app

        # Header
        self._section_header("Activity Timeline", "Observed activity with project attribution suggestions")

        # Filter bar
        filter_frame = ttk.Frame(self, style="App.TFrame")
        filter_frame.pack(fill="x", pady=(0, 12))

        ttk.Label(filter_frame, text="Filter by user:").pack(side="left", padx=(0, 8))
        self.user_var = tk.StringVar(value="All users")
        user_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.user_var,
            values=["All users", "designer_01", "designer_02"],
            state="readonly",
            width=15,
        )
        user_combo.pack(side="left", padx=(0, 16))
        user_combo.bind("<<ComboboxSelected>>", lambda _: self._refresh())

        # Timeline table
        table_frame = ttk.Frame(self, style="App.TFrame")
        table_frame.pack(fill="both", expand=True)

        cols = ("time", "user", "app", "window_title", "duration", "afk", "project", "confidence", "status")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=14)

        self.tree.heading("#0", text="Event ID")
        self.tree.heading("time", text="Time")
        self.tree.heading("user", text="User")
        self.tree.heading("app", text="Application")
        self.tree.heading("window_title", text="Window Title")
        self.tree.heading("duration", text="Duration (min)")
        self.tree.heading("afk", text="AFK")
        self.tree.heading("project", text="Project")
        self.tree.heading("confidence", text="Confidence")
        self.tree.heading("status", text="Status")

        self.tree.column("#0", width=100)
        self.tree.column("time", width=130)
        self.tree.column("user", width=100)
        self.tree.column("app", width=120)
        self.tree.column("window_title", width=200)
        self.tree.column("duration", width=80)
        self.tree.column("afk", width=60)
        self.tree.column("project", width=150)
        self.tree.column("confidence", width=80)
        self.tree.column("status", width=100)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bind double-click to toggle attribution
        self.tree.bind("<Double-1>", self._on_entry_double_click)

        # Populate
        self._populate()

        # Legend
        legend_frame = ttk.Frame(self, style="App.TFrame")
        legend_frame.pack(fill="x", pady=(12, 0))

        ttk.Label(
            legend_frame,
            text="Legend:  AFK = idle period  •  Unassigned = no project mapping  •  "
                 "Confidence = correlation certainty (window title match)",
            style="MetricLabel.TLabel",
        ).pack(anchor="w")

    def _populate(self) -> None:
        """Populate the timeline table from the database."""
        # Clear existing
        for item in self.tree.get_children():
            self.tree.delete(item)

        events = self.db.list_events(user_id=None)
        attributed = {a.activity_event_id: a for a in self.db.list_attributed_time()}

        # Filter by user if selected
        user_filter = self.user_var.get()
        if user_filter != "All users":
            events = [e for e in events if e.user_id == user_filter]

        for event in events:
            att = attributed.get(event.id)
            project_name = "Unassigned"
            confidence = "-"
            status = "Unattributed"

            if att and att.project_id:
                project = self.app.db.get_project(att.project_id)
                if project:
                    project_name = project.name
                    confidence = f"{att.confidence:.0%}"
                    status = "Suggested"
                else:
                    project_name = "Unknown"
                    confidence = "—"
                    status = "Unassigned"
            elif att:
                project_name = "Unassigned"
                confidence = "0%"
                status = "Unassigned"

            # Format window title with privacy redaction indicator
            title = event.window_title
            if event.title_redacted:
                title = "[REDACTED]"
            elif len(title) > 40:
                title = title[:37] + "..."

            afk_text = "Yes" if event.is_afk else "No"

            self.tree.insert(
                "",
                "end",
                text=event.id,
                values=(
                    event.started_at[:16].replace("T", " "),
                    event.user_id,
                    event.app_name,
                    title,
                    f"{event.duration_minutes:.0f}",
                    afk_text,
                    project_name,
                    confidence,
                    status,
                ),
            )

    def _refresh(self) -> None:
        self._populate()

    def _on_entry_double_click(self, event: Any) -> None:
        """Toggle attribution for the selected event."""
        selection = self.tree.selection()
        if not selection:
            return
        item = self.tree.item(selection[0])
        event_id = item["text"]

        # Find the event
        events = self.db.list_events()
        target_event = None
        for ev in events:
            if ev.id == event_id:
                target_event = ev
                break

        if not target_event:
            return

        if target_event.is_afk:
            from tkinter import messagebox
            messagebox.showinfo(
                "AFK Period",
                "AFK periods cannot be attributed to projects.\n"
                "They represent idle/away time.",
            )
            return

        # Check if already attributed
        existing = [a for a in self.db.list_attributed_time() if a.activity_event_id == event_id]
        if existing:
            from tkinter import messagebox
            messagebox.showinfo(
                "Already Attributed",
                f"This event is already attributed to:\n{existing[0].project_id}\n"
                f"Confidence: {existing[0].confidence:.0%}\n"
                f"Method: {existing[0].correlation_method}",
            )
            return

        # Auto-attribute using correlation
        from bimspend.correlation import correlate_events
        projects = self.app.projects
        attributed = correlate_events([target_event], projects)

        if attributed and attributed[0].project_id is not None:
            self.db.upsert_attributed_time(attributed[0])
            self._populate()
        else:
            from tkinter import messagebox
            messagebox.showinfo(
                "Cannot Attribute",
                "No matching project found for this activity.\n"
                "The event remains unassigned.",
            )
