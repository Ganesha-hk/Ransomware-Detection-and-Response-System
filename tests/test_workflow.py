from pathlib import Path
from fastapi.testclient import TestClient
from app.api.main import create_app
from tests.conftest import wait_for


def test_incident_pending_scoped_and_logical_files(config_path):
    with TestClient(create_app(config_path)) as c:
        r = c.app.state.runtime
        first = r.store.save("incidents", dict(root="root", status="active", peak_score=95))
        second = r.store.save("incidents", dict(root="other", status="closed", peak_score=95))
        for kind, src, dest in [
            ("created", "/root/a.txt", None),
            ("moved", "/root/a.txt", "/root/a.locked"),
        ]:
            event = r.store.save(
                "events",
                dict(
                    event_type=kind,
                    source_path=src,
                    destination_path=dest,
                    identity=None if kind == "created" else "1:2",
                    entropy=7.99,
                ),
            )
            r.store.save("incident_events", dict(incident_id=first["id"], event_id=event["id"]))
        with r.pending_lock:
            r.evidence_pending[first["id"]] = 1
        assert c.get("/incidents/" + first["id"]).json()["evidence_state"] == "pending"
        assert c.get("/incidents/" + second["id"]).json()["evidence_state"] == "complete"
        detail = c.get("/incidents/" + first["id"]).json()
        assert len(detail["logical_files"]) == 1
        assert detail["logical_files"][0]["path"] == "/root/a.locked"
        assert detail["logical_files"][0]["previous_paths"] == ["/root/a.txt"]
        status = c.get("/status").json()
        assert status["watch_paths"] == r.config.monitor.watch_paths
        assert status["window_seconds"] == r.config.detection.window_seconds


def test_scan_history_and_progress(runtime):
    root = Path(runtime.config.monitor.watch_paths[0])
    for i in range(55):
        (root / f"ordinary-{i}.txt").write_text("plain text")
    job = runtime.start_scan(str(root))
    wait_for(lambda: runtime.store.get("scan_jobs", job["id"])["status"] == "completed")
    final = runtime.store.get("scan_jobs", job["id"])
    assert final["count"] == 55
    assert final["failures"] == 0


def test_scan_history_endpoint(config_path):
    with TestClient(create_app(config_path)) as c:
        assert c.get("/scans").json() == []
        assert c.get("/scans?limit=201").status_code == 422
