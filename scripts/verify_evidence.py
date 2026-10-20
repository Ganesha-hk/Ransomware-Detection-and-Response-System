import argparse
import hashlib
import json
from pathlib import Path


def verify(report_path, evidence_root):
    report = json.loads(Path(report_path).read_text())
    rows = report["evidence_manifest"]
    for row in rows:
        if row["status"] == "copied":
            path = Path(evidence_root) / row["stored_path"]
            if hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
                raise ValueError("Evidence hash mismatch: " + row["stored_path"])
    return sum(r["status"] == "copied" for r in rows)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("report")
    p.add_argument("--evidence-root", default="data/quarantine")
    a = p.parse_args()
    print("Verified copies:", verify(a.report, a.evidence_root))
