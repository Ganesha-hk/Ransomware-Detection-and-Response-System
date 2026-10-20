import csv
import io
import json
import pytest
from app.core.config import Settings
from app.database.session import Store
from app.services.evidence_service import EvidenceService
from app.services.report_service import ReportService
from app.services.settings_service import update
from app.reports.csv_exporter import safe, export
from tests.conftest import wait_for


def test_store_restart_and_filters(tmp_path):
    path = tmp_path / "db.sqlite"
    s = Store(path)
    e = s.save("events", dict(root="root", event_type="created"))
    assert s.get("events", e["id"]) == e
    assert s.get("events", "absent") is None
    assert s.rows("events", root="root", since="2000", until="9999") == [e]
    assert s.filtered("events", event_type="created") == [e]
    assert s.filtered("events", event_type="deleted") == []
    for fn in (
        lambda: s.save("bad", {}),
        lambda: s.get("bad", "id"),
        lambda: s.rows("bad"),
        lambda: s.filtered("bad"),
        lambda: s.filtered("events", bad="x"),
    ):
        with pytest.raises(ValueError):
            fn()
    s.close()
    s = Store(path)
    assert s.get("events", e["id"]) == e
    s.close()


def test_evidence_failures(tmp_path):
    c = Settings()
    c.response.evidence_dir = str(tmp_path / "evidence")
    c.response.max_file_bytes = 20
    s = Store(tmp_path / "db")
    service = EvidenceService(s, c)
    root = tmp_path / "sandbox"
    root.mkdir()
    source = root / "a"
    source.write_bytes(b"hello")
    incident = s.save("incidents", dict(id="incident"))
    event = s.save("events", dict(id="event", root=str(root), source_path=str(source)))
    row = service.capture(incident, event)
    assert row["status"] == "copied"
    c.response.max_files_per_incident = 1
    assert service.capture(incident, event)["error"] == "file_count_quota"
    c.response.max_files_per_incident = 10
    source.write_bytes(b"x" * 21)
    assert service.capture(incident, event)["error"] == "byte_quota"
    source.unlink()
    assert service.capture(incident, event)["status"] == "failed"
    source.symlink_to(tmp_path / "outside")
    assert service.capture(incident, event)["status"] == "failed"
    s.close()


def test_report_csv(tmp_path):
    c = Settings()
    c.reports.output_dir = str(tmp_path)
    s = Store(tmp_path / "db")
    service = ReportService(s, c)
    with pytest.raises(KeyError):
        service.detail("missing")
    with pytest.raises(ValueError):
        service.generate("missing", "pdf")
    incident = s.save("incidents", dict(status="active", root="root", peak_score=95))
    e = s.save("events", dict(source_path="=SUM(A1)", event_type="created"))
    s.save("incident_events", dict(incident_id=incident["id"], event_id=e["id"]))
    report = service.generate(incident["id"], "json")
    content = json.loads((tmp_path / report["path"]).read_text())
    assert content["event_timeline"][0]["source_path"] == "=SUM(A1)"
    parsed = list(csv.DictReader(io.StringIO(export(content).decode())))
    assert any(row["value"] == "'=SUM(A1)" for row in parsed)
    for text in ("=x", "+x", "-x", "@x", "  =x"):
        assert safe(text).startswith("'")
    assert safe("normal") == "normal"
    s.close()


def test_settings(runtime):
    r = runtime
    v = r.version
    updated = update(r, v, dict(detection=dict(entropy_threshold=7.8)))
    assert updated["version"] == v + 1
    with pytest.raises(FileExistsError):
        update(r, v, {})
    for patch in (
        {"monitor": {}},
        {"detection": {"window_seconds": 1}},
        {"detection": {"entropy_threshold": 9}},
    ):
        with pytest.raises(ValueError):
            update(r, r.version, patch)
    assert r.config.detection.entropy_threshold == 7.8


def test_runtime_restart(config_path):
    from app.services.runtime import Runtime

    r = Runtime(config_path)
    r.start()
    update(r, r.version, {"dashboard": {"poll_interval_seconds": 3}})
    r.stop()
    r = Runtime(config_path)
    r.start()
    try:
        assert r.config.dashboard.poll_interval_seconds == 3
        wait_for(lambda: r.store.rows("processes"))
    finally:
        r.stop()
