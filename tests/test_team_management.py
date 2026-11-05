import pytest
from bimspend.db import Database
from bimspend.models import TeamMember, Project


def test_roster_assignments_rates_and_status_persist(tmp_path):
    path = str(tmp_path / "team.db")
    db = Database(path)
    db.upsert_project(Project("p", "Synthetic project", "Client", 150, 85))
    designer = TeamMember("m", "Designer", "designer", 95)
    db.upsert_member(designer)
    db.assign_member("m", "p")
    db.assign_member("m", "p")
    assert db.list_assignments("m") == ["p"]
    designer.loaded_cost_rate = 110
    designer.is_active = False
    db.upsert_member(designer)
    with pytest.raises(ValueError):
        db.assign_member("m", "p")
    with pytest.raises(ValueError):
        db.upsert_member(TeamMember("x", "Bad", "administrator", -2))
    db.close()
    db = Database(path)
    assert db.list_members() == [TeamMember("m", "Designer", "designer", 110, False)]
    assert db.list_assignments("m") == ["p"]
    db.close()


def test_team_screen_can_open_and_refresh(tmp_path):
    import tkinter as tk
    from bimspend.app.shell import BIMSpendApp
    root = tk.Tk()
    root.withdraw()
    app = BIMSpendApp(root=root, db_path=str(tmp_path / "ui.db"))
    try:
        app.show_screen("team")
        assert app.current_screen == "team"
        app.db.upsert_member(TeamMember("m", "Designer", "designer", 80))
        app.screens["team"].on_show()
        assert len(app.screens["team"].tree.get_children()) == 1
    finally:
        app.destroy()
