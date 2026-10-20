import hashlib
import json
from pathlib import Path
import pytest
from scripts import simulate_activity as simulator


def test_boundaries_and_profiles(tmp_path, monkeypatch):
    base = tmp_path / "data" / "sandbox"
    base.mkdir(parents=True)
    sentinel = base / "existing.txt"
    sentinel.write_bytes(b"leave me alone")
    before = hashlib.sha256(sentinel.read_bytes()).hexdigest()
    monkeypatch.setattr(simulator, "BASE", base)
    monkeypatch.setattr(simulator, "__file__", str(tmp_path / "scripts" / "simulate_activity.py"))
    runs = []
    for profile in ("benign", "isolated", "archive", "burst"):
        manifest = json.loads(simulator.simulate(profile, pause=0).read_text())
        runs.append(manifest["run"])
        for row in manifest["files"]:
            assert Path(row["path"]).is_relative_to(manifest["run"])
            assert hashlib.sha256(Path(row["path"]).read_bytes()).hexdigest() == row["sha256"]
        assert hashlib.sha256(sentinel.read_bytes()).hexdigest() == before
    assert len(set(runs)) == 4
    with pytest.raises(ValueError):
        simulator.simulate("bad")
    link = tmp_path / "link"
    link.symlink_to(base, target_is_directory=True)
    monkeypatch.setattr(simulator, "BASE", link)
    with pytest.raises(ValueError):
        simulator.simulate()


def test_department_boundary(tmp_path, monkeypatch):
    base = tmp_path / "data" / "sandbox"
    monkeypatch.setattr(simulator, "BASE", base)
    monkeypatch.setattr(simulator, "__file__", str(tmp_path / "scripts" / "simulate_activity.py"))
    manifest = json.loads(simulator.simulate("benign", pause=0, department="finance").read_text())
    assert Path(manifest["run"]).is_relative_to(tmp_path / "data" / "sensitive-lab" / "finance")
    with pytest.raises(ValueError):
        simulator.simulate(department="../outside")
