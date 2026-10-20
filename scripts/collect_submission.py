"""Create clearly marked sanitized report derivatives for a local submission folder."""

import argparse
import hashlib
import json
import platform
import sys
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.reports.csv_exporter import export  # noqa: E402


def collect(source, name):
    source = Path(source)
    raw = source.read_bytes()
    report = json.loads(raw)
    report["process_context"] = []
    report["incident"]["process_context"] = []
    report["redaction"] = {
        "notice": "Sanitized derivative of an actual generated report; not original download bytes.",
        "omitted": ["raw process context"],
        "path_prefix": "<project>",
        "original_sha256": hashlib.sha256(raw).hexdigest(),
    }

    def redact(value):
        if isinstance(value, str):
            return value.replace(str(ROOT), "<project>")
        if isinstance(value, list):
            return [redact(v) for v in value]
        if isinstance(value, dict):
            return {k: redact(v) for k, v in value.items()}
        return value

    report = redact(report)
    destination = ROOT / "evidence" / "reports"
    destination.mkdir(parents=True, exist_ok=True)
    if not name.replace("-", "").replace("_", "").isalnum():
        raise ValueError("Use a simple artifact name")
    (destination / (name + ".json")).write_text(json.dumps(report, indent=2))
    (destination / (name + ".csv")).write_bytes(export(report))
    return destination / (name + ".json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("report", help="An actual generated JSON report")
    parser.add_argument("--name", default="sanitized-report")
    args = parser.parse_args()
    print(collect(args.report, args.name))
    metadata = dict(
        python=platform.python_version(),
        platform=platform.platform(),
        packages={
            p: version(p) for p in ["fastapi", "sqlalchemy", "watchdog", "psutil", "pydantic"]
        },
    )
    (ROOT / "evidence" / "test-results" / "environment.json").write_text(
        json.dumps(metadata, indent=2)
    )
