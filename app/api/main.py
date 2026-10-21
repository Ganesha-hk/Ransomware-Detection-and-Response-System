import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, Header, Depends, Query, Request
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.concurrency import run_in_threadpool
from jinja2 import Environment, FileSystemLoader, select_autoescape
from app.services.runtime import Runtime
from app.services.settings_service import update
from app.api.schemas import ReportRequest, ReportSelection, ScanRequest, SettingsRequest

from app.api.auth import configure_auth, require_session_write

ASSETS = Path(__file__).resolve().parents[1] / "dashboard"


def create_app(config_path=None, watch=None):
    @asynccontextmanager
    async def lifespan(app):
        runtime = Runtime(config_path or os.getenv("RDRS_CONFIG", "config.yaml"), watch)
        app.state.runtime = runtime
        app.state.token = os.getenv("RDRS_ADMIN_TOKEN", "")
        await run_in_threadpool(runtime.start)
        try:
            yield
        finally:
            await run_in_threadpool(runtime.stop)

    app = FastAPI(title="RDRS educational detector", lifespan=lifespan)
    hostname = configure_auth(app, ASSETS)
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver", "[::1]", hostname]
    )
    app.mount("/static", StaticFiles(directory=ASSETS / "static"), name="static")

    def runtime():
        return app.state.runtime

    def authorize(request: Request, authorization: str | None = Header(default=None)):
        if app.state.auth_mode != "local":
            require_session_write(request, admin=request.url.path in ("/settings", "/scan"))
            return
        token = app.state.token
        if not token or not secrets.compare_digest(authorization or "", "Bearer " + token):
            raise HTTPException(401, "A local admin token is required")

    def found(kind, id):
        row = runtime().store.get(kind, id)
        if row is None:
            raise HTTPException(404, "Record not found")
        return row

    @app.get("/", response_class=HTMLResponse)
    def dashboard():
        env = Environment(
            loader=FileSystemLoader(ASSETS / "templates"), autoescape=select_autoescape()
        )
        return env.get_template("index.html").render()

    @app.get("/health")
    def health():
        s = runtime().status()
        return JSONResponse(
            {"live": True, "ready": s["ready"], "monitor_state": s["monitor_state"]},
            status_code=200 if s["ready"] else 503,
        )

    @app.get("/status")
    def status():
        return runtime().status()

    @app.get("/events")
    def events(
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
        root: str | None = None,
        since: str | None = None,
        until: str | None = None,
        type: str | None = None,
        incident: str | None = None,
    ):
        return runtime().store.filtered(
            "events",
            limit,
            offset,
            root=root,
            since=since,
            until=until,
            event_type=type,
            linked_incident=incident,
        )

    @app.get("/alerts")
    def alerts(
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
        severity: str | None = None,
        since: str | None = None,
        until: str | None = None,
    ):
        return runtime().store.filtered(
            "alerts", limit, offset, severity=severity, since=since, until=until
        )

    @app.get("/incidents")
    def incidents(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
        return runtime().store.rows("incidents", limit, offset)

    @app.get("/incidents/{id}")
    def incident(id: str):
        found("incidents", id)
        detail = runtime().reports.detail(id)
        pending = runtime().evidence_count(id)
        detail["evidence_state"] = (
            "pending" if pending else "partial" if detail["copy_failures"] else "complete"
        )
        return detail

    @app.get("/metrics")
    def metrics(limit: int = Query(100, ge=1, le=200)):
        r = runtime()
        recent = r.store.rows("events", 200)
        top = {}
        for e in recent:
            if (
                e["event_type"] in ("created", "modified", "moved")
                and e.get("source_kind") == "live"
            ):
                key = e.get("identity") or e.get("destination_path") or e["source_path"]
                item = top.setdefault(
                    key, dict(path=e.get("destination_path") or e["source_path"], observations=0)
                )
                item["observations"] += 1
        return dict(
            top_files=sorted(top.values(), key=lambda x: x["observations"], reverse=True)[:10],
            scores=r.store.rows("scores", limit),
            processes=r.store.rows("processes", limit),
            cpu_units="psutil process percent; may exceed 100 across cores",
        )

    @app.get("/reports")
    def reports(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
        return runtime().store.rows("reports", limit, offset)

    @app.post("/reports", dependencies=[Depends(authorize)])
    def generate(body: ReportRequest):
        found("incidents", body.incident_id)
        return runtime().reports.generate(body.incident_id, body.format)

    @app.post("/reports/selection", dependencies=[Depends(authorize)])
    def selected_reports(body: ReportSelection):
        r = runtime()
        matches = []
        for incident in r.store.rows("incidents", limit=100000):
            detail = r.reports.detail(incident["id"], body.start, body.end)
            if detail["event_timeline"]:
                matches.append(incident["id"])
        if not matches:
            return {"reports": [], "message": "No recorded incident activity in this period."}
        if len(matches) > 100:
            raise HTTPException(422, "Choose a shorter period (maximum 100 incidents).")
        return {"reports": [r.reports.generate(i, f, body.start, body.end)
                            for i in matches for f in body.formats],
                "message": "Generated only the selected formats, one report per matching incident."}

    @app.get("/reports/{id}/download")
    def download(id: str):
        row = found("reports", id)
        base = Path(runtime().config.reports.output_dir).resolve()
        path = base / row["path"]
        if not path.resolve().is_relative_to(base) or not path.is_file() or path.is_symlink():
            raise HTTPException(404, "Report artifact unavailable")
        return FileResponse(
            path,
            filename=path.name,
            media_type={"json": "application/json", "csv": "text/csv", "html": "text/html"}[row["format"]],
        )

    @app.get("/reports/{id}/view")
    def view_report(id: str):
        row = found("reports", id)
        base = Path(runtime().config.reports.output_dir).resolve()
        path = base / row["path"]
        if row["format"] != "html" or not path.resolve().is_relative_to(base) or not path.is_file() or path.is_symlink():
            raise HTTPException(404, "Assessment report unavailable")
        return FileResponse(path, media_type="text/html", headers={
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'",
            "X-Content-Type-Options": "nosniff",
        })

    @app.post("/scan", status_code=202, dependencies=[Depends(authorize)])
    def start_scan(body: ScanRequest):
        try:
            return runtime().start_scan(body.root)
        except FileExistsError as exc:
            raise HTTPException(409, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/scans")
    def scans(limit: int = Query(20, ge=1, le=200), offset: int = Query(0, ge=0)):
        return runtime().store.rows("scan_jobs", limit, offset)

    @app.get("/scans/{id}")
    def scan(id: str):
        return found("scan_jobs", id)

    @app.get("/settings")
    def settings():
        r = runtime()
        with r.lock:
            return dict(version=r.version, settings=r.config.model_dump())

    @app.post("/settings", dependencies=[Depends(authorize)])
    def settings_update(body: SettingsRequest):
        try:
            return update(runtime(), body.expected_version, body.patch)
        except FileExistsError as exc:
            raise HTTPException(409, str(exc)) from exc
        except (ValueError, TypeError, AttributeError) as exc:
            raise HTTPException(422, str(exc)) from exc

    return app


app = create_app()
