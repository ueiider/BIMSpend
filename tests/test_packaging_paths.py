from pathlib import Path
from bimspend.app import shell


def test_frozen_fixture_root_is_explicit(tmp_path, monkeypatch):
    import sys
    fixture = tmp_path / "data" / "synthetic"
    fixture.mkdir(parents=True)
    (fixture / "projects.json").write_text("[]", encoding="utf-8")
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert Path(shell._fixture("projects.json")).read_text(encoding="utf-8") == "[]"
