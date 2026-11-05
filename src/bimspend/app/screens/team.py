"""Local synthetic team roster and project assignments."""
from __future__ import annotations

import uuid
from tkinter import simpledialog, messagebox, ttk
from bimspend.app.screens.base import BaseScreen
from bimspend.models import TeamMember


class TeamScreen(BaseScreen):
    def on_show(self) -> None:
        for widget in self.winfo_children():
            widget.destroy()
        self._section_header("Team", "Synthetic roster, roles, rates and assignments")
        self.tree = ttk.Treeview(
            self, columns=("id", "role", "cost", "status", "projects"),
            show="headings", height=13,
        )
        for col, label in (("id", "ID"), ("role", "Role"),
                           ("cost", "Internal A$/h"), ("status", "Status"),
                           ("projects", "Project IDs")):
            self.tree.heading(col, text=label)
            self.tree.column(col, width=125 if col != "projects" else 200)
        self.tree.pack(fill="both", expand=True)
        buttons = ttk.Frame(self, style="App.TFrame")
        buttons.pack(fill="x", pady=10)
        for label, callback in (("Add member", self._add), ("Edit member", self._edit),
                                ("Deactivate", self._deactivate),
                                ("Assign project", self._assign)):
            ttk.Button(buttons, text=label, command=callback).pack(side="left", padx=4)
        self._refresh()

    def _refresh(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        for member in self.db.list_members():
            self.tree.insert("", "end", text=member.name,
                             values=(member.id, member.role,
                                     f"{member.loaded_cost_rate:.2f}",
                                     "Active" if member.is_active else "Inactive",
                                     ", ".join(self.db.list_assignments(member.id))))

    def _selected(self) -> TeamMember | None:
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Team", "Select a member.")
            return None
        member_id = self.tree.item(selected[0])["values"][0]
        return next((m for m in self.db.list_members() if m.id == member_id), None)

    def _fields(self, member: TeamMember | None = None) -> None:
        name = simpledialog.askstring("Team", "Member name:",
                                      initialvalue=member.name if member else "")
        if name is None:
            return
        role = simpledialog.askstring("Team", "Role (designer or manager):",
                                      initialvalue=member.role if member else "designer")
        if role is None:
            return
        cost = simpledialog.askfloat("Team", "Loaded internal hourly cost (A$):",
                                     initialvalue=member.loaded_cost_rate if member else 85)
        if cost is None:
            return
        try:
            self.db.upsert_member(TeamMember(
                member.id if member else f"member_{uuid.uuid4().hex}",
                name.strip(), role.strip().lower(), cost,
                member.is_active if member else True,
            ))
            self._refresh()
        except ValueError as exc:
            messagebox.showerror("Team error", str(exc))

    def _add(self) -> None:
        self._fields()

    def _edit(self) -> None:
        member = self._selected()
        if member:
            self._fields(member)

    def _deactivate(self) -> None:
        member = self._selected()
        if member and messagebox.askyesno("Team", f"Deactivate {member.name}?"):
            member.is_active = False
            self.db.upsert_member(member)
            self._refresh()

    def _assign(self) -> None:
        member = self._selected()
        if not member:
            return
        choices = "\n".join(f"{p.id}: {p.name}" for p in self.db.list_projects()
                            if not p.is_archived)
        project_id = simpledialog.askstring("Assign project",
                                            f"Project ID:\n{choices}")
        if project_id is None:
            return
        try:
            self.db.assign_member(member.id, project_id.strip())
            self._refresh()
        except ValueError as exc:
            messagebox.showerror("Assignment error", str(exc))
