import csv
import pytest
from bimspend.app.shell import BIMSpendApp
from bimspend.auth import SessionManager, hash_password
from bimspend.db import Database
from bimspend.identity import Role, current_auth
from bimspend.models import TeamMember, TimeEntryState
from bimspend.reporting import aggregate, build_report, export_csv
from bimspend.review import submit_entry, approve_entry, bill_entry


@pytest.mark.gui
def test_report_date_filter_grouping_csv_and_privacy(tmp_path):
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    app = BIMSpendApp(root=root, db_path=str(tmp_path / "report.db"))
    try:
        # Set up company-scoped auth for timesheet transitions (SH-001/SH-002)
        app.db.upsert_company("report-co", "Report Company", is_active=True)
        app.db.upsert_member(TeamMember("designer_01", "Designer", "designer", 95, True))
        app.db.upsert_member(TeamMember("manager_01", "Manager", "manager", 120, True))
        app.db.upsert_company_member("report-co", "designer_01", "designer")
        app.db.upsert_company_member("report-co", "manager_01", "manager")
        app.db.upsert_user_credential("designer_01", "designer_01", hash_password("demo"))
        app.db.upsert_user_credential("manager_01", "manager_01", hash_password("demo"))

        entry = app.db.list_time_entries()[0]
        sm = SessionManager(app.db)

        # Designer submits own entry
        sm.login("designer_01", "demo", company_id="report-co")
        assert current_auth.actor.role == Role.DESIGNER
        submit_entry(entry)
        app.db.upsert_time_entry(entry)

        # Manager approves and bills
        sm.logout()
        sm.login("manager_01", "demo", company_id="report-co")
        assert current_auth.actor.role == Role.MANAGER
        approve_entry(entry)
        app.db.upsert_time_entry(entry)
        bill_entry(entry, 30)
        app.db.upsert_time_entry(entry, actor_id="manager_01")

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
