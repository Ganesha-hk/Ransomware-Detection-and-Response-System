from collections import deque
import time
from app.detectors.rules import evaluate


class Window:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.events = deque()
        self.aliases = {}

    def add(self, e):
        key = e.get("identity") or self.aliases.get(e["source_path"]) or e["source_path"]
        old_key = self.aliases.get(e["source_path"])
        if old_key and old_key != key:
            self.events = deque((t, key if k == old_key else k, row) for t, k, row in self.events)
            self.aliases = {p: key if k == old_key else k for p, k in self.aliases.items()}
        self.aliases[e["source_path"]] = key
        if e.get("destination_path"):
            self.aliases[e["destination_path"]] = key
        self.events.append((e["arrival"], key, e))

    def result(self, c):
        cutoff = self.clock() - c.window_seconds
        self.events = deque(row for row in self.events if row[0] > cutoff)
        keys = {k for _, k, _ in self.events}
        self.aliases = {p: k for p, k in self.aliases.items() if k in keys}
        files = {}
        for _, key, e in self.events:
            f = files.setdefault(
                key, dict(changed=False, moved=False, suffix_changed=False, entropy=None)
            )
            f["changed"] |= e["event_type"] in ("created", "modified")
            f["moved"] |= e["event_type"] == "moved"
            f["suffix_changed"] |= e["event_type"] == "moved" and e["old_suffix"] != e["new_suffix"]
            if e.get("entropy") is not None:
                f["entropy"] = e["entropy"]
        return evaluate(files, c)
