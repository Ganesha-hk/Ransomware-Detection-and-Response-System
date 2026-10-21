"""Bounded web demo: only create and change files in a fresh owned directory."""

import os
import time
import sys
from pathlib import Path
from uuid import uuid4


DEPARTMENTS = {"finance", "hr", "customer-data", "legal", "backups"}


def simulate(config, register=None):
    roots = list(
        dict.fromkeys(
            Path(p)
            for p in config.monitor.watch_paths
            if Path(p).name == "sandbox"
            or (Path(p).parent.name == "sensitive-lab" and Path(p).name in DEPARTMENTS)
        )
    )
    if not roots:
        raise ValueError("No monitored demo folders are configured")
    # Validate every root before creating files. Never use arbitrary production roots.
    for root in roots:
        if any(p.is_symlink() for p in [root, *root.parents]):
            raise ValueError("Demo folders must not use symlinks")
        if len(list(root.glob("web-demo-*"))) >= 20:
            raise ValueError("Demo storage limit reached; restart the disposable hosted service")
        if not root.is_dir() or not os.access(root, os.W_OK):
            raise ValueError(f"Demo folder is not writable: {root}")
    runs, paths = [], []
    for root in roots:
        run = root / ("web-demo-" + uuid4().hex)
        run.mkdir()
        if register:
            register(
                str(run),
                {
                    "pid": os.getpid(),
                    "name": Path(sys.executable).name,
                    "executable": sys.executable,
                    "label": "Known simulator process (self-reported, not detector attribution)",
                    "scope": str(run),
                },
            )
        (run / "fictional-record.csv").write_text(
            f"notice,department,reference,amount\nFICTIONAL DEMO,{root.name},EXAMPLE-001,1250\n"
        )
        for i in range(50):
            p = run / f"{root.name}-sample-{i:03}.txt"
            with p.open("x") as f:
                f.write(f"Fictional RDRS {root.name} demonstration data\n" * 30)
            paths.append(p)
        runs.append({"root": str(root), "directory": str(run), "files": 51})
    time.sleep(2)
    for p in paths:
        with p.open("wb") as f:
            f.write(os.urandom(20000))
    time.sleep(1)
    for p in paths:
        p.rename(p.with_suffix(".locked"))
    return {
        "runs": runs,
        "files": 51 * len(runs),
        "message": f"Simulation finished across {len(runs)} monitored demo folders. Open Incidents to see detection for each folder.",
    }
