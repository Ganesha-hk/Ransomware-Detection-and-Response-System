import time
from app.core.models import utc
from app.core.entropy import sample
from app.core.paths import approved
from app.core.logging import log


def process(runtime, event):
    path = event.get("destination_path") or event["source_path"]
    root = event["root"]
    if not approved(path, root, runtime.config.monitor.exclude_paths):
        return
    if event["event_type"] == "deleted":
        event.update(
            entropy=None, sampling_status="deleted", sampled_bytes=0, size=None, identity=None
        )
    else:
        for attempt in range(runtime.config.monitor.sample_retries + 1):
            path = runtime.move_aliases.get(path, path)
            result = sample(path, root, runtime.config)
            if result["sampling_status"] == "ok":
                break
            if attempt < runtime.config.monitor.sample_retries:
                time.sleep(0.01)
        event.update(result)
    event["sample_time"] = utc()
    runtime.store.save("events", event)
    runtime.windows[root].add(event)
    runtime.last_processed = utc()
    log("events", f"{event['event_type']} {path} sample={event['sampling_status']}")
    runtime.evaluate(root)
