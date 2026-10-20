from datetime import datetime
from app.core.models import uid, utc
from app.core.logging import log


class Incidents:
    def __init__(self, runtime):
        self.r = runtime
        self.active = {}
        self.last_level = {}
        self.linked = {}
        for incident in self.r.store.rows("incidents", limit=100000):
            if incident["status"] == "active":
                incident["interrupted"] = True
                self.active[incident["root"]] = incident
                self.r.store.save("incidents", incident)
                self.linked[incident["id"]] = {
                    row["event_id"]
                    for row in self.r.store.rows(
                        "incident_events", limit=100000, incident_id=incident["id"]
                    )
                }

    def update(self, root, result, events):
        r = self.r
        current = self.active.get(root)
        if result["severity"] == "Critical":
            if not current:
                current = dict(
                    id=uid(),
                    root=root,
                    status="active",
                    opened_at=utc(),
                    closed_at=None,
                    peak_score=0,
                    settings_snapshot=r.config.model_dump(),
                    settings_version=r.version,
                    attribution="unknown",
                    process_context=r.process_context.copy(),
                    interrupted=False,
                )
                self.active[root] = current
                if r.config.response.simulate_termination:
                    r.store.save(
                        "audit_records",
                        dict(
                            action="would_terminate",
                            executed=False,
                            target=None,
                            reason="No writer established",
                        ),
                    )
                    log("audit", "would_terminate executed=false target=unknown")
            current["last_critical_at"] = utc()
            current["last_seen_at"] = utc()
            if result["score"] >= current["peak_score"]:
                current["peak_score"] = result["score"]
                current["peak_signals"] = result
            r.store.save("incidents", current)
        if current:
            for event in events:
                link_id = current["id"] + ":" + event["id"]
                linked = self.linked.setdefault(current["id"], set())
                if event["id"] not in linked:
                    r.store.save(
                        "incident_events",
                        dict(id=link_id, incident_id=current["id"], event_id=event["id"]),
                    )
                linked.add(event["id"])
                key = (
                    current["id"],
                    event.get("identity") or event.get("destination_path") or event["source_path"],
                )
                if event.get("sampling_status") == "ok" and key not in r.evidence_queued:
                    r.schedule_evidence(current, event, key)
            elapsed = (
                datetime.fromisoformat(utc()) - datetime.fromisoformat(current["last_critical_at"])
            ).total_seconds()
            if (
                result["severity"] != "Critical"
                and elapsed >= r.config.detection.incident_cooldown_seconds
            ):
                current.update(status="closed", closed_at=utc())
                r.store.save("incidents", current)
                del self.active[root]
                r.schedule_final_reports(current["id"])
        previous = self.last_level.get(root, "Normal")
        if result["severity"] != previous and result["severity"] != "Normal":
            r.store.save(
                "alerts",
                dict(
                    root=root,
                    score_id=result["id"],
                    score=result["score"],
                    severity=result["severity"],
                    previous_severity=previous,
                    incident_id=current["id"] if current else None,
                ),
            )
            log("alerts", f"{root}: {result['severity']} score={result['score']}")
        self.last_level[root] = result["severity"]
