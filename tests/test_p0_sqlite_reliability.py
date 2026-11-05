import sqlite3
import builtins
import pytest
import threading
import time

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


def test_version_tracking_preserves_legacy_project(tmp_path):
    path = str(tmp_path / "legacy.db")
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT NOT NULL, client TEXT NOT NULL, standard_rate REAL NOT NULL, loaded_cost_rate REAL NOT NULL, is_billable INTEGER NOT NULL, created_at TEXT NOT NULL)")
        conn.execute("INSERT INTO projects VALUES ('old','Legacy','Synthetic',90,45,1,'2026-01-01T00:00:00Z')")
    db = Database(path)
    try:
        assert db.get_project("old").name == "Legacy"
        assert db.conn.execute("SELECT version FROM schema_version").fetchall()[0][0] == 1
    finally:
        db.close()
    reopened = Database(path)
    try:
        assert reopened.conn.execute("SELECT count(*) FROM schema_version").fetchone()[0] == 1
        assert reopened.get_project("old").name == "Legacy"
    finally:
        reopened.close()


def test_nested_transaction_rolls_back_all_writes(tmp_path):
    db = Database(str(tmp_path / "atomic.db"))
    with pytest.raises(sqlite3.IntegrityError):
        with db.transaction():
            db.upsert_project(Project("first", "First", "Synthetic", 100, 50))
            db.upsert_project(Project("invalid", "Bad", None, 100, 50))
    assert db.list_projects() == []
    db.upsert_project(Project("after", "After", "Synthetic", 100, 50))
    assert [p.id for p in db.list_projects()] == ["after"]
    db.close()


def test_writer_waits_for_real_sqlite_lock_then_succeeds(tmp_path):
    path = str(tmp_path / "locked.db")
    first = Database(path)
    started = threading.Event()
    outcome = []

    def writer():
        started.set()
        second = Database(path)
        try:
            second.upsert_project(Project("second", "Second", "Synthetic", 100, 50))
            outcome.append("committed")
        finally:
            second.close()

    with first.transaction():
        first.upsert_project(Project("first", "First", "Synthetic", 100, 50))
        thread = threading.Thread(target=writer)
        thread.start()
        assert started.wait(2)
        time.sleep(0.15)
        assert not outcome
    thread.join(timeout=3)
    assert not thread.is_alive()
    assert outcome == ["committed"]
    assert {p.id for p in first.list_projects()} == {"first", "second"}
    first.close()
