from collections import deque
import fcntl
import queue
import threading
import time
from pathlib import Path
from loguru import logger
from app.core.config import load
from app.core.logging import configure, log
from app.core.models import utc
from app.database.session import Store
from app.detectors.event_normalizer import normalize
from app.detectors.file_monitor import observer
from app.detectors.process_monitor import ProcessSampler
from app.detectors.sliding_window import Window
from app.services.event_pipeline import process
from app.services.incident_service import Incidents
from app.services.evidence_service import EvidenceService
from app.services.report_service import ReportService
from app.services.scan_service import scan


class Runtime:
    def __init__(self, path, watch=None):
        self.config = load(path)
        if watch:
            # Validate convenience override through the same path policy.
            from app.core.config import validate_paths

            self.config.monitor.watch_paths = [str(Path(watch).resolve())]
            validate_paths(self.config)
        self.lock = threading.RLock()
        self.stopping = threading.Event()
        self.response_stop = threading.Event()
        self.queue = queue.Queue(self.config.monitor.queue_capacity)
        self.responses = queue.Queue(self.config.monitor.queue_capacity)
        self.windows = {p: Window() for p in self.config.monitor.watch_paths}
        self.move_aliases = {}
        self.move_times = {}
        self.debounce = {}
        self.pending_modifies = {}
        self.dropped = 0
        self.suppressed = 0
        self.errors = []
        self.last_processed = None
        self.process_context = []
        self.cpu_samples = deque(maxlen=3600)
        self.cpu_lock = threading.Lock()
        self.live = {}
        self.demo_processes = {}
        self.evidence_queued = set()
        self.evidence_pending = {}
        self.pending_lock = threading.Lock()
        self.started = time.monotonic()
        self.threads = []
        self.scan_thread = None
        self.running = False

    def start(self):
        c = self.config
        for p in [
            *c.monitor.watch_paths,
            c.response.evidence_dir,
            c.reports.output_dir,
            c.logging.directory,
            str(Path(c.database.path).parent),
        ]:
            Path(p).mkdir(parents=True, exist_ok=True)
        self.instance_lock = open(c.database.path + ".lock", "a")
        try:
            fcntl.flock(self.instance_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.instance_lock.close()
            raise RuntimeError("Another runtime owns this database; use one worker")
        c.monitor.exclude_paths.append(c.database.path + ".lock")
        self.log_ids = configure(c.logging)
        self.store = Store(c.database.path, c.database.busy_timeout_ms)
        versions = self.store.rows("settings_versions", limit=100000)
        self.version = max([x["version"] for x in versions], default=0) + 1
        if versions:
            previous = max(versions, key=lambda x: x["version"])["settings"]
            # Only persisted hot settings override configuration on restart.
            from app.services.settings_service import ALLOWED
            from app.core.config import Settings

            data = c.model_dump()
            for key in ALLOWED:
                data["detection"][key] = previous["detection"][key]
            data["dashboard"] = previous["dashboard"]
            self.config = c = Settings.model_validate(data)
        self.store.save(
            "settings_versions",
            dict(
                id=str(self.version),
                version=self.version,
                settings=c.model_dump(),
                change_summary="Runtime start",
            ),
        )
        self.store.save(
            "audit_records", dict(action="runtime_started", live_window="empty_after_restart")
        )
        for job in self.store.rows("scan_jobs", limit=100000):
            if job["status"] == "running":
                job.update(status="interrupted", finished_at=utc())
                self.store.save("scan_jobs", job)
        self.incidents = Incidents(self)
        for row in self.store.rows("evidence_files", limit=100000):
            self.evidence_queued.add(
                (row["incident_id"], row.get("source_identity") or row["source_path"])
            )
        self.evidence = EvidenceService(self.store, c)
        self.reports = ReportService(self.store, c)
        self.observer = observer(self)
        self.sampler = ProcessSampler()
        self.running = True
        for name, fn in [
            ("events", self.event_loop),
            ("timer", self.timer_loop),
            ("processes", self.process_loop),
            ("response", self.response_loop),
        ]:
            thread = threading.Thread(
                name="rdrs-" + name, target=self.guarded, args=(name, fn), daemon=True
            )
            self.threads.append(thread)
            thread.start()
        self.observer.start()
        log("system", "Runtime started in simulation mode")

    def guarded(self, name, fn):
        try:
            fn()
        except Exception as exc:
            self.errors.append(name + ": " + type(exc).__name__)
            log("errors", name + ": " + str(exc))

    def enqueue(self, root, kind, source, destination=None, synthetic=False):
        if self.stopping.is_set():
            return
        # Callback does only lexical checks and bounded in-memory bookkeeping.
        path = destination or source
        p = Path(path)
        if not p.is_relative_to(Path(root)) or any(
            p == Path(x) or p.is_relative_to(Path(x)) for x in self.config.monitor.exclude_paths
        ):
            return
        now = time.monotonic()
        if destination:
            self.move_aliases[source] = destination
            self.move_times[source] = now
        if kind == "modified":
            if (
                now - self.debounce.get(source, -float("inf"))
                < self.config.monitor.debounce_ms / 1000
            ):
                self.suppressed += 1
                if (
                    len(self.pending_modifies) < self.config.monitor.queue_capacity
                    or source in self.pending_modifies
                ):
                    self.pending_modifies[source] = normalize(
                        root, kind, source, destination, now, synthetic
                    )
                else:
                    self.dropped += 1
                return
            self.debounce[source] = now
        try:
            self.queue.put_nowait(normalize(root, kind, source, destination, now, synthetic))
        except queue.Full:
            self.dropped += 1

    def event_loop(self):
        while not self.stopping.is_set() or not self.queue.empty():
            try:
                event = self.queue.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                with self.lock:
                    process(self, event)
            finally:
                self.queue.task_done()

    def evaluate(self, root):
        result = self.windows[root].result(self.config.detection)
        result.update(
            root=root, settings_version=self.version, weights=self.config.detection.weights
        )
        cpu = [p["cpu_percent"] for p in self.process_context if p.get("cpu_percent") is not None]
        result["cpu_percent"] = sum(cpu) if cpu else None
        result = self.store.save("scores", result)
        self.live[root] = result
        events = [e for _, _, e in self.windows[root].events]
        self.incidents.update(root, result, events)

    def timer_loop(self):
        while not self.stopping.wait(self.config.detection.tick_seconds):
            with self.lock:
                pending = list(self.pending_modifies.values())
                self.pending_modifies.clear()
                for event in pending:
                    process(self, event)
                for root in self.windows:
                    self.evaluate(root)
                cutoff = time.monotonic() - self.config.detection.window_seconds
                self.debounce = {p: t for p, t in self.debounce.items() if t > cutoff}
                for p, t in list(self.move_times.items()):
                    if t <= cutoff:
                        self.move_times.pop(p, None)
                        self.move_aliases.pop(p, None)

    def process_loop(self):
        while not self.stopping.is_set():
            rows = self.sampler.sample(time.monotonic())
            measured = [row["cpu_percent"] for row in rows if row.get("cpu_percent") is not None]
            with self.cpu_lock:
                self.cpu_samples.append(
                    {
                        "timestamp": utc(),
                        "cpu_percent": sum(measured) if measured else None,
                    }
                )
            for row in rows:
                self.store.save("processes", row)
            with self.lock:
                self.process_context = rows
            self.stopping.wait(self.config.processes.sample_interval_seconds)

    def schedule_evidence(self, incident, event, key):
        try:
            with self.pending_lock:
                self.evidence_pending[incident["id"]] = (
                    self.evidence_pending.get(incident["id"], 0) + 1
                )
            self.responses.put_nowait(("evidence", incident.copy(), event.copy()))
            self.evidence_queued.add(key)
        except queue.Full:
            with self.pending_lock:
                self.evidence_pending[incident["id"]] -= 1
            self.dropped += 1

    def evidence_count(self, id):
        with self.pending_lock:
            return self.evidence_pending.get(id, 0)

    def schedule_final_reports(self, id):
        try:
            self.responses.put_nowait(("reports", id, None))
        except queue.Full:
            self.dropped += 1

    def response_loop(self):
        while not self.response_stop.is_set() or not self.responses.empty():
            try:
                kind, item, event = self.responses.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                if kind == "evidence":
                    original = event.get("destination_path") or event["source_path"]
                    resolved = original
                    for _ in range(8):
                        nxt = self.move_aliases.get(resolved, resolved)
                        if nxt == resolved:
                            break
                        resolved = nxt
                    if resolved != original:
                        event["destination_path"] = resolved
                    self.evidence.capture(item, event)
                else:
                    pass  # Reports are generated only on explicit user selection.
            finally:
                if kind == "evidence":
                    with self.pending_lock:
                        self.evidence_pending[item["id"]] -= 1
                self.responses.task_done()

    def start_scan(self, root):
        with self.lock:
            if root not in self.config.monitor.watch_paths:
                raise ValueError("Root must be a configured watched root")
            if self.scan_thread and self.scan_thread.is_alive():
                raise FileExistsError("A scan is already running")
            job = self.store.save(
                "scan_jobs", dict(root=root, status="running", count=0, bytes=0, failures=0)
            )
            self.scan_thread = threading.Thread(target=scan, args=(self, job), daemon=True)
            self.scan_thread.start()
            return job

    def status(self):
        with self.lock:
            workers = {t.name: t.is_alive() for t in self.threads}
            ready = (
                self.running
                and self.observer.is_alive()
                and all(workers.values())
                and not self.errors
                and not self.dropped
            )
            live = list(self.live.values())
            maximum = (
                max(live, key=lambda x: x["score"]) if live else dict(score=0, severity="Normal")
            )
            return dict(
                score=maximum["score"],
                severity=maximum["severity"],
                roots=live,
                simulation_mode=True,
                watch_paths=self.config.monitor.watch_paths,
                window_seconds=self.config.detection.window_seconds,
                cooldown_seconds=self.config.detection.incident_cooldown_seconds,
                monitor_state="running"
                if ready and not self.dropped
                else "degraded"
                if self.running
                else "stopped",
                ready=ready,
                workers=workers,
                queue_depth=self.queue.qsize(),
                response_queue_depth=self.responses.qsize(),
                dropped_events=self.dropped,
                suppressed_duplicates=self.suppressed,
                last_processed=self.last_processed,
                uptime_seconds=time.monotonic() - self.started,
                active_incidents=list(self.incidents.active.values()),
                process_visibility="container"
                if Path("/.dockerenv").exists()
                else "host-visible; writer unknown",
                errors=self.errors,
                database_bytes=Path(self.config.database.path).stat().st_size,
                poll_interval_seconds=self.config.dashboard.poll_interval_seconds,
            )

    def stop(self):
        self.observer.stop()
        self.observer.join(timeout=5)
        with self.lock:
            for event in list(self.pending_modifies.values()):
                process(self, event)
            self.pending_modifies.clear()
        self.stopping.set()
        for thread in self.threads[:3]:
            thread.join(timeout=5)
        if self.scan_thread:
            self.scan_thread.join(timeout=5)
        self.response_stop.set()
        self.threads[3].join(timeout=10)
        alive = [t.name for t in self.threads if t.is_alive()]
        self.store.save(
            "audit_records",
            dict(
                action="runtime_stopped",
                unfinished_workers=alive,
                pending_events=self.queue.qsize(),
                pending_responses=self.responses.qsize(),
            ),
        )
        self.running = False
        if not alive:
            self.store.close()
            fcntl.flock(self.instance_lock, fcntl.LOCK_UN)
            self.instance_lock.close()
        for id in self.log_ids:
            logger.remove(id)
