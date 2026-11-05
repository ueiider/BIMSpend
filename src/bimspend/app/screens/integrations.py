"""Synthetic-only integration console. No live connection controls."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from bimspend.app.screens.base import BaseScreen
from bimspend.integrations import (AttributionRules, MiruMockExport,
                                    ingest_synthetic_batch, parse_activitywatch, parse_revit, suggest)
from bimspend.models import TimeEntryState


class IntegrationsScreen(BaseScreen):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.events = []
        self.rules = AttributionRules({}, {})
        self.mock = MiruMockExport()
        self.last_result = "No synthetic import yet"

    def on_show(self):
        for widget in self.winfo_children():
            widget.destroy()
        self._section_header("Integrations", "Mock services only — live collection disabled")
        counts = {name: sum(e.source == name for e in self.db.list_events()) for name in ("activitywatch", "revit")}
        for name, detail in (("ActivityWatch", f"Mock Ready · {counts['activitywatch']} local synthetic events · AFK excluded · no live connection"),
                             ("Revit", f"Mock Ready · {counts['revit']} local synthetic events · no add-in installed"),
                             ("Miru", "Mock Ready · in-memory export only · endpoint not configured")):
            frame = ttk.LabelFrame(self, text=name, padding=12)
            frame.pack(fill="x", pady=6)
            ttk.Label(frame, text=detail).pack(anchor="w")
        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=12)
        for title, action in (("Load Synthetic Events", self.load_events),
                              ("Preview Normalized Events", self.preview),
                              ("Import Synthetic Events", self.import_events),
                              ("Inspect Integration Diagnostics", self.diagnostics),
                              ("Generate Mock Miru Export", self.mock_export)):
            ttk.Button(actions, text=title, command=action).pack(anchor="w", pady=3)
        self.output = tk.Text(self, height=12, wrap="word")
        self.output.pack(fill="both", expand=True)
        self._write(self.last_result)

    def _write(self, value):
        self.last_result = str(value)
        self.output.delete("1.0", "end")
        self.output.insert("end", self.last_result)

    def load_events(self):
        """Fixed demonstrator; no watcher, Revit installation or file access."""
        projects = [p for p in self.db.list_projects() if not p.is_archived]
        if not projects:
            self._write("Error: create a project before loading the synthetic demonstrator")
            return
        project = projects[0]
        self.rules = AttributionRules({"SYNTHETIC-MODEL-001": project.id}, {})
        window = [{"id": 90001, "timestamp": "2026-01-02T09:00:00+11:00", "duration": 3600,
                   "data": {"app": "Revit", "title": "Synthetic window"}}]
        idle = [{"id": 90002, "timestamp": "2026-01-02T09:45:00+11:00", "duration": 300,
                 "data": {"status": "afk"}}]
        revit = [{"schema_version": 1, "event_id": "synthetic-session-001", "kind": "active",
                  "document_id": "SYNTHETIC-MODEL-001", "started_at": "2026-01-02T09:15:00+11:00",
                  "ended_at": "2026-01-02T09:45:00+11:00"}]
        self.events = (parse_activitywatch("bimspend-synthetic-window", "currentwindow", window, "designer_01") +
                       parse_activitywatch("bimspend-synthetic-afk", "afkstatus", idle, "designer_01") +
                       parse_revit(revit, "designer_01"))
        self._write(f"Loaded {len(self.events)} synthetic events for {project.name}; live services remain disabled.")

    def preview(self):
        if not self.events:
            self._write("Load synthetic events first")
            return
        suggestions = suggest(self.events, self.db.list_projects(), self.rules)
        self._write("Synthetic preview — no records written:\n" + "\n".join(
            f"{s.attributed_minutes:.1f} min · {s.project_id or 'Unassigned'} · {s.correlation_method}"
            for s in suggestions))

    def import_events(self):
        if not self.events:
            self._write("Load synthetic events first")
            return
        try:
            result = ingest_synthetic_batch(self.db, self.events, self.rules)
        except Exception as exc:
            self._write(f"Synthetic import error: {exc}")
            return
        self._write(f"Synthetic import: {result['events']} new events, {result['suggestions']} suggestions, "
                    f"{result['pending_entries']} pending entries; existing reviews preserved. "
                    f"Skipped {len(self.events) - result['events']} repeated source events.")

    def diagnostics(self):
        self._write("ActivityWatch: disabled, local API never contacted. Revit: no add-in. "
                    "Miru: mock only, no remote endpoint. SQLite: local synthetic preview. "
                    f"Recorded events: {len(self.db.list_events())}.")

    def mock_export(self):
        eligible = [e for e in self.db.list_time_entries() if e.state == TimeEntryState.APPROVED]
        if not eligible:
            self._write("No approved time entries eligible for synthetic Miru mock export")
            return
        if not messagebox.askyesno("Synthetic export", "Create in-memory mock receipts for approved entries? No network traffic will occur."):
            return
        for entry in eligible:
            self.mock.export(entry.id, entry.project_id, entry.minutes, approved=True, explicitly_requested=True)
        self._write(f"Mock receipts: {len(self.mock.exported)} unique approved entries; no live synchronization.")
