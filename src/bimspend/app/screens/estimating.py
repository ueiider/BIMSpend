"""Historical Estimating view - BIMSpend R1-08.

Approved synthetic project history only.
Uses the BIMSpend design system.
"""

from tkinter import messagebox, ttk
from typing import Any

from bimspend.app.design import (
    APP_BG,
    CARD_BG,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from bimspend.app.screens.base import BaseScreen
from bimspend.app.shell import BIMSpendApp
from bimspend.estimating import estimate_from_history


class EstimatingScreen(BaseScreen):
    def __init__(self, parent: ttk.Widget, app: BIMSpendApp):
        super().__init__(parent, app)

    def on_show(self) -> None:
        for child in self.winfo_children():
            child.destroy()
        self._section_header(
            "Historical Estimating",
            "Approved synthetic project history only",
        )
        projects = self.db.list_projects()
        self.project_ids = {
            f"{p.name} ({p.id})": p.id for p in projects
        }
        self.project_box = ttk.Combobox(
            self,
            values=list(self.project_ids),
            state="readonly",
            width=50,
        )
        self.project_box.pack(anchor="w", pady=8)
        if projects:
            self.project_box.current(0)
        ttk.Button(
            self, text="Calculate reference", command=self._calculate
        ).pack(anchor="w")
        self.result = ttk.Label(
            self,
            text="Choose a target project.",
            style="Subtitle.TLabel",
            wraplength=680,
            justify="left",
        )
        self.result.pack(anchor="w", pady=16)

    def _calculate(self) -> None:
        project_id = self.project_ids.get(self.project_box.get())
        if not project_id:
            messagebox.showinfo("Estimate", "Select a project.")
            return
        estimate = estimate_from_history(self.db, project_id)
        if estimate is None:
            self.result.configure(
                text="No other projects have approved time yet."
            )
            return
        self.result.configure(
            text=(
                f"Reference projects: {estimate.reference_projects}\n"
                f"Median approved hours: {estimate.median_hours:.1f} h\n"
                f"Observed reference range: {estimate.low_hours:.1f} to "
                f"{estimate.high_hours:.1f} h\n"
                f"Indicative internal cost: A$"
                + format(estimate.estimated_cost_aud, ".2f")
                + "\n"
                + estimate.assumptions
            )
        )
