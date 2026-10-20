import math
import os
from pathlib import Path
import pytest
import yaml
from app.core.config import Settings, Detection, load
from app.core.entropy import entropy, sample
from app.core.paths import approved, safe_open
from app.detectors.rules import evaluate
from app.detectors.scoring import severity, score
from app.detectors.sliding_window import Window


@pytest.mark.parametrize("data,expected", [(b"", 0), (b"a" * 500, 0), (bytes(range(256)) * 8, 8)])
def test_entropy(data, expected):
    assert entropy(data) == expected


@pytest.mark.parametrize(
    "score_value,label",
    [
        (0, "Normal"),
        (39, "Normal"),
        (40, "Warning"),
        (69, "Warning"),
        (70, "Critical"),
        (100, "Critical"),
    ],
)
def test_boundaries(score_value, label):
    assert severity(score_value, Detection()) == label


@pytest.mark.parametrize(
    "n,random,moved,expected",
    [
        (3, False, False, 0),
        (1, True, False, 0),
        (5, True, False, 25),
        (50, True, False, 65),
        (50, False, True, 30),
        (50, True, True, 95),
    ],
)
def test_scenarios(n, random, moved, expected):
    files = {
        str(i): dict(changed=True, moved=moved, suffix_changed=moved, entropy=8 if random else 0)
        for i in range(n)
    }
    assert evaluate(files, Detection())["score"] == expected


def test_context():
    c = Detection(cpu_signal_enabled=True, unknown_program_signal_enabled=True)
    assert evaluate({}, c, [dict(cpu_percent=90, executable="/bad")], ["/good"])["score"] == 0
    supported = [dict(supported_candidate=True, cpu_percent=90, executable="/bad")]
    assert evaluate({}, c, supported, ["/good"])["score"] == 25
    assert evaluate({}, c, supported, [])["score"] == 15
    assert score(dict.fromkeys(c.weights, True), c)["score"] == 100


@pytest.mark.parametrize(
    "patch",
    [
        {"app": {"simulation_mode": False}},
        {"monitor": {"observer": "bad"}},
        {"detection": {"warning_min": 80, "critical_min": 70}},
        {"detection": {"weights": {"bad": 1}}},
        {
            "detection": {
                "weights": dict(
                    rapid_high_entropy_writes=math.inf,
                    mass_rename=1,
                    high_entropy=1,
                    cpu_spike=1,
                    unknown_program=1,
                )
            }
        },
        {"detection": {"entropy_threshold": 9}},
        {"monitor": {"sample_bytes": 0}},
        {"unknown": 1},
    ],
)
def test_bad_settings(patch):
    with pytest.raises(ValueError):
        Settings.model_validate(patch)


@pytest.mark.parametrize(
    "paths", [["/"], [str(Path.home())], ["./data", "./data/nested"], ["./logs"], []]
)
def test_bad_paths(tmp_path, paths):
    p = tmp_path / "config.yaml"
    p.write_text(yaml.safe_dump(dict(monitor=dict(watch_paths=paths))))
    with pytest.raises(ValueError):
        load(p)


def test_sampling_paths(tmp_path):
    c = Settings()
    root = tmp_path / "sandbox"
    root.mkdir()
    normal = root / "a"
    normal.write_bytes(bytes(range(256)))
    assert sample(normal, root, c)["entropy"] == 8
    assert sample(root / "missing", root, c)["entropy"] is None
    link = root / "link"
    link.symlink_to(normal)
    assert not approved(link, root)
    assert not approved(root / ".." / "outside", root)
    assert not approved(normal, root, [str(normal)])
    assert not approved(tmp_path / "outside", root)
    fifo = root / "pipe"
    os.mkfifo(fifo)
    with pytest.raises(ValueError):
        safe_open(fifo, root)
    nested = root / "nested"
    nested.mkdir()
    (nested / "a").write_bytes(b"")
    with safe_open(nested / "a", root) as f:
        assert f.read() == b""


def test_window_dedup_expiry():
    now = [100.0]
    w = Window(lambda: now[0])
    c = Detection(window_seconds=1)
    for _ in range(100):
        w.add(dict(arrival=100, identity="one", source_path="/a", event_type="modified", entropy=8))
    assert w.result(c)["score"] == 0
    w.add(
        dict(
            arrival=100,
            identity="one",
            source_path="/a",
            destination_path="/b",
            event_type="moved",
            old_suffix=".txt",
            new_suffix=".locked",
            entropy=8,
        )
    )
    assert w.result(c)["facts"]["changed_files"] == 1
    now[0] = 101
    assert w.result(c)["facts"]["changed_files"] == 0
    assert w.aliases == {}
