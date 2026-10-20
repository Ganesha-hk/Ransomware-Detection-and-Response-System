import os
import time
from app.core.entropy import sample
from app.core.models import utc
from app.core.paths import approved
from app.detectors.event_normalizer import normalize


def scan(runtime, job):
    root = job["root"]
    started = time.monotonic()
    try:
        for directory, dirs, files in os.walk(root, followlinks=False):
            dirs[:] = [
                d
                for d in dirs
                if approved(os.path.join(directory, d), root, runtime.config.monitor.exclude_paths)
            ]
            for name in files:
                if runtime.stopping.is_set():
                    job["status"] = "interrupted"
                    return
                if (
                    job["count"] >= 10000
                    or job["bytes"] >= 104857600
                    or time.monotonic() - started >= 30
                ):
                    job["status"] = "limit_reached"
                    return
                path = os.path.join(directory, name)
                if not approved(path, root, runtime.config.monitor.exclude_paths):
                    continue
                event = normalize(root, "inventory", path, None, time.monotonic())
                event.update(
                    sample(path, root, runtime.config), source_kind="scan", sample_time=utc()
                )
                runtime.store.save("events", event)
                job["count"] += 1
                job["bytes"] += event["sampled_bytes"]
                job["failures"] += event["sampling_status"] != "ok"
                if job["count"] % 50 == 0:
                    runtime.store.save("scan_jobs", job)
        job["status"] = "completed"
    except Exception as exc:
        job.update(status="failed", error=str(exc))
    finally:
        job["finished_at"] = utc()
        runtime.store.save("scan_jobs", job)
