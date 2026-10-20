from pathlib import Path
import math
import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class App(Strict):
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    simulation_mode: bool = True


class Monitor(Strict):
    watch_paths: list[str] = ["./data/sandbox"]
    recursive: bool = True
    observer: str = "native"
    queue_capacity: int = Field(default=10000, ge=1, le=100000)
    debounce_ms: int = Field(default=100, ge=0, le=10000)
    sample_bytes: int = Field(default=65536, ge=256, le=1048576)
    sample_retries: int = Field(default=2, ge=0, le=5)
    exclude_paths: list[str] = ["./logs", "./evidence"]


class Database(Strict):
    path: str = "./data/rdrs.db"
    busy_timeout_ms: int = Field(default=5000, ge=1, le=30000)


class Detection(Strict):
    window_seconds: float = Field(default=60, gt=0, le=3600)
    tick_seconds: float = Field(default=1, gt=0, le=60)
    rapid_write_min_files: int = Field(default=20, ge=1)
    mass_rename_min_files: int = Field(default=20, ge=1)
    extension_change_min_files: int = Field(default=10, ge=1)
    high_entropy_min_files: int = Field(default=5, ge=1)
    entropy_threshold: float = Field(default=7.5, ge=0, le=8)
    cpu_threshold_percent: float = Field(default=80, ge=0, le=10000)
    cpu_signal_enabled: bool = False
    unknown_program_signal_enabled: bool = False
    weights: dict[str, float] = dict(
        rapid_high_entropy_writes=40,
        mass_rename=30,
        high_entropy=25,
        cpu_spike=15,
        unknown_program=10,
    )
    warning_min: float = Field(default=40, gt=0)
    critical_min: float = Field(default=70, le=100)
    incident_cooldown_seconds: float = Field(default=60, gt=0)

    @model_validator(mode="after")
    def valid(self):
        if not self.warning_min < self.critical_min:
            raise ValueError("Severity thresholds must be ordered")
        if set(self.weights) != {
            "rapid_high_entropy_writes",
            "mass_rename",
            "high_entropy",
            "cpu_spike",
            "unknown_program",
        }:
            raise ValueError("Supply exactly the five signal weights")
        if any(not math.isfinite(v) or v < 0 for v in self.weights.values()):
            raise ValueError("Weights must be finite and nonnegative")
        return self


class Processes(Strict):
    sample_interval_seconds: float = Field(default=5, gt=0)
    allowlisted_executables: list[str] = []


class Response(Strict):
    evidence_dir: str = "./data/quarantine"
    max_files_per_incident: int = Field(default=100, ge=1)
    max_file_bytes: int = Field(default=10485760, ge=1)
    max_incident_bytes: int = Field(default=104857600, ge=1)
    simulate_termination: bool = False


class Reports(Strict):
    output_dir: str = "./data/reports"


class Dashboard(Strict):
    poll_interval_seconds: float = Field(default=2, ge=0.5, le=60)


class Logging(Strict):
    directory: str = "./logs"
    rotation: str = "10 MB"
    retention: str = "7 days"


class Settings(Strict):
    app: App = App()
    monitor: Monitor = Monitor()
    database: Database = Database()
    detection: Detection = Detection()
    processes: Processes = Processes()
    response: Response = Response()
    reports: Reports = Reports()
    dashboard: Dashboard = Dashboard()
    logging: Logging = Logging()

    @model_validator(mode="after")
    def valid(self):
        if not self.app.simulation_mode:
            raise ValueError("Only simulation mode is supported")
        if self.monitor.observer not in ("native", "polling"):
            raise ValueError("observer must be native or polling")
        return self


def load(path):
    path = Path(path).resolve()
    c = Settings.model_validate(yaml.safe_load(path.read_text()) or {})

    def absolute(value):
        return str((path.parent / value).resolve())

    c.monitor.watch_paths = [absolute(p) for p in c.monitor.watch_paths]
    c.monitor.exclude_paths = [absolute(p) for p in c.monitor.exclude_paths]
    for obj, key in [
        (c.database, "path"),
        (c.response, "evidence_dir"),
        (c.reports, "output_dir"),
        (c.logging, "directory"),
    ]:
        setattr(obj, key, absolute(getattr(obj, key)))
    validate_paths(c)
    return c


def validate_paths(c):
    roots = [Path(p) for p in c.monitor.watch_paths]
    outputs = [Path(c.response.evidence_dir), Path(c.reports.output_dir), Path(c.logging.directory)]
    if not roots:
        raise ValueError("At least one watched root is required")
    for i, r in enumerate(roots):
        if r == Path("/") or r == Path.home() or r in Path.home().parents:
            raise ValueError("Unsafe broad watched root")
        if any(r.is_relative_to(q) or q.is_relative_to(r) for q in roots[i + 1 :]):
            raise ValueError("Overlapping watched roots")
        if any(r.is_relative_to(q) for q in outputs):
            raise ValueError("Cannot watch output directory")
    c.monitor.exclude_paths += [str(p) for p in outputs] + [
        c.database.path + s for s in ("", "-wal", "-shm")
    ]
    return c
