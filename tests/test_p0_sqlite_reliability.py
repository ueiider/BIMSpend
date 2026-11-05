import sqlite3
import builtins
import pytest

from bimspend.db import Database
from bimspend.models import Project


def test_wal_timeout_and_two_connections_preserve_writes(tmp_path):
    path = str(tmp_path / "preview.db")
    first = Database(path)
    second = Database(path)
    try:
        assert first.conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert first.conn.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
        first.upsert_project(Project("first", "First", "Synthetic", 100, 50))
        second.upsert_project(Project("second", "Second", "Synthetic", 100, 50))
        assert {p.id for p in first.list_projects()} == {"first", "second"}
    finally:
        first.close()
        second.close()


@pytest.mark.gui
def test_startup_without_external_adapter_modules(tmp_path, monkeypatch):
    import tkinter as tk
    from bimspend.app.shell import BIMSpendApp
    original_import = builtins.__import__

    def without_optional(name, *args, **kwargs):
        if name.startswith("bimspend.adapters.activitywatch") or name.startswith("bimspend.adapters.miru"):
            raise ImportError("External adapter unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_optional)
    root = tk.Tk()
    root.withdraw()
    app = BIMSpendApp(root=root, db_path=str(tmp_path / "preview.db"))
    try:
        assert app.db.list_projects()
        assert app.db.list_events()
    finally:
        app.db.close()
        root.destroy()
