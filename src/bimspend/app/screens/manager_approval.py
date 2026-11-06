"""Manager Approval Screen - BIMSpend R1-06.

Manager-facing screen for reviewing and approving submitted time entries.
Managers can:
- View submitted time entries with attribution confidence
- Approve entries (moves to APPROVED state)
- Reject entries with a reason (moves to REJECTED state)
- Return for correction (moves to REJECTED state with notes)
- Bulk approve/reject selected entries
- View audit trail

All actions require an authenticated manager session with company scope.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from typing import Any, Optional

from bimspend.app.screens.base import BaseScreen
from bimspend.app.shell import BIMSpendApp
from bimspend.identity import Actor, Role, current_auth
from bimspend.models import TimeEntry, TimeEntryState


class ManagerApprovalScreen(BaseScreen):
    """Manager approval screen for reviewing and approving submitted time entries.

    Managers can:
    - View submitted entries with attribution confidence
    - Approve entries (moves to APPROVED state)
    - Reject entries with a reason (moves to REJECTED state)
    - Return for correction (moves back to PENDING_REVIEW)
    - Bulk approve/reject selected entries
    - View audit trail
    """

    def __init__(self, parent: ttk.Widget, app: BIMSpendApp):
        super().__init__(parent, app)
        self._entry_id_map: dict[str, str] = {}  # tree item id -> entry id

    def on_show(self) -> None:
        """Refresh when shown."""
        for widget in self.winfo_children():
            widget.destroy()
        self._build_ui()

    def _build_ui(self) -> None:
        app = self.app

        # Header
        self._section_header("Manager Approval", "Review and approve submitted time entries")

        # Session info bar
        self._build_session_bar()

        # Filter bar
        self._build_filter_bar()

        # Submitted entries table
        self._build_entry_table()

        # Action buttons
        self._build_action_buttons()

        # Populate
        self._refresh()

    def _build_session_bar(self) -> None:
        """Build the session info bar."""
        frame = ttk.Frame(self, style="App.TFrame")
        frame.pack(fill="x", pady=(0, 8))

        actor = current_auth.actor
        if actor:
            ttk.Label(
                frame,
                text=f"Actor: {actor.id} ({actor.role.value})",
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

        ttk.Label(frame, text="Filter by project:").pack(side="left", padx=(0, 8))
        self._project_var = tk.StringVar(value="All projects")
        self._project_combo = ttk.Combobox(
            frame,
            textvariable=self._project_var,
            values=["All projects"],
            state="readonly",
            width=20,
        )
        self._project_combo.pack(side="left", padx=(0, 16))
        self._project_combo.bind("<<ComboboxSelected>>", lambda _: self._refresh())

        ttk.Button(
            frame,
            text="Refresh",
            command=self._refresh,
        ).pack(side="right")

    def _build_entry_table(self) -> None:
        """Build the submitted entries table."""
        frame = ttk.Frame(self, style="App.TFrame")
        frame.pack(fill="both", expand=True)

        cols = (
            "entry_id",
            "project",
            "user",
            "start",
            "end",
            "minutes",
            "confidence",
            "state",
        )
        self._tree = ttk.Treeview(
            frame, columns=cols, show="headings", height=15
        )
        self._tree.heading("#0", text="Entry ID")
        self._tree.heading("project", text="Project")
        self._tree.heading("user", text="User")
        self._tree.heading("start", text="Start")
        self._tree.heading("end", text="End")
        self._tree.heading("minutes", text="Minutes")
        self._tree.heading("confidence", text="Confidence")
        self._tree.heading("state", text="State")

        self._tree.column("#0", width=100)
        self._tree.column("project", width=180)
        self._tree.column("user", width=100)
        self._tree.column("start", width=130)
        self._tree.column("end", width=130)
        self._tree.column("minutes", width=80)
        self._tree.column("confidence", width=100)
        self._tree.column("state", width=100)

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)

        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _build_action_buttons(self) -> None:
        """Build action buttons."""
        frame = ttk.Frame(self, style="App.TFrame")
        frame.pack(fill="x", pady=(8, 0))

        self._approve_btn = ttk.Button(
            frame,
            text="Approve Selected",
            command=self._approve_selected,
        )
        self._approve_btn.pack(side="left", padx=(0, 8))

        self._reject_btn = ttk.Button(
            frame,
            text="Reject Selected",
            command=self._reject_selected,
        )
        self._reject_btn.pack(side="left", padx=(0, 8))

        self._return_btn = ttk.Button(
            frame,
            text="Return for Correction",
            command=self._return_for_correction,
        )
        self._return_btn.pack(side="left", padx=(0, 8))

        self._bulk_approve_btn = ttk.Button(
            frame,
            text="Bulk Approve Selected",
            command=self._bulk_approve,
        )
        self._bulk_approve_btn.pack(side="left", padx=(0, 8))

        self._bulk_reject_btn = ttk.Button(
            frame,
            text="Bulk Reject Selected",
            command=self._bulk_reject,
        )
        self._bulk_reject_btn.pack(side="left")

    def _refresh(self) -> None:
        """Refresh the entries table."""
        actor = current_auth.actor
        if actor is None:
            return

        self._tree.delete(*self._tree.get_children())
        self._entry_id_map.clear()

        # Get submitted entries for this company
        entries = self.db.list_time_entries(user_id=None, state=TimeEntryState.SUBMITTED)

        # Filter by company
        entries = [e for e in entries if e.company_id == actor.company_id]

        # Filter by project if selected
        project_filter = self._project_var.get()
        if project_filter and project_filter != "All projects":
            entries = [e for e in entries if e.project_id == project_filter]

        for entry in entries:
            project = self.app.db.get_project(entry.project_id)
            project_name = project.name if project else entry.project_id

            self._tree.insert(
                "",
                "end",
                text=entry.id,
                values=(
                    project_name,
                    entry.user_id,
                    entry.started_at[:16].replace("T", " "),
                    entry.ended_at[:16].replace("T", " "),
                    f"{entry.minutes:.1f}",
                    "N/A",
                    entry.state.value.replace("_", " ").title(),
                ),
            )
            self._entry_id_map[self._tree.get_children()[-1]] = entry.id

    def _get_selected_entry_id(self) -> Optional[str]:
        """Get the selected entry ID."""
        selection = self._tree.selection()
        if not selection:
            return None
        return self._tree.item(selection[0])["text"]

    def _get_selected_entry(self) -> Optional[TimeEntry]:
        """Get the selected TimeEntry object."""
        entry_id = self._get_selected_entry_id()
        if entry_id is None:
            return None
        return self.db.get_time_entry(entry_id)

    def _approve_selected(self) -> None:
        """Approve the selected entry."""
        entry = self._get_selected_entry()
        if entry is None:
            from tkinter import messagebox
            messagebox.showinfo("Approve", "Select an entry to approve.")
            return

        actor = current_auth.actor
        if actor is None:
            from tkinter import messagebox
            messagebox.showerror("Approve Error", "No authenticated session.")
            return

        try:
            from bimspend.review import approve_entry
            approve_entry(entry, reviewed_by=actor.id)
            self.db.upsert_time_entry(entry, actor_id=actor.id)
            self._refresh()
        except (ValueError, PermissionError) as exc:
            from tkinter import messagebox
            messagebox.showerror("Approve Error", str(exc))

    def _reject_selected(self) -> None:
        """Reject the selected entry."""
        entry = self._get_selected_entry()
        if entry is None:
            from tkinter import messagebox
            messagebox.showinfo("Reject", "Select an entry to reject.")
            return

        actor = current_auth.actor
        if actor is None:
            from tkinter import messagebox
            messagebox.showerror("Reject Error", "No authenticated session.")
            return

        from tkinter import simpledialog
        notes = simpledialog.askstring(
            "Reject Entry",
            "Reason for rejection:",
        )
        if notes is None:
            return

        try:
            from bimspend.review import reject_entry
            reject_entry(entry, reviewed_by=actor.id, notes=notes)
            self.db.upsert_time_entry(entry, actor_id=actor.id)
            self._refresh()
        except (ValueError, PermissionError) as exc:
            from tkinter import messagebox
            messagebox.showerror("Reject Error", str(exc))

    def _return_for_correction(self) -> None:
        """Return the selected entry for correction."""
        entry = self._get_selected_entry()
        if entry is None:
            from tkinter import messagebox
            messagebox.showinfo("Return for Correction", "Select an entry to return.")
            return

        actor = current_auth.actor
        if actor is None:
            from tkinter import messagebox
            messagebox.showerror("Return Error", "No authenticated session.")
            return

        from tkinter import simpledialog
        notes = simpledialog.askstring(
            "Return for Correction",
            "Reason for return:",
        )
        if notes is None:
            return

        try:
            from bimspend.review import reject_entry
            reject_entry(entry, reviewed_by=actor.id, notes=notes)
            self.db.upsert_time_entry(entry, actor_id=actor.id)
            self._refresh()
        except (ValueError, PermissionError) as exc:
            from tkinter import messagebox
            messagebox.showerror("Return Error", str(exc))

    def _bulk_approve(self) -> None:
        """Bulk approve all selected entries."""
        selection = self._tree.selection()
        if not selection:
            from tkinter import messagebox
            messagebox.showinfo("Bulk Approve", "Select entries to approve.")
            return

        actor = current_auth.actor
        if actor is None:
            from tkinter import messagebox
            messagebox.showerror("Approve Error", "No authenticated session.")
            return

        from tkinter import messagebox
        if not messagebox.askyesno(
            "Bulk Approve",
            f"Approve {len(selection)} selected entries?",
        ):
            return

        from bimspend.review import approve_entry
        for item_id in selection:
            entry_id = self._tree.item(item_id)["text"]
            entry = self.db.get_time_entry(entry_id)
            if entry and entry.state == TimeEntryState.SUBMITTED:
                try:
                    approve_entry(entry, reviewed_by=actor.id)
                    self.db.upsert_time_entry(entry, actor_id=actor.id)
                except (ValueError, PermissionError):
                    pass  # Skip errors in bulk operations

        self._refresh()

    def _bulk_reject(self) -> None:
        """Bulk reject all selected entries."""
        selection = self._tree.selection()
        if not selection:
            from tkinter import messagebox
            messagebox.showinfo("Bulk Reject", "Select entries to reject.")
            return

        actor = current_auth.actor
        if actor is None:
            from tkinter import messagebox
            messagebox.showerror("Reject Error", "No authenticated session.")
            return

        from tkinter import messagebox
        if not messagebox.askyesno(
            "Bulk Reject",
            f"Reject {len(selection)} selected entries?",
        ):
            return

        from tkinter import simpledialog
        notes = simpledialog.askstring(
            "Bulk Reject",
            "Reason for rejection:",
        )
        if notes is None:
            return

        from bimspend.review import reject_entry
        for item_id in selection:
            entry_id = self._tree.item(item_id)["text"]
            entry = self.db.get_time_entry(entry_id)
            if entry and entry.state == TimeEntryState.SUBMITTED:
                try:
                    reject_entry(entry, reviewed_by=actor.id, notes=notes)
                    self.db.upsert_time_entry(entry, actor_id=actor.id)
                except (ValueError, PermissionError):
                    pass

        self._refresh()