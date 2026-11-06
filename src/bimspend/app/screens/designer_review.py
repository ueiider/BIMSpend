"""Designer Review Screen - BIMSpend R1-08.

Designer-facing screen for reviewing attributed time suggestions.
Designers can:
- View pending suggestions with project attribution confidence
- Edit suggested project and duration
- Add review notes
- Submit entries for manager approval
- Reject incorrect suggestions
- Split suggestions into multiple entries
- Merge compatible suggestions

All actions require an authenticated designer session with company scope.
Uses the BIMSpend design system.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from typing import Any, Optional

from bimspend.app.design import (
    ACCENT_BLUE,
    ACCENT_TEAL,
    CARD_BG,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    format_date_time,
    format_minutes,
)
from bimspend.app.screens.base import BaseScreen
from bimspend.app.shell import BIMSpendApp
from bimspend.capture.suggestion_domain import SuggestionService
from bimspend.identity import Actor, Role, current_auth
from bimspend.models import (
    ActivityEvent,
    AttributedTime,
    Project,
    TimeEntry,
    TimeEntryState,
    TimeEntrySuggestion,
)


class DesignerReviewScreen(BaseScreen):
    """Designer review screen for reviewing and submitting time suggestions."""

    def __init__(self, parent: ttk.Widget, app: BIMSpendApp):
        super().__init__(parent, app)
        self._suggestions: list[TimeEntrySuggestion] = []
        self._service = SuggestionService(self.db)

    def on_show(self) -> None:
        """Refresh when shown."""
        for widget in self.winfo_children():
            widget.destroy()
        self._build_ui()

    def _build_ui(self) -> None:
        app = self.app

        # Header
        self._section_header(
            "Designer Review", "Review and submit time suggestions"
        )

        # Session info bar
        self._build_session_bar()

        # Filter bar
        self._build_filter_bar()

        # Suggestions table
        self._build_suggestion_table()

        # Action buttons
        self._build_action_buttons()

        # Populate
        self._refresh()

    def _build_session_bar(self) -> None:
        """Build the session info bar showing current auth context."""
        frame = ttk.Frame(self, style="App.TFrame")
        frame.pack(fill="x", pady=(0, 8))

        actor = current_auth.actor
        if actor:
            ttk.Label(
                frame,
                text=f"Actor: {actor.id}  ({actor.role.value})",
                style="MetricLabel.TLabel",
            ).pack(side="left", padx=(0, 16))
            ttk.Label(
                frame,
                text=f"Company: {actor.company_id}",
                style="MetricLabel.TLabel",
            ).pack(side="left", padx=(0, 16))
        else:
            ttk.Label(
                frame,
                text="No authenticated session",
                style="MetricLabel.TLabel",
            ).pack(side="left", padx=(0, 16))

        ttk.Button(
            frame,
            text="Refresh",
            command=self._refresh,
        ).pack(side="right")

    def _build_filter_bar(self) -> None:
        """Build the filter bar."""
        frame = ttk.Frame(self, style="App.TFrame")
        frame.pack(fill="x", pady=(0, 8))

        ttk.Label(
            frame, text="Filter by project:", style="MetricLabel.TLabel"
        ).pack(side="left", padx=(0, 8))
        self._project_var = tk.StringVar(value="All projects")
        self._project_combo = ttk.Combobox(
            frame,
            textvariable=self._project_var,
            values=["All projects"],
            state="readonly",
            width=20,
        )
        self._project_combo.pack(side="left", padx=(0, 16))
        self._project_combo.bind(
            "<<ComboboxSelected>>", lambda _: self._refresh()
        )

        ttk.Button(
            frame,
            text="Refresh",
            command=self._refresh,
        ).pack(side="right")

    def _build_suggestion_table(self) -> None:
        """Build the suggestions table."""
        frame = ttk.Frame(self, style="App.TFrame")
        frame.pack(fill="both", expand=True)

        cols = (
            "project",
            "start",
            "end",
            "minutes",
            "confidence",
            "source",
            "state",
        )
        self._tree = ttk.Treeview(
            frame,
            columns=cols,
            show="headings",
            height=15,
            style="App.Treeview",
        )
        self._tree.heading("#0", text="Suggestion ID")
        self._tree.heading("project", text="Project")
        self._tree.heading("start", text="Start")
        self._tree.heading("end", text="End")
        self._tree.heading("minutes", text="Minutes")
        self._tree.heading("confidence", text="Confidence")
        self._tree.heading("source", text="Source")
        self._tree.heading("state", text="State")

        self._tree.column("#0", width=0, stretch=False)
        self._tree.column("project", width=180)
        self._tree.column("start", width=130)
        self._tree.column("end", width=130)
        self._tree.column("minutes", width=80)
        self._tree.column("confidence", width=100)
        self._tree.column("source", width=120)
        self._tree.column("state", width=100)

        scrollbar = ttk.Scrollbar(
            frame, orient="vertical", command=self._tree.yview
        )
        self._tree.configure(yscrollcommand=scrollbar.set)

        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Double-click to edit
        self._tree.bind("<Double-1>", self._on_edit_selected)

    def _build_action_buttons(self) -> None:
        """Build action buttons."""
        frame = ttk.Frame(self, style="App.TFrame")
        frame.pack(fill="x", pady=(8, 0))

        self._edit_btn = ttk.Button(
            frame,
            text="Edit Selected",
            command=self._edit_selected,
        )
        self._edit_btn.pack(side="left", padx=(0, 8))

        self._submit_btn = ttk.Button(
            frame,
            text="Submit Selected",
            command=self._submit_selected,
        )
        self._submit_btn.pack(side="left", padx=(0, 8))

        self._reject_btn = ttk.Button(
            frame,
            text="Reject Selected",
            command=self._reject_selected,
        )
        self._reject_btn.pack(side="left", padx=(0, 8))

        self._split_btn = ttk.Button(
            frame,
            text="Split Selected",
            command=self._split_selected,
        )
        self._split_btn.pack(side="left", padx=(0, 8))

        self._merge_btn = ttk.Button(
            frame,
            text="Merge Selected",
            command=self._merge_selected,
        )
        self._merge_btn.pack(side="left")

    def _refresh(self) -> None:
        """Refresh the suggestions table."""
        actor = current_auth.actor
        if actor is None:
            return

        self._tree.delete(*self._tree.get_children())

        suggestions = self.db.list_suggestions(
            user_id=actor.id, state="pending_review"
        )

        project_filter = self._project_var.get()
        if project_filter and project_filter != "All projects":
            suggestions = [
                s for s in suggestions if s.project_id == project_filter
            ]

        confidence_map = {
            "CONFIRMED": "High",
            "HIGH": "High",
            "MEDIUM": "Medium",
            "LOW": "Low",
            "UNASSIGNED": "Unassigned",
        }

        for suggestion in suggestions:
            project_name = suggestion.project_id or "Unassigned"
            project = (
                self.app.db.get_project(suggestion.project_id)
                if suggestion.project_id
                else None
            )
            if project:
                project_name = project.name

            confidence_text = confidence_map.get(
                suggestion.confidence, suggestion.confidence
            )

            self._tree.insert(
                "",
                "end",
                text=suggestion.id,
                values=(
                    project_name,
                    format_date_time(suggestion.start_time),
                    format_date_time(suggestion.end_time),
                    format_minutes(suggestion.suggested_minutes),
                    confidence_text,
                    ", ".join(suggestion.evidence_ids[:2]),
                    suggestion.state.replace("_", " ").title(),
                ),
            )

    def _get_selected_suggestion(self) -> Optional[TimeEntrySuggestion]:
        """Get the selected suggestion object."""
        selection = self._tree.selection()
        if not selection:
            return None
        suggestion_id = self._tree.item(selection[0])["text"]
        return self.db.get_suggestion(suggestion_id)

    def _edit_selected(self) -> None:
        """Edit the selected suggestion (project, minutes, notes)."""
        suggestion = self._get_selected_suggestion()
        if suggestion is None:
            messagebox.showinfo("Edit", "Select a suggestion to edit.")
            return

        self._open_edit_dialog(suggestion)

    def _open_edit_dialog(self, suggestion: TimeEntrySuggestion) -> None:
        """Open the edit dialog for a suggestion."""
        dialog = tk.Toplevel(self.app.root)
        dialog.title("Edit Suggestion")
        dialog.transient(self.app.root)
        dialog.grab_set()

        frame = ttk.Frame(dialog, style="App.TFrame")
        frame.pack(fill="both", expand=True, padx=24, pady=24)

        ttk.Label(
            frame, text="Project ID", style="MetricLabel.TLabel"
        ).pack(anchor="w")
        project_var = tk.StringVar(value=suggestion.project_id or "")
        ttk.Entry(frame, textvariable=project_var, width=40).pack(
            fill="x", pady=(4, 12)
        )

        ttk.Label(frame, text="Minutes", style="MetricLabel.TLabel").pack(
            anchor="w"
        )
        minutes_var = tk.StringVar(value=str(suggestion.suggested_minutes))
        ttk.Entry(frame, textvariable=minutes_var, width=40).pack(
            fill="x", pady=(4, 12)
        )

        ttk.Label(
            frame, text="Review Notes", style="MetricLabel.TLabel"
        ).pack(anchor="w")
        notes_var = tk.StringVar(value=suggestion.review_notes or "")
        ttk.Entry(frame, textvariable=notes_var, width=40).pack(
            fill="x", pady=(4, 24)
        )

        def _save() -> None:
            try:
                new_minutes = float(minutes_var.get())
                if new_minutes <= 0 or new_minutes > 24 * 60:
                    raise ValueError(
                        "Minutes must be between 0 and 1440."
                    )
            except ValueError as exc:
                messagebox.showerror("Edit Error", str(exc))
                return

            suggestion.project_id = project_var.get() or None
            suggestion.edited_minutes = new_minutes
            suggestion.review_notes = notes_var.get() or None
            self.db.upsert_suggestion(suggestion)
            self._refresh()
            dialog.destroy()

        btn_frame = ttk.Frame(frame, style="App.TFrame")
        btn_frame.pack(fill="x")
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(
            side="right", padx=(8, 0)
        )
        ttk.Button(btn_frame, text="Save", command=_save).pack(side="right")

    def _submit_selected(self) -> None:
        """Submit the selected suggestion for manager approval."""
        suggestion = self._get_selected_suggestion()
        if suggestion is None:
            messagebox.showinfo("Submit", "Select a suggestion to submit.")
            return

        actor = current_auth.actor
        if actor is None:
            messagebox.showerror("Submit Error", "No authenticated session.")
            return

        try:
            self._service.submit_suggestion(
                suggestion, actor_id=actor.id
            )
            self._refresh()
        except (ValueError, PermissionError) as exc:
            messagebox.showerror("Submit Error", str(exc))

    def _reject_selected(self) -> None:
        """Reject the selected suggestion."""
        suggestion = self._get_selected_suggestion()
        if suggestion is None:
            messagebox.showinfo("Reject", "Select a suggestion to reject.")
            return

        actor = current_auth.actor
        if actor is None:
            messagebox.showerror("Reject Error", "No authenticated session.")
            return

        try:
            self._service.reject_suggestion(
                suggestion, actor_id=actor.id
            )
            self._refresh()
        except (ValueError, PermissionError) as exc:
            messagebox.showerror("Reject Error", str(exc))

    def _split_selected(self) -> None:
        """Split the selected suggestion."""
        suggestion = self._get_selected_suggestion()
        if suggestion is None:
            messagebox.showinfo("Split", "Select a suggestion to split.")
            return

        actor = current_auth.actor
        if actor is None:
            messagebox.showerror("Split Error", "No authenticated session.")
            return

        split_minutes = simpledialog.askfloat(
            "Split Entry",
            f"Enter minutes for first part (total: {suggestion.suggested_minutes}):",
            minvalue=0.1,
            maxvalue=suggestion.suggested_minutes - 0.1,
        )
        if split_minutes is None:
            return

        try:
            self._service.split_suggestion(
                suggestion, split_minutes, actor_id=actor.id
            )
            self._refresh()
        except (ValueError, PermissionError) as exc:
            messagebox.showerror("Split Error", str(exc))

    def _merge_selected(self) -> None:
        """Merge selected suggestions."""
        selection = self._tree.selection()
        if len(selection) < 2:
            messagebox.showinfo(
                "Merge", "Select at least two suggestions to merge."
            )
            return

        suggestion_ids = [
            self._tree.item(sel)["text"] for sel in selection
        ]

        actor = current_auth.actor
        if actor is None:
            messagebox.showerror("Merge Error", "No authenticated session.")
            return

        try:
            self._service.merge_suggestions(
                suggestion_ids, actor_id=actor.id
            )
            self._refresh()
        except (ValueError, PermissionError) as exc:
            messagebox.showerror("Merge Error", str(exc))
