"""Base screen class for BIMSpend application screens.

All screens inherit from BaseScreen and receive the app instance for
access to the domain layer (db, models, etc.).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from bimspend.app.shell import BIMSpendApp


class BaseScreen(ttk.Frame):
    """Base class for all application screens."""

    def __init__(self, parent: ttk.Widget, app: BIMSpendApp):
        super().__init__(parent, style="App.TFrame")
        self.app = app
        self.db = app.db
        self.visible = False

    def show(self) -> None:
        """Show the screen."""
        self.pack(fill="both", expand=True)
        self.visible = True
        self.on_show()

    def hide(self) -> None:
        """Hide the screen."""
        self.pack_forget()
        self.visible = False

    def on_show(self) -> None:
        """Called when the screen becomes visible. Subclasses override."""
        pass

    def _section_header(self, title: str, subtitle: str = "") -> ttk.Frame:
        """Create a section header with title and optional subtitle."""
        frame = ttk.Frame(self, style="App.TFrame")
        frame.pack(fill="x", pady=(0, 16))

        ttk.Label(frame, text=title, style="Title.TLabel").pack(anchor="w")
        if subtitle:
            ttk.Label(frame, text=subtitle, style="Subtitle.TLabel").pack(anchor="w", pady=(2, 0))

        return frame

    def _metric_card(
        self,
        parent: ttk.Widget,
        label: str,
        value: str,
        sublabel: str = "",
        color: str = "#14324A",
    ) -> ttk.Frame:
        """Create a metric card: label + value + optional sublabel."""
        card = ttk.Frame(parent, style="Card.TFrame")
        card.pack(fill="x", padx=0, pady=4)

        inner = ttk.Frame(card, style="Card.TFrame")
        inner.pack(fill="x", padx=16, pady=12)

        ttk.Label(inner, text=label, style="MetricLabel.TLabel").pack(anchor="w")
        ttk.Label(
            inner, text=value, style="MetricValue.TLabel", foreground=color
        ).pack(anchor="w", pady=(2, 0))
        if sublabel:
            ttk.Label(inner, text=sublabel, style="MetricLabel.TLabel").pack(anchor="w")

        return card

    def _divider(self) -> ttk.Separator:
        """Create a horizontal divider."""
        sep = ttk.Separator(self, orient="horizontal")
        sep.pack(fill="x", pady=16)
        return sep

    def _info_panel(
        self, title: str, items: list[tuple[str, str]]
    ) -> ttk.Frame:
        """Create an info panel with labeled values."""
        panel = ttk.Frame(self, style="Card.TFrame")
        panel.pack(fill="x", pady=8)

        inner = ttk.Frame(panel, style="Card.TFrame")
        inner.pack(fill="x", padx=16, pady=12)

        ttk.Label(inner, text=title, style="MetricLabel.TLabel").pack(anchor="w", pady=(0, 8))

        for label, value in items:
            row = ttk.Frame(inner, style="Card.TFrame")
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=label, style="MetricLabel.TLabel").pack(side="left")
            ttk.Label(row, text=value, style="MetricValue.TLabel").pack(side="right")

        return panel
