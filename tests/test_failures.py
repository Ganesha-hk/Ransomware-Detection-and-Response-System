import os
import sqlite3
import time
from pathlib import Path
from unittest.mock import MagicMock
import pytest
import psutil
from sqlalchemy.exc import OperationalError
from app.core.config import Settings
from app.core.entropy import sample
from app.database.session import Store
from app.detectors.process_monitor import ProcessSampler
from app.detectors.sliding_window import Window
from app.services.runtime import Runtime
from tests.conftest import wait_for


def test_permission_denied(monkeypatch, tmp_path):
    def denied(*args):
        raise PermissionError("denied")

    monkeypatch.setattr("app.core.entropy.safe_open", denied)
    assert sample(tmp_path / "x", tmp_path, Settings())["sampling_status"] == "PermissionError"


def test_unstable_sample(monkeypatch, tmp_path):
    path = tmp_path / "x"
    path.write_bytes(b"hello")
    real = os.fstat
    n = [0]

    def changing(fd):
        result = real(fd)
        n[0] += 1
        proxy = MagicMock()
        proxy.st_size = result.st_size
        proxy.st_mtime_ns = result.st_mtime_ns + n[0]
        proxy.st_dev = result.st_dev
        proxy.st_ino = result.st_ino
        proxy.st_mode = result.st_mode
        return proxy

    monkeypatch.setattr("app.core.entropy.os.fstat", changing)
    assert sample(path, tmp_path, Settings())["sampling_status"] == "unstable"


def test_database_lock_is_bounded(tmp_path):
    path = tmp_path / "db"
    store = Store(path, timeout=30)
    conn = sqlite3.connect(path)
    conn.execute("BEGIN IMMEDIATE")
    start = time.monotonic()
    with pytest.raises(OperationalError):
        store.save("events", {})
    assert time.monotonic() - start < 1
    conn.rollback()
    conn.close()
    assert store.save("events", {})
    store.close()


def test_process_denied_and_disappearing(monkeypatch):
    vanished = MagicMock()
    vanished.pid = 1
    vanished.create_time.side_effect = psutil.NoSuchProcess(1)
    denied = MagicMock()
    denied.pid = 2
    denied.create_time.return_value = 123.0
    denied.ppid.return_value = 1
    denied.name.return_value = "example"
    denied.exe.side_effect = psutil.AccessDenied(2)
    denied.memory_info.return_value.rss = 1024
    denied.io_counters.side_effect = psutil.AccessDenied(2)
    denied.cpu_percent.return_value = 5
    monkeypatch.setattr(
        "app.detectors.process_monitor.psutil.process_iter", lambda: [vanished, denied]
    )
    sampler = ProcessSampler()
    first = sampler.sample(1)[0]
    assert first["executable"] is None and first["cpu_percent"] is None
    second = sampler.sample(2)[0]
    assert second["cpu_percent"] == 5 and second["write_bytes_per_second"] is None
    assert second["confidence"] == "unknown" and not second["writer"]


def test_move_alias_joins_missing_sample():
    w = Window(lambda: 1)
    w.add(dict(arrival=1, source_path="/a.txt", event_type="modified", identity=None, entropy=None))
    w.add(
        dict(
            arrival=1,
            source_path="/a.txt",
            destination_path="/b.locked",
            event_type="moved",
            identity="1:2",
            old_suffix=".txt",
            new_suffix=".locked",
            entropy=8,
        )
    )
    result = w.result(Settings().detection)
    assert result["facts"]["changed_files"] == 1
    assert result["facts"]["valid_samples"] == 1
    assert result["facts"]["moved_files"] == 1


def test_restart_active_incident(config_path):
    r = Runtime(config_path)
    r.start()
    root = r.config.monitor.watch_paths[0]
    incident = r.store.save(
        "incidents",
        dict(
            root=root,
            status="active",
            peak_score=95,
            last_critical_at=__import__("app.core.models", fromlist=["utc"]).utc(),
        ),
    )
    r.store.save("scan_jobs", dict(status="running"))
    r.stop()
    r = Runtime(config_path)
    r.start()
    try:
        assert r.incidents.active[root]["id"] == incident["id"]
        assert r.incidents.active[root]["interrupted"]
        assert r.store.rows("scan_jobs")[0]["status"] == "interrupted"
    finally:
        r.stop()


def test_queue_data_loss_health(runtime):
    runtime.dropped = 1
    assert not runtime.status()["ready"]
    assert runtime.status()["monitor_state"] == "degraded"


def test_cooldown_and_new_incident(runtime):
    r = runtime
    root = r.config.monitor.watch_paths[0]
    with r.lock:
        critical = r.store.save("scores", dict(score=95, severity="Critical", contributions={}))
        normal = r.store.save("scores", dict(score=0, severity="Normal", contributions={}))
        r.incidents.update(root, critical, [])
        first = r.incidents.active[root]["id"]
        r.incidents.update(root, normal, [])
        r.incidents.update(root, critical, [])
        assert r.incidents.active[root]["id"] == first
    wait_for(lambda: r.store.get("incidents", first)["status"] == "closed")
    with r.lock:
        r.incidents.update(root, critical, [])
        assert r.incidents.active[root]["id"] != first


def test_shutdown_drains(runtime):
    root = Path(runtime.config.monitor.watch_paths[0])
    for i in range(30):
        (root / f"queued-{i}").write_bytes(b"hello")
    wait_for(lambda: runtime.store.rows("events"))
    # Fixture shutdown exercises draining the actual workers.


def test_cli(monkeypatch, config_path):
    from app.main import main

    called = []
    monkeypatch.setattr(
        "sys.argv",
        ["rdrs", "--config", str(config_path), "--watch", str(config_path.parent / "sandbox")],
    )
    monkeypatch.setattr("app.main.uvicorn.run", lambda app, **kw: called.append(kw))
    main()
    assert called[0]["workers"] == 1


def test_multiple_roots(config_path):
    import yaml

    config = yaml.safe_load(config_path.read_text())
    config["monitor"] = {"watch_paths": ["./one", "./two"]}
    config_path.write_text(yaml.safe_dump(config))
    r = Runtime(config_path)
    r.start()
    try:
        (Path(r.config.monitor.watch_paths[0]) / "x").write_bytes(os.urandom(20000))
        wait_for(lambda: r.store.rows("events"))
        wait_for(lambda: len(r.live) == 2)
        other = r.live[r.config.monitor.watch_paths[1]]
        assert other["facts"]["changed_files"] == 0
    finally:
        r.stop()
