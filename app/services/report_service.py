import hashlib
import os
from pathlib import Path
from app.core.models import uid, utc
from app.reports import json_exporter, csv_exporter, html_exporter
from app.reports.recommendations import RECOMMENDATIONS


class ReportService:
    def __init__(self, store, config):
        self.store, self.config = store, config

    def detail(self, id, start=None, end=None):
        incident = self.store.get("incidents", id)
        if not incident:
            raise KeyError(id)
        links = self.store.rows("incident_events", limit=100000, incident_id=id)
        events = [self.store.get("events", link["event_id"]) for link in links]
        manifest = self.store.rows("evidence_files", limit=100000, incident_id=id)
        if start is not None:
            from datetime import datetime
            events = [e for e in events if e and start <= datetime.fromisoformat(e['timestamp']) < end]
            event_ids = {e['id'] for e in events}
            manifest = [e for e in manifest if e.get('event_id') in event_ids]
        path_identities = {}
        for event in events:
            if event and event.get("identity"):
                for path in (event["source_path"], event.get("destination_path")):
                    if path:
                        path_identities.setdefault(path, set()).add(event["identity"])
        logical = {}
        for event in sorted((e for e in events if e), key=lambda e: e["timestamp"]):
            path = event.get("destination_path") or event["source_path"]
            candidates = path_identities.get(path, set())
            inferred = next(iter(candidates)) if len(candidates) == 1 else None
            key = event.get("identity") or inferred or path
            item = logical.setdefault(
                key,
                dict(
                    path=event["source_path"],
                    first_seen=event["timestamp"],
                    last_seen=event["timestamp"],
                    event_count=0,
                    entropy=None,
                    previous_paths=[],
                ),
            )
            path = event.get("destination_path") or event["source_path"]
            if item["path"] != path:
                item["previous_paths"].append(item["path"])
            item.update(
                path=path, last_seen=event["timestamp"], event_count=item["event_count"] + 1
            )
            if event.get("entropy") is not None:
                item["entropy"] = event["entropy"]
        return dict(
            requested_period={"start": start.isoformat(), "end_exclusive": end.isoformat()} if start else None,
            logical_files=list(logical.values()),
            schema_version=1,
            generated_at=utc(),
            snapshot=incident["status"] != "closed",
            incident=incident,
            event_timeline=[e for e in events if e],
            affected_files=sorted(
                {e.get("destination_path") or e["source_path"] for e in events if e}
            ),
            process_context=incident.get("process_context", []),
            attribution="Unknown: portable filesystem events do not identify the writer.",
            evidence_manifest=manifest,
            copy_failures=[e for e in manifest if e["status"] != "copied"],
            recommendations=RECOMMENDATIONS,
        )

    def generate(self, id, format, start=None, end=None):
        if format not in ("json", "csv", "html"):
            raise ValueError("Unsupported report format")
        report = self.detail(id, start, end)
        data = {"json": json_exporter, "csv": csv_exporter, "html": html_exporter}[format].export(report)
        name = uid() + "." + format
        path = Path(self.config.reports.output_dir) / name
        tmp = path.with_suffix(path.suffix + ".part")
        with tmp.open("xb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        tmp.replace(path)
        return self.store.save(
            "reports",
            dict(
                requested_period=report["requested_period"],
                incident_id=id,
                format=format,
                path=name,
                sha256=hashlib.sha256(data).hexdigest(),
                bytes=len(data),
                report_version=1,
                snapshot=report["snapshot"],
            ),
        )
