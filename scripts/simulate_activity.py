"""Creates only its own files in a fresh sandbox run; never encrypts existing files."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import time
from uuid import uuid4

BASE = Path(__file__).resolve().parents[1] / "data" / "sandbox"


DEPARTMENTS = ("finance", "hr", "customer-data", "legal", "backups")


def simulate(profile="burst", pause=1, department=None):
    if profile not in ("benign", "isolated", "archive", "burst"):
        raise ValueError("Unknown profile")
    if department is not None and department not in DEPARTMENTS:
        raise ValueError("Unknown department")
    base = BASE if department is None else BASE.parent / "sensitive-lab" / department
    if any(p.is_symlink() for p in [base, *base.parents]):
        raise ValueError("Sandbox must not use symlinks")
    base.mkdir(parents=True, exist_ok=True)
    run = base / (("locked-files-test-" if profile == "burst" else "run-") + uuid4().hex)
    run.mkdir(exist_ok=False)
    count = 3 if profile == "benign" else 1 if profile == "isolated" else 50
    files = []
    for i in range(count):
        path = run / f"example-{i:03}.txt"
        with path.open("xb") as f:
            f.write(b"RDRS synthetic baseline\n" * 20)
        files.append(path)
    time.sleep(pause)
    for path in files:
        if path.is_symlink() or not path.resolve().is_relative_to(run):
            raise ValueError("Run boundary changed")
        fd = os.open(path, os.O_WRONLY | os.O_NOFOLLOW | os.O_TRUNC)
        with os.fdopen(fd, "wb") as f:
            f.write(b"ordinary edit\n" * 20 if profile == "benign" else os.urandom(20000))
    time.sleep(0.15)
    if profile == "burst":
        renamed = []
        for path in files:
            target = path.with_suffix(".locked")
            path.rename(target)
            renamed.append(target)
        files = renamed
    manifest = dict(
        profile=profile,
        run=str(run),
        files=[dict(path=str(p), sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files],
    )
    # Manifest lives outside watched sandbox to avoid polluting detection.
    output = Path(__file__).resolve().parents[1] / "data" / "demo-manifests"
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / (run.name + ".json")
    manifest_path.write_text(json.dumps(manifest, indent=2))
    return manifest_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--profile", choices=["benign", "isolated", "archive", "burst"], default="burst"
    )
    parser.add_argument("--department", choices=DEPARTMENTS)
    args = parser.parse_args()
    print(simulate(args.profile, department=args.department))
