import csv
import pytest
from bimspend.app.shell import BIMSpendApp
from bimspend.db import Database
from bimspend.models import TimeEntryState
from bimspend.reporting import aggregate, build_report, export_csv


@pytest.mark.gui
def test_report_date_filter_grouping_csv_and_privacy(tmp_path):
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    app = BIMSpendApp(root=root, db_path=str(tmp_path / "report.db"))
    try:
        entry = app.db.list_time_entries()[0]
        from bimspend.review import submit_entry, approve_entry, bill_entry
        submit_entry(entry, entry.user_id)
        approve_entry(entry, "manager_demo")
        bill_entry(entry, 30, "manager_demo")
        app.db.upsert_time_entry(entry, actor_id="manager_demo")
        all_rows = build_report(app.db)
        assert any(r["billed_hours"] == 0.5 for r in all_rows)
        assert all("window_title" not in r for r in all_rows)
        assert build_report(app.db, "2025-01-01", "2025-01-31") == []
        assert build_report(app.db, "2026-10-05", "2026-10-05")
        with pytest.raises(ValueError):
            build_report(app.db, "2026-10-06", "2026-10-05")
        projects = aggregate(all_rows, "Projects")
        team = aggregate(all_rows, "Team")
        assert sum(r["billed_hours"] for r in projects) == 0.5
        assert any(r["user_id"] == entry.user_id for r in team)
        app.show_screen("reports")
        assert app.current_screen == "reports"
        app.screens["reports"].section.set("Projects")
        app.screens["reports"]._generate()
        assert app.screens["reports"].rows
        out = tmp_path / "report.csv"
        export_csv(out, all_rows)
        assert len(list(csv.DictReader(out.open(encoding="utf-8-sig")))) == len(all_rows)
    finally:
        app.destroy()


def test_csv_formula_neutralized(tmp_path):
    path = tmp_path / "safe.csv"
    export_csv(path, [{"section": "Projects", "project_name": "=SUM(1,2)"}])
    values = list(csv.DictReader(path.open(encoding="utf-8-sig")))
    assert values[0]["project_name"] == "'=SUM(1,2)"
