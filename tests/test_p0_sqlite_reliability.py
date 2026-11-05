import sqlite3

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
