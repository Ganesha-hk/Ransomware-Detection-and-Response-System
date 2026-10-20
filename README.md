> **Reviewer files:** [Project report](submission/PROJECT_REPORT.docx), [report source](submission/PROJECT_REPORT.md), and [three matching sample reports](submission/sample-reports/). Latest verification: 58 tests passed, 95.16% statement coverage.

> **Submission package:** Start with [the demonstration and artifact index](docs/SUBMISSION_INDEX.md). It links the current screenshots, final reports, integrity checks, test results and reflection.

# RDRS — Ransomware Detection and Response System

A local, rules-based educational detector with real filesystem observation, explainable scores, persistent incidents, copy-only evidence, a live dashboard, and JSON/CSV reports. It does not identify an attacker's process, prevent ransomware, or restore files.

## Quick start (Docker)

From the project directory, run `./scripts/start.sh`, then open **http://127.0.0.1:8000**. The launcher creates a private local token in `.env` on first use and starts the persistent service. Enter the token value in **Setup & test** when you need to run an inventory, change thresholds or generate a report. No token is needed to view activity or download existing reports.

The workspace has five pages:

- **Overview:** exact monitored folders, current score, retained latest incident, worker health and observed metrics.
- **Incidents:** persistent peaks, readable detection reasons, distinct-file history, copy outcomes and event timeline.
- **File activity:** actual live and inventory observations, with folder/type filters and pagination.
- **Reports:** choose a date/time period and HTML assessment, JSON and/or CSV; only selected formats are created. Historical exports remain available.
- **Setup & test:** monitoring instructions, bounded inventory, local admin access, versioned thresholds and safe test steps.

The Docker service monitors the host `data/sandbox` plus five department folders under `data/sensitive-lab`, mounted as `/sandbox` and `/sensitive-lab` inside the container. The live score expires after the detection window; historical incidents stay visible. An inventory reads existing files but does not treat their existence as an attack. Merely naming a file `.locked` does not prove ransomware.

## Run locally on Linux

From this repository directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
export RDRS_ADMIN_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
python -m app.main --config config.yaml
```

Open **http://127.0.0.1:8000**. Keep the server terminal open. The token protects report generation, scans and settings updates; it is never logged or committed. If unset, live detection and read access still work, but mutations return 401. To generate reports from the dashboard, enter the same token in its password field. Existing report downloads require no token on the local interface.

In a second terminal, activate the environment and run:

```bash
python scripts/simulate_activity.py --profile benign
python scripts/simulate_activity.py --profile burst
```

The burst creates a fresh exclusive sandbox folder containing 50 synthetic files, replaces only those files with random bytes, and renames them to `.locked`. It is not encryption. Existing user files are never selected. Expect 95/Critical with the default rules. Files are left for inspection, and ground-truth manifests are saved in `data/demo-manifests/`.

The `isolated` profile creates one high-entropy file (expected 0); `archive` creates 50 high-entropy files without renames (expected 65/Warning). Run profiles with at least 60 seconds between them when evaluating them independently. Incidents close after the score is below Critical for another 60 seconds. Historical peaks remain visible after the live score returns to Normal.

## Run with Docker

```bash
mkdir -p data/sandbox data/sensitive-lab/{finance,hr,customer-data,legal,backups}
export RDRS_ADMIN_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
docker compose up --build -d
docker compose ps
```

Open the same localhost address. Stop the local server first if it uses port 8000. Run the simulator **on the host**, not inside the read-only container sandbox mount. Runtime data persists in the `rdrs-runtime` named volume. The service is non-root, and only `127.0.0.1:8000` is published. No privileged mode, host PID namespace, Docker socket, or host-wide mount is used. The container uses a polling observer; brief changes between polls may be missed. Process statistics are container-scoped.

```bash
docker compose restart
docker compose down
```

`down` preserves the data volume; do not add `-v` if you want to retain incidents.

## Test and inspect

```bash
pytest --cov=app --cov-report=term-missing --cov-report=html --cov-fail-under=90
ruff check .
docker compose exec -T rdrs pytest --cov=app --cov-fail-under=90
```

Results and measured demo behavior are in [BUILD_STATUS](docs/BUILD_STATUS.md), [testing](docs/testing.md), and `evidence/`. Coverage is a gate, not a claim of detection accuracy. `/docs` provides interactive API documentation. The API supports scans without inserting them into live burst statistics, and versioned hot updates of thresholds, weights, and polling interval.

To verify copied artifacts against a downloaded raw JSON report:

```bash
python scripts/verify_evidence.py data/reports/REPORT_ID.json --evidence-root data/quarantine
```

## Configuration and operational notes

`config.yaml` lists all defaults. Relative paths resolve against that file, not the current shell directory. `--watch ./data/sandbox` is a validated convenience override. `uvicorn app.api.main:app` uses the same lifespan and accepts `RDRS_CONFIG`. Never use multiple workers or reload for a recorded demo; a database ownership lock rejects a second runtime.

The UI shows queue depth, dropped events, last processing time through `/status`, and degraded health. A dropped event is evidence of incomplete observation. SQLite/WAL, reports, evidence, logs and submission artifacts are excluded from monitoring. Archival is manual; there is no automatic evidence deletion. Stop the app before moving the SQLite database and its WAL/SHM companions. Unknown schema versions fail closed without deleting the database.

Evidence is a bounded point-in-time copy, not a forensic snapshot or clean backup. File changes and read failures are recorded. Source content can already have changed before capture. See [limitations](docs/limitations.md), [architecture](docs/architecture.md), [API](docs/api.md), [demo runbook](docs/demo_runbook.md) and [requirements matrix](docs/requirements_matrix.md).

## Credits and source scope

Built using FastAPI/Starlette, Uvicorn, SQLAlchemy/SQLite, watchdog, psutil, Pydantic, PyYAML, Loguru and Jinja2; development checks use pytest, coverage, HTTPX and Ruff. Versions are pinned in the requirements files. No paid API, AI model, training dataset or cloud service is used by the detector.

The supplied build pack is retained in `docs/RDRS_Astra_Build_Pack.md`. The supplied FSD version 1.0 and Hands-On Build Guide were reviewed on 20 October 2026. Their local demonstration and submission requirements are mapped in `submission/PROJECT_REPORT.md`. Neither document specifies a portal, recipient or deadline. Linux only has been verified. Development and documentation were assisted by OpenAI Codex; libraries and sample guidance are credited here. The student should review the implementation and comply with the internship provider’s AI-assistance rules.


## Multiple sensitive folders

Six independent roots are enabled: general sandbox plus Finance, HR, Customer Data, Legal and Backups. The five department directories live under `data/sensitive-lab/` on the host and `/sensitive-lab/` in Docker. They contain synthetic demonstration files only; no real business data or external folders are connected. The parent is not itself watched, avoiding overlapping roots and duplicate counting. Docker mounts both lab areas read-only.

Overview shows each root’s score, severity and file counts. File activity can filter by root; Setup & test can inventory any configured root. Incidents are grouped independently by root.

Run a controlled test in one department:

```bash
python scripts/simulate_activity.py --profile benign --department hr
python scripts/simulate_activity.py --profile burst --department finance
```

Allowed departments: finance, hr, customer-data, legal, backups. The simulator still creates an exclusive new run folder and never modifies existing files. The normal default remains the general sandbox.

Verified: real benign writes in all five departments followed by a Finance-only burst produced Finance 95 and all other roots 0, with zero dropped events. Results: `evidence/demo/multiple-folders.json`. To connect real business folders, specify their exact approved paths and add explicit read-only mounts/configured roots; do not mount or monitor the whole VM by default.

### Readable assessment reports

Open an incident and choose **Generate assessment report** (local admin token required). In Reports, choose **Open assessment report**. The standalone HTML includes an executive summary, historical severity, rule findings, observed files, chronological timeline, evidence manifest and recommended actions. Use the browser's **Print → Save as PDF** for a printable report. Reports are generated only on request; closure does not create exports. Existing incidents can generate one on demand. JSON and CSV remain available for data analysis. RDRS scores are behavioral scores, not vulnerability/CVSS scores.

Use **Reports → Create a report** to select local start/end dates and one or more formats. Only selected formats are generated, one per incident with events in the half-open period [start, end). Event/file/evidence tables are filtered; incident severity and findings retain labeled historical context. Previous reports remain under a collapsed history section.
