"""Bounded web demo: only create and change files in a fresh owned directory."""

import os
import time
from pathlib import Path
from uuid import uuid4


def simulate(config):
    root = next((Path(p) for p in config.monitor.watch_paths if Path(p).name == "sandbox"), None)
    if root is None or any(p.is_symlink() for p in [root, *root.parents]):
        raise ValueError("A monitored, non-symlink sandbox is required")
    if len(list(root.glob("web-demo-*"))) >= 20:
        raise ValueError("Demo storage limit reached; restart the disposable hosted service")
    run = root / ("web-demo-" + uuid4().hex)
    run.mkdir()
    (run / "fictional-invoice.csv").write_text("customer,amount\nExample Company,1250\n")
    paths = []
    for i in range(50):
        p = run / f"sample-{i:03}.txt"
        p.write_text("Fictional RDRS demonstration data\n" * 30)
        paths.append(p)
    time.sleep(2)
    for p in paths:
        with p.open("wb") as f:
            f.write(os.urandom(20000))
    time.sleep(1)
    for p in paths:
        p.rename(p.with_suffix(".locked"))
    return {
        "directory": str(run),
        "files": 51,
        "message": "Simulation finished. Open Overview and Incidents to see detection.",
    }
