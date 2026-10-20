import csv
import io
import json


def safe(value):
    text = str(value)
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r", "\n")) else text


def export(report):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(["record_type", "incident_id", "record_id", "field", "value"])
    groups = {
        "summary": [
            {
                k: v
                for k, v in report.items()
                if k
                not in ("event_timeline", "evidence_manifest", "process_context", "recommendations")
            }
        ],
        "event": report["event_timeline"],
        "evidence": report["evidence_manifest"],
        "process_context": report["process_context"],
        "recommendation": [{"text": r} for r in report["recommendations"]],
    }
    for kind, rows in groups.items():
        for row in rows:
            for field, value in row.items():
                if isinstance(value, (list, dict)):
                    value = json.dumps(value, ensure_ascii=False)
                writer.writerow(
                    [
                        kind,
                        report["incident"]["id"],
                        row.get("id", ""),
                        field,
                        safe(value) if value is not None else "",
                    ]
                )
    return stream.getvalue().encode()
