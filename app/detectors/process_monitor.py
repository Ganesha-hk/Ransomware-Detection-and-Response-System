import psutil
from app.core.models import utc


class ProcessSampler:
    def __init__(self):
        self.previous = {}
        self.handles = {}

    def sample(self, now):
        rows = []
        alive = set()
        for proc in psutil.process_iter():
            try:
                key = (proc.pid, proc.create_time())
                alive.add(key)
                p = self.handles.setdefault(key, proc)
                data = dict(
                    pid=p.pid,
                    creation_time=key[1],
                    timestamp=utc(),
                    attribution_method="temporal_context_only",
                    confidence="unknown",
                    writer=False,
                )
                for field, call in [
                    ("parent_pid", p.ppid),
                    ("name", p.name),
                    ("executable", p.exe),
                    ("memory_bytes", lambda: p.memory_info().rss),
                    ("write_bytes", lambda: p.io_counters().write_bytes),
                ]:
                    try:
                        data[field] = call()
                    except (psutil.Error, OSError):
                        data[field] = None
                cpu = p.cpu_percent()
                previous = self.previous.get(key)
                data["cpu_percent"] = cpu if previous else None
                data["write_bytes_per_second"] = None
                if (
                    previous
                    and data["write_bytes"] is not None
                    and previous[1] is not None
                    and now > previous[0]
                ):
                    data["write_bytes_per_second"] = max(0, data["write_bytes"] - previous[1]) / (
                        now - previous[0]
                    )
                self.previous[key] = (now, data["write_bytes"])
                rows.append(data)
            except (psutil.Error, OSError):
                continue
        self.handles = {k: v for k, v in self.handles.items() if k in alive}
        self.previous = {k: v for k, v in self.previous.items() if k in alive}
        return rows
