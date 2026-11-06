"""Live Activity screen - BIMSpend R1-08.

Shows observed activity events with project attribution suggestions.
Designer can confirm, correct, or reject attributions. AFK and
unattributed events are clearly marked. Uses the BIMSpend design system.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, timezone
from typing import Any

from bimspend.app.design import (
    ACCENT_BLUE,
    ACCENT_TEAL,
    APP_BG,
    CARD_BG,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    format_date_time,
    format_minutes,
)
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
        self._section_header(
            "Live Activity",
            "Observed activity with project attribution suggestions",
        )

        # Filter bar
        self._build_filter_bar()

        # Timeline table
        self._build_timeline_table()

        # Action buttons
        self._build_action_buttons()

        # Legend
        self._build_legend()

        # Populate
        self._populate()

    def _build_filter_bar(self) -> None:
        """Build the filter bar."""
        frame = ttk.Frame(self, style="App.TFrame")
        frame.pack(fill="x", pady=(0, 12))

        ttk.Label(
            frame, text="Filter by user:", style="MetricLabel.TLabel"
        ).pack(side="left", padx=(0, 8))
        self.user_var = tk.StringVar(value="All users")
        user_combo = ttk.Combobox(
            frame,
            textvariable=self.user_var,
            values=["All users"],
            state="readonly",
            width=18,
        )
        user_combo.pack(side="left", padx=(0, 16))
        user_combo.bind("<<ComboboxSelected>>", lambda _: self._refresh())

        # Populate user filter
        users = {"All users"}
        for event in self.db.list_events():
            users.add(event.user_id)
        user_combo["values"] = sorted(users)

    def _build_timeline_table(self) -> None:
        """Build the timeline table."""
        table_frame = ttk.Frame(self, style="App.TFrame")
        table_frame.pack(fill="both", expand=True)

        cols = (
            "time",
            "user",
            "app",
            "window_title",
            "duration",
            "afk",
            "project",
            "confidence",
            "status",
        )
        self.tree = ttk.Treeview(
            table_frame,
            columns=cols,
            show="headings",
            height=14,
            style="App.Treeview",
        )

        self.tree.heading("#0", text="Event ID")
        self.tree.heading("time", text="Time")
        self.tree.heading("user", text="User")
        self.tree.heading("app", text="Application")
        self.tree.heading("window_title", text="Window Title")
        self.tree.heading("duration", text="Duration")
        self.tree.heading("afk", text="AFK")
        self.tree.heading("project", text="Project")
        self.tree.heading("confidence", text="Confidence")
        self.tree.heading("status", text="Status")

        self.tree.column("#0", width=0, stretch=False)
        self.tree.column("time", width=130)
        self.tree.column("user", width=100)
        self.tree.column("app", width=120)
        self.tree.column("window_title", width=220)
        self.tree.column("duration", width=80)
        self.tree.column("afk", width=50)
        self.tree.column("project", width=160)
        self.tree.column("confidence", width=80)
        self.tree.column("status", width=100)

        scrollbar = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bind double-click to toggle attribution
        self.tree.bind("<Double-1>", self._on_entry_double_click)

    def _build_action_buttons(self) -> None:
        """Build action buttons."""
        btn_frame = ttk.Frame(self, style="App.TFrame")
        btn_frame.pack(fill="x", pady=(8, 0))

        ttk.Button(
            btn_frame,
            text="Assign Selected to Project",
            command=self._assign_selected,
        ).pack(side="left", padx=(0, 8))

    def _build_legend(self) -> None:
        """Build the legend."""
        legend_frame = ttk.Frame(self, style="App.TFrame")
        legend_frame.pack(fill="x", pady=(12, 0))

        ttk.Label(
            legend_frame,
            text=(
                "Legend:  AFK = idle period  •  Unassigned = no project mapping  •  "
                "Confidence = correlation certainty (window title match)"
            ),
            style="Caption.TLabel",
        ).pack(anchor="w")

    def _populate(self) -> None:
        """Populate the timeline table from the database."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        events = self.db.list_events(user_id=None)
        attributed = {a.activity_event_id: a for a in self.db.list_attributed_time()}

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
                    format_date_time(event.started_at),
                    event.user_id,
                    event.app_name,
                    title,
                    format_minutes(event.duration_minutes),
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

        events = self.db.list_events()
        target_event = None
        for ev in events:
            if ev.id == event_id:
                target_event = ev
                break

        if not target_event:
            return

        if target_event.is_afk:
            messagebox.showinfo(
                "AFK Period",
                "AFK periods cannot be attributed to projects.\n"
                "They represent idle/away time.",
            )
            return

        existing = [
            a for a in self.db.list_attributed_time()
            if a.activity_event_id == event_id
        ]
        if existing and existing[0].project_id is not None:
            messagebox.showinfo(
                "Already Attributed",
                f"This event is already attributed to:\n{existing[0].project_id}\n"
                f"Confidence: {existing[0].confidence:.0%}\n"
                f"Method: {existing[0].correlation_method}",
            )
            return

        from bimspend.correlation import correlate_events

        projects = self.app.projects
        attributed_list = correlate_events([target_event], projects)

        if attributed_list and attributed_list[0].project_id is not None:
            self._save_suggestion(attributed_list[0], target_event)
            self._populate()
        else:
            messagebox.showinfo(
                "Cannot Attribute",
                "No matching project found for this activity.\n"
                "The event remains unassigned.",
            )

    def _save_suggestion(
        self, suggestion: AttributedTime, event: ActivityEvent
    ) -> None:
        """Keep project attribution and pending review entry together."""
        from bimspend.review import suggest_entry

        self.db.upsert_attributed_time(suggestion)
        if suggestion.project_id is None:
            return
        project = self.db.get_project(suggestion.project_id)
        if project is None or project.is_archived:
            messagebox.showerror(
                "Error",
                "Cannot attribute activity to a missing or archived project.",
            )
            return
        entry = suggest_entry(suggestion, project, event.user_id)
        if self.db.get_time_entry(entry.id) is None:
            self.db.upsert_time_entry(entry)

    def _assign_selected(self) -> None:
        """Explicit designer mapping for an unmatched synthetic event."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Assign", "Select an activity event.")
            return
        event_id = self.tree.item(selected[0])["text"]
        event = next(
            (e for e in self.db.list_events() if e.id == event_id), None
        )
        if event is None or event.is_afk:
            messagebox.showinfo("Assign", "AFK periods cannot be assigned.")
            return
        projects = [p for p in self.app.projects if not p.is_archived]
        choices = "\n".join(f"{p.id}: {p.name}" for p in projects)
        project_id = simpledialog.askstring(
            "Assign activity", f"Enter project ID:\n{choices}"
        )
        if project_id is None:
            return
        project = next(
            (p for p in projects if p.id == project_id.strip()), None
        )
        if project is None:
            messagebox.showerror("Assign", "Unknown or archived project ID.")
            return
        existing = next(
            (a for a in self.db.list_attributed_time() if a.activity_event_id == event_id),
            None,
        )
        if existing and existing.project_id:
            messagebox.showinfo(
                "Assign", "Already assigned; edit in a future review workflow."
            )
            return
        from datetime import datetime, timezone

        suggestion = AttributedTime(
            id=f"att_{event.id}",
            activity_event_id=event.id,
            project_id=project.id,
            attributed_minutes=event.duration_minutes,
            confidence=1.0,
            correlation_method="user_confirmed",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._save_suggestion(suggestion, event)
        self._populate()
