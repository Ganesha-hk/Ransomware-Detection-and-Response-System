import hashlib
import os
from pathlib import Path
from tests.conftest import wait_for
from app.services.runtime import Runtime


def burst(root, n=25):
    files = []
    for i in range(n):
        p = root / f"{i}.txt"
        p.write_bytes(b"baseline" * 100)
        files.append(p)
    import time

    time.sleep(0.2)
    for p in files:
        p.write_bytes(os.urandom(20000))
    for p in files:
        p.rename(p.with_suffix(".locked"))
    return [p.with_suffix(".locked") for p in files]


def test_live_pipeline_reports_decay_restart(runtime, config_path):
    r = runtime
    root = Path(r.config.monitor.watch_paths[0])
    files = burst(root)
    before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    wait_for(lambda: r.status()["score"] == 95)
    incident = wait_for(lambda: r.store.rows("incidents"))[0]
    assert incident["peak_score"] == 95
    wait_for(lambda: r.responses.unfinished_tasks == 0)
    assert len(r.store.rows("incidents")) == 1
    copies = r.store.rows("evidence_files", 200, incident_id=incident["id"])
    assert copies
    for e in copies:
        if e["status"] == "copied":
            assert (
                hashlib.sha256(
                    (Path(r.config.response.evidence_dir) / e["stored_path"]).read_bytes()
                ).hexdigest()
                == e["sha256"]
            )
    assert before == {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    for format in ("json", "csv"):
        report = r.reports.generate(incident["id"], format)
        data = (Path(r.config.reports.output_dir) / report["path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == report["sha256"]
    files[0].unlink()
    wait_for(lambda: any(e["event_type"] == "deleted" for e in r.store.rows("events", 200)))
    wait_for(lambda: r.status()["score"] == 0)
    wait_for(lambda: r.store.get("incidents", incident["id"])["status"] == "closed")
    assert len(r.store.rows("reports")) == 2  # Closure must not generate unselected formats.
    assert not r.errors
    assert r.store.rows("processes")
    with __import__("pytest").raises(RuntimeError):
        Runtime(config_path).start()


def test_queue_overflow_and_scan(config_path):
    r = Runtime(config_path)
    from queue import Queue

    r.queue = Queue(1)
    root = r.config.monitor.watch_paths[0]
    r.enqueue(root, "created", root + "/one")
    r.enqueue(root, "created", root + "/two")
    assert r.dropped == 1
    r.enqueue(root, "modified", root + "/repeat")
    r.enqueue(root, "modified", root + "/repeat")
    assert r.suppressed == 1
    r.enqueue(root, "created", "/outside")
    r.stopping.set()
    r.enqueue(root, "created", root + "/three")


def test_scan_does_not_trigger(runtime):
    r = runtime
    root = Path(r.config.monitor.watch_paths[0])
    # Inventory an existing high entropy file; source_kind stays scan.
    (root / "single").write_bytes(os.urandom(20000))
    job = r.start_scan(str(root))
    wait_for(lambda: r.store.get("scan_jobs", job["id"])["status"] == "completed")
    assert any(e["source_kind"] == "scan" for e in r.store.rows("events"))
    assert r.status()["score"] == 0
