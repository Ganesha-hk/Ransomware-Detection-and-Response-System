from fastapi.testclient import TestClient
from app.api.main import create_app
from tests.conftest import wait_for


def test_api(config_path, monkeypatch):
    monkeypatch.setenv("RDRS_ADMIN_TOKEN", "test-token")
    with TestClient(create_app(config_path)) as c:
        assert c.get("/").status_code == 200
        assert c.get("/static/dashboard.js").status_code == 200
        for path in (
            "/health",
            "/status",
            "/events",
            "/alerts",
            "/incidents",
            "/reports",
            "/metrics",
            "/settings",
        ):
            assert c.get(path).status_code == 200
        assert c.get("/events?limit=201").status_code == 422
        assert c.get("/incidents/missing").status_code == 404
        assert c.get("/scans/missing").status_code == 404
        assert c.get("/reports/missing/download").status_code == 404
        assert c.get("/status", headers={"host": "evil.example"}).status_code == 400
        assert c.post("/scan", json={"root": "/"}).status_code == 401
        auth = {"Authorization": "Bearer test-token"}
        assert c.post("/scan", json={"root": "/"}, headers=auth).status_code == 422
        settings = c.get("/settings").json()
        v = settings["version"]
        assert (
            c.post(
                "/settings",
                json={"expected_version": v, "patch": {"dashboard": {"poll_interval_seconds": 3}}},
                headers=auth,
            ).status_code
            == 200
        )
        assert (
            c.post("/settings", json={"expected_version": v, "patch": {}}, headers=auth).status_code
            == 409
        )
        assert (
            c.post(
                "/settings",
                json={"expected_version": v + 1, "patch": {"app": {"host": "0.0.0.0"}}},
                headers=auth,
            ).status_code
            == 422
        )
        job = c.post(
            "/scan", json={"root": settings["settings"]["monitor"]["watch_paths"][0]}, headers=auth
        )
        assert job.status_code == 202
        wait_for(lambda: c.get("/scans/" + job.json()["id"]).json()["status"] == "completed")
        assert (
            c.post(
                "/reports", json={"incident_id": "missing", "format": "json"}, headers=auth
            ).status_code
            == 404
        )
        assert (
            c.post(
                "/reports", json={"incident_id": "missing", "format": "pdf"}, headers=auth
            ).status_code
            == 422
        )
        r = c.app.state.runtime
        incident = r.store.save("incidents", dict(status="closed", root="root", peak_score=95))
        for fmt in ("json", "csv"):
            report = c.post(
                "/reports", json={"incident_id": incident["id"], "format": fmt}, headers=auth
            )
            assert report.status_code == 200
            assert c.get("/reports/" + report.json()["id"] + "/download").status_code == 200
        assert c.get("/incidents/" + incident["id"]).json()["evidence_state"] == "complete"
        r.errors.append("test failure")
        assert c.get("/health").status_code == 503
