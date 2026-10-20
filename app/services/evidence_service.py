import hashlib
import os
from pathlib import Path
from app.core.paths import safe_open
from app.core.models import uid, utc


class EvidenceService:
    def __init__(self, store, config):
        self.store, self.config = store, config

    def capture(self, incident, event):
        c = self.config.response
        original = event.get("destination_path") or event["source_path"]
        row = dict(
            incident_id=incident["id"],
            event_id=event["id"],
            root=event["root"],
            source_path=original,
            source_identity=event.get("identity"),
            stored_path=None,
            bytes=0,
            sha256=None,
            status="failed",
            error=None,
            timestamp=utc(),
        )
        previous = self.store.rows("evidence_files", limit=100000, incident_id=incident["id"])
        good = [r for r in previous if r["status"] == "copied"]
        temp = None
        try:
            if len(good) >= c.max_files_per_incident:
                raise ValueError("file_count_quota")
            with safe_open(original, event["root"], self.config.monitor.exclude_paths) as source:
                before = os.fstat(source.fileno())
                row["source_before"] = dict(
                    size=before.st_size,
                    mtime_ns=before.st_mtime_ns,
                    device=before.st_dev,
                    inode=before.st_ino,
                )
                if (
                    event.get("identity")
                    and event["identity"] != f"{before.st_dev}:{before.st_ino}"
                ):
                    raise ValueError("source_identity_changed")
                remaining = c.max_incident_bytes - sum(r["bytes"] for r in good)
                cap = min(c.max_file_bytes, remaining)
                if before.st_size > cap:
                    raise ValueError("byte_quota")
                directory = Path(c.evidence_dir) / incident["id"]
                directory.mkdir(parents=True, exist_ok=True)
                name = uid() + ".bin"
                temp = directory / (name + ".part")
                digest = hashlib.sha256()
                count = 0
                with temp.open("xb") as target:
                    while chunk := source.read(min(65536, max(1, cap - count + 1))):
                        count += len(chunk)
                        if count > cap:
                            raise ValueError("byte_quota_during_copy")
                        digest.update(chunk)
                        target.write(chunk)
                    target.flush()
                    os.fsync(target.fileno())
                after = os.fstat(source.fileno())
                row["source_after"] = dict(
                    size=after.st_size,
                    mtime_ns=after.st_mtime_ns,
                    device=after.st_dev,
                    inode=after.st_ino,
                )
                if row["source_before"] != row["source_after"]:
                    raise ValueError("unstable")
                temp.replace(directory / name)
                row.update(
                    status="copied",
                    bytes=count,
                    sha256=digest.hexdigest(),
                    stored_path=str(Path(incident["id"]) / name),
                )
        except (OSError, ValueError) as exc:
            row.update(error=str(exc), status="unstable" if str(exc) == "unstable" else "failed")
        finally:
            if temp and temp.exists():
                temp.unlink()
        return self.store.save("evidence_files", row)
