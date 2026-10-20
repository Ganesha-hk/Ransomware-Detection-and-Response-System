from collections import Counter
import math
import os
from app.core.paths import safe_open


def entropy(data):
    if not data:
        return 0.0
    return -sum((n / len(data)) * math.log2(n / len(data)) for n in Counter(data).values())


def sample(path, root, settings):
    try:
        with safe_open(path, root, settings.monitor.exclude_paths) as f:
            before = os.fstat(f.fileno())
            data = f.read(settings.monitor.sample_bytes)
            after = os.fstat(f.fileno())
        stable = (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
        return dict(
            entropy=entropy(data) if stable else None,
            sampling_status="ok" if stable else "unstable",
            sampled_bytes=len(data),
            size=after.st_size,
            identity=f"{after.st_dev}:{after.st_ino}",
        )
    except (OSError, ValueError) as e:
        return dict(
            entropy=None,
            sampling_status=type(e).__name__,
            sampled_bytes=0,
            size=None,
            identity=None,
        )
