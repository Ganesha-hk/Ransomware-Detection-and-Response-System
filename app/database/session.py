import json
import threading
from sqlalchemy import create_engine, text, event
from app.core.models import uid, utc

KINDS = (
    "events",
    "processes",
    "scores",
    "alerts",
    "incidents",
    "incident_events",
    "evidence_files",
    "reports",
    "scan_jobs",
    "settings_versions",
    "audit_records",
)


class Store:
    def __init__(self, path, timeout=5000):
        self.lock = threading.RLock()
        self.engine = create_engine(
            "sqlite:///" + str(path), connect_args={"timeout": timeout / 1000}
        )

        @event.listens_for(self.engine, "connect")
        def setup(db, record):
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=NORMAL")

        with self.engine.begin() as c:
            c.execute(text("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)"))
            v = c.execute(text("SELECT version FROM schema_version")).scalar()
            if v is None:
                c.execute(text("INSERT INTO schema_version VALUES (1)"))
            elif v != 1:
                raise ValueError(
                    "Unsupported schema version; preserve database and migrate explicitly"
                )
            for kind in KINDS:
                c.execute(
                    text(
                        f"CREATE TABLE IF NOT EXISTS {kind} (id TEXT PRIMARY KEY, timestamp TEXT NOT NULL, root TEXT, incident_id TEXT REFERENCES incidents(id), event_id TEXT REFERENCES events(id), payload TEXT NOT NULL)"
                    )
                )
                c.execute(
                    text(
                        f"CREATE INDEX IF NOT EXISTS ix_{kind}_root_time ON {kind}(root,timestamp)"
                    )
                )
            c.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_incident_event_unique ON incident_events(incident_id,event_id)"
                )
            )

    def save(self, kind, data):
        if kind not in KINDS:
            raise ValueError("Unknown record kind")
        row = dict(data)
        row.setdefault("id", uid())
        row.setdefault("timestamp", utc())
        with self.lock, self.engine.begin() as c:
            c.execute(
                text(
                    f"INSERT INTO {kind} (id,timestamp,root,incident_id,event_id,payload) VALUES (:id,:timestamp,:root,:incident_id,:event_id,:payload) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload"
                ),
                dict(
                    id=row["id"],
                    timestamp=row["timestamp"],
                    root=row.get("root"),
                    incident_id=row.get("incident_id"),
                    event_id=row.get("event_id"),
                    payload=json.dumps(row),
                ),
            )
        return row

    def get(self, kind, id):
        if kind not in KINDS:
            raise ValueError("Unknown record kind")
        with self.engine.connect() as c:
            raw = c.execute(text(f"SELECT payload FROM {kind} WHERE id=:id"), {"id": id}).scalar()
        return json.loads(raw) if raw else None

    def rows(self, kind, limit=50, offset=0, root=None, incident_id=None, since=None, until=None):
        if kind not in KINDS:
            raise ValueError("Unknown record kind")
        filters = []
        args = dict(limit=limit, offset=offset)
        for k, v in [
            ("root", root),
            ("incident_id", incident_id),
            ("since", since),
            ("until", until),
        ]:
            if v is not None:
                filters.append(
                    {"since": "timestamp >= :since", "until": "timestamp <= :until"}.get(
                        k, f"{k}=:{k}"
                    )
                )
                args[k] = v
        where = " WHERE " + " AND ".join(filters) if filters else ""
        with self.engine.connect() as c:
            rows = c.execute(
                text(
                    f"SELECT payload FROM {kind}{where} ORDER BY timestamp DESC,id DESC LIMIT :limit OFFSET :offset"
                ),
                args,
            )
            return [json.loads(x[0]) for x in rows]

    def filtered(self, kind, limit=50, offset=0, **filters):
        if kind not in KINDS:
            raise ValueError("Unknown record kind")
        clauses = []
        args = dict(limit=limit, offset=offset)
        for key, value in filters.items():
            if value is None:
                continue
            if key in ("root", "since", "until"):
                clauses.append(
                    {
                        "root": "root=:root",
                        "since": "timestamp>=:since",
                        "until": "timestamp<=:until",
                    }[key]
                )
            elif key in ("severity", "event_type"):
                clauses.append(f"json_extract(payload,'$.{key}')=:{key}")
            elif key == "linked_incident":
                clauses.append(
                    "id IN (SELECT json_extract(payload,'$.event_id') FROM incident_events WHERE incident_id=:linked_incident)"
                )
            else:
                raise ValueError("Unsupported filter")
            args[key] = value
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self.engine.connect() as c:
            result = c.execute(
                text(
                    f"SELECT payload FROM {kind}{where} ORDER BY timestamp DESC,id DESC LIMIT :limit OFFSET :offset"
                ),
                args,
            )
            return [json.loads(row[0]) for row in result]

    def close(self):
        self.engine.dispose()
