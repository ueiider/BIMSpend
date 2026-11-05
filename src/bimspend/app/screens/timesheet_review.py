"""Timesheet Review screen.

Designer submits pending entries; manager approves/rejects submitted
entries. Billing is a separate explicit action (not shown here —
requires separate billing workflow).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from bimspend.app.screens.base import BaseScreen
from bimspend.app.shell import BIMSpendApp
from bimspend.models import TimeEntry, TimeEntryState
from bimspend.review import submit_entry, approve_entry, reject_entry


class TimesheetReviewScreen(BaseScreen):
    """Timesheet review: designer submits, manager approves/rejects."""

    def __init__(self, parent: ttk.Widget, app: BIMSpendApp):
        super().__init__(parent, app)
        self.current_user = "designer_01"  # synthetic designer; not authenticated

    def on_show(self) -> None:
        for widget in self.winfo_children():
            widget.destroy()
        self._build_ui()

    def _build_ui(self) -> None:
        app = self.app

        # Header
        self._section_header("Timesheet Review", "Designer submits; manager approves or returns")

        # Action bar
        action_frame = ttk.Frame(self, style="App.TFrame")
        action_frame.pack(fill="x", pady=(0, 12))

        ttk.Label(
            action_frame, text="Current user: " + self.current_user, style="MetricLabel.TLabel"
        ).pack(side="left", padx=(0, 16))

        ttk.Button(
            action_frame,
            text="Refresh",
            command=self._refresh,
        ).pack(side="right")

        # Two panes: Pending review (designer) and Submitted (manager)
        panes = ttk.Frame(self, style="App.TFrame")
        panes.pack(fill="both", expand=True)

        # Left: Pending review
        left = ttk.Frame(panes, style="App.TFrame")
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        ttk.Label(
            left, text="Pending Review (Designer)", style="MetricLabel.TLabel", font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", pady=(0, 8))

        self.pending_tree = ttk.Treeview(
            left, columns=("project", "minutes", "state"), show="headings", height=12
        )
        self.pending_tree.heading("project", text="Project")
        self.pending_tree.heading("minutes", text="Minutes")
        self.pending_tree.heading("state", text="State")
        self.pending_tree.column("project", width=200)
        self.pending_tree.column("minutes", width=80)
        self.pending_tree.column("state", width=120)

        p_scroll = ttk.Scrollbar(left, orient="vertical", command=self.pending_tree.yview)
        self.pending_tree.configure(yscrollcommand=p_scroll.set)

        self.pending_tree.pack(side="left", fill="both", expand=True)
        p_scroll.pack(side="right", fill="y")

        # Pending action buttons
        pending_btns = ttk.Frame(left, style="App.TFrame")
        pending_btns.pack(fill="x", pady=(8, 0))

        ttk.Button(
            pending_btns,
            text="Submit Selected",
            command=self._submit_selected,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            pending_btns,
            text="Reset to Pending",
            command=self._reset_selected,
        ).pack(side="left")

        # Right: Submitted (manager)
        right = ttk.Frame(panes, style="App.TFrame")
        right.pack(side="right", fill="both", expand=True, padx=(8, 0))

        ttk.Label(
            right, text="Submitted (Manager Approval)", style="MetricLabel.TLabel", font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", pady=(0, 8))

        self.submitted_tree = ttk.Treeview(
            right, columns=("project", "user", "minutes", "state"), show="headings", height=12
        )
        self.submitted_tree.heading("project", text="Project")
        self.submitted_tree.heading("user", text="User")
        self.submitted_tree.heading("minutes", text="Minutes")
        self.submitted_tree.heading("state", text="State")
        self.submitted_tree.column("project", width=180)
        self.submitted_tree.column("user", width=100)
        self.submitted_tree.column("minutes", width=80)
        self.submitted_tree.column("state", width=100)

        s_scroll = ttk.Scrollbar(right, orient="vertical", command=self.submitted_tree.yview)
        self.submitted_tree.configure(yscrollcommand=s_scroll.set)

        self.submitted_tree.pack(side="left", fill="both", expand=True)
        s_scroll.pack(side="right", fill="y")

        # Manager action buttons
        manager_btns = ttk.Frame(right, style="App.TFrame")
        manager_btns.pack(fill="x", pady=(8, 0))

        ttk.Button(
            manager_btns,
            text="Approve Selected",
            command=self._approve_selected,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            manager_btns,
            text="Reject Selected",
            command=self._reject_selected,
        ).pack(side="left")

        # Billing is a separate manager action after approval.
        approved_frame = ttk.Frame(self, style="App.TFrame")
        approved_frame.pack(fill="x", pady=(12, 0))
        ttk.Label(approved_frame, text="Approved, not yet billed",
                  style="MetricLabel.TLabel").pack(anchor="w")
        self.approved_tree = ttk.Treeview(
            approved_frame, columns=("project", "minutes", "billed"),
            show="headings", height=4)
        for col, title in (("project", "Project"), ("minutes", "Approved minutes"),
                           ("billed", "Billed minutes")):
            self.approved_tree.heading(col, text=title)
            self.approved_tree.column(col, width=160)
        self.approved_tree.pack(fill="x")
        ttk.Button(approved_frame, text="Bill selected explicitly",
                   command=self._bill_selected).pack(anchor="w", pady=4)
        ttk.Button(pending_btns, text="Edit minutes",
                   command=self._edit_selected).pack(side="left", padx=8)

        # Populate
        self._refresh()

    def _refresh(self) -> None:
        """Refresh both trees from the database."""
        # Clear
        for item in self.pending_tree.get_children():
            self.pending_tree.delete(item)
        for item in self.submitted_tree.get_children():
            self.submitted_tree.delete(item)

        for item in self.approved_tree.get_children():
            self.approved_tree.delete(item)

        entries = self.app.db.list_time_entries()
        projects = {p.id: p for p in self.app.projects}

        for entry in entries:
            project = projects.get(entry.project_id)
            project_name = project.name if project else entry.project_id

            if entry.state in (TimeEntryState.PENDING_REVIEW, TimeEntryState.REJECTED):
                self.pending_tree.insert(
                    "",
                    "end",
                    text=entry.id,
                    values=(project_name, f"{entry.minutes:.0f}", entry.state.value.replace("_", " ").title()),
                )
            elif entry.state == TimeEntryState.APPROVED:
                self.approved_tree.insert(
                    "", "end", text=entry.id,
                    values=(project_name, f"{entry.minutes:.0f}",
                            f"{entry.billed_minutes:.0f}"),
                )
            elif entry.state == TimeEntryState.SUBMITTED:
                self.submitted_tree.insert(
                    "",
                    "end",
                    text=entry.id,
                    values=(project_name, entry.user_id, f"{entry.minutes:.0f}", entry.state.value),
                )

    def _submit_selected(self) -> None:
        """Designer submits selected pending entry."""
        selection = self.pending_tree.selection()
        if not selection:
            from tkinter import messagebox
            messagebox.showinfo("Submit", "Please select a pending entry to submit.")
            return

        entry_id = self.pending_tree.item(selection[0])["text"]
        entry = self.app.db.get_time_entry(entry_id)
        if not entry:
            return

        try:
            submit_entry(entry, submitted_by=self.current_user)
            self.app.db.upsert_time_entry(entry, actor_id=self.current_user)
            self._refresh()
        except (ValueError, PermissionError) as exc:
            from tkinter import messagebox
            messagebox.showerror("Submit Error", str(exc))

    def _reset_selected(self) -> None:
        """Reset rejected entry to pending."""
        selection = self.pending_tree.selection()
        if not selection:
            return

        entry_id = self.pending_tree.item(selection[0])["text"]
        entry = self.app.db.get_time_entry(entry_id)
        if not entry:
            return

        from bimspend.review import reset_to_pending

        try:
            reset_to_pending(entry, self.current_user)
            self.app.db.upsert_time_entry(entry, actor_id=self.current_user)
            self._refresh()
        except (ValueError, PermissionError) as exc:
            from tkinter import messagebox
            messagebox.showerror("Reset Error", str(exc))

    def _approve_selected(self) -> None:
        """Manager approves submitted entry."""
        selection = self.submitted_tree.selection()
        if not selection:
            from tkinter import messagebox
            messagebox.showinfo("Approve", "Please select a submitted entry to approve.")
            return

        entry_id = self.submitted_tree.item(selection[0])["text"]
        entry = self.app.db.get_time_entry(entry_id)
        if not entry:
            return

        try:
            approve_entry(entry, reviewed_by="manager_demo")
            self.app.db.upsert_time_entry(entry, actor_id="manager_demo")
            self._refresh()
        except (ValueError, PermissionError) as exc:
            from tkinter import messagebox
            messagebox.showerror("Approve Error", str(exc))

    def _reject_selected(self) -> None:
        """Manager rejects submitted entry."""
        selection = self.submitted_tree.selection()
        if not selection:
            from tkinter import messagebox
            messagebox.showinfo("Reject", "Please select a submitted entry to reject.")
            return

        entry_id = self.submitted_tree.item(selection[0])["text"]
        entry = self.app.db.get_time_entry(entry_id)
        if not entry:
            return

        from tkinter import simpledialog

        reason = simpledialog.askstring("Reject Entry", "Reason for rejection:")
        if reason is None:
            return

        try:
            reject_entry(entry, reviewed_by="manager_demo", notes=reason)
            self.app.db.upsert_time_entry(entry, actor_id="manager_demo")
            self._refresh()
        except (ValueError, PermissionError) as exc:
            from tkinter import messagebox
            messagebox.showerror("Reject Error", str(exc))


    def _edit_selected(self) -> None:
        from tkinter import simpledialog, messagebox
        selected = self.pending_tree.selection()
        if not selected:
            messagebox.showinfo("Edit", "Select a pending entry.")
            return
        entry = self.db.get_time_entry(self.pending_tree.item(selected[0])["text"])
        if entry is None:
            return
        minutes = simpledialog.askfloat("Edit time", "Confirmed minutes:",
                                        initialvalue=entry.minutes)
        if minutes is None:
            return
        from bimspend.review import edit_entry
        try:
            edit_entry(entry, minutes, self.current_user)
            self.db.upsert_time_entry(entry, actor_id=self.current_user)
            self._refresh()
        except (ValueError, PermissionError) as exc:
            messagebox.showerror("Edit Error", str(exc))

    def _bill_selected(self) -> None:
        from tkinter import simpledialog, messagebox
        selected = self.approved_tree.selection()
        if not selected:
            messagebox.showinfo("Bill", "Select an approved entry.")
            return
        entry = self.db.get_time_entry(self.approved_tree.item(selected[0])["text"])
        if entry is None:
            return
        minutes = simpledialog.askfloat("Explicit billing", "Billed minutes:",
                                        initialvalue=entry.minutes)
        if minutes is None:
            return
        from bimspend.review import bill_entry
        try:
            bill_entry(entry, minutes, reviewed_by="manager_demo")
            self.db.upsert_time_entry(entry, actor_id="manager_demo")
            self._refresh()
        except (ValueError, PermissionError) as exc:
            messagebox.showerror("Billing Error", str(exc))
