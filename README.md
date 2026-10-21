# Ransomware Detection and Response System

RDRS is a local educational detector for ransomware-like file activity. It monitors configured folders, calculates an explainable threat score, records incidents and copies evidence without modifying source files.

## Requirements

- Docker with Docker Compose, and Python 3 for the launcher and safe simulator; or
- Python 3.12 or newer for running directly on Linux.

## Start with Docker

```bash
git clone https://github.com/Ganesha-hk/Ransomware-Detection-and-Response-System.git
cd Ransomware-Detection-and-Response-System
./scripts/start.sh
```

Open http://127.0.0.1:8000. The launcher creates the sandbox folders and a private `.env` file, builds the app and waits for it to become healthy. On a fresh installation, create the username **admin** at **Create account**, then log in with your chosen password. This account can change settings and inventory folders. Other accounts can view the shared workspace and generate reports. No Google credentials are needed. Keep `.env` private. If this repository is private, GitHub must grant you access before cloning.

```bash
docker compose ps
docker compose down
```

Stopping with `down` preserves runtime data. Do not add `-v` unless you intend to delete it.

## Run directly with Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export RDRS_AUTH_MODE=password
export RDRS_ADMIN_EMAILS=admin
export RDRS_SESSION_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
python -m app.main --config config.yaml
```

Use one server at a time on port 8000. Create username **admin** at `/signup`, then log in. Native startup creates the configured data directories automatically.

## Safe demonstration

Run on the host from the project directory:

```bash
python3 scripts/simulate_activity.py --profile benign
python3 scripts/simulate_activity.py --profile burst
```

The burst creates 50 new throwaway files in an exclusive sandbox folder, writes random content and renames them to `.locked`. It never selects existing user files. Expected default peak: 95/Critical. Simulation mode does not automatically generate activity. Allow the 60-second window and subsequent cooldown to finish between independent tests. Historical incidents remain after the live score returns to Normal.

## Dashboard

- **Overview:** live score, monitored folders, alerts and metrics.
- **Incidents:** detection reasons, observed files, timeline and evidence copies.
- **File activity:** live events with folder and event-type filters.
- **Reports:** select local start/end times and readable HTML, JSON or CSV formats. Only selected formats are generated, one per incident opened within the selected range. Event, file and evidence lists are restricted to that range; incident lifecycle and historical peak remain labeled context. The end time is excluded. HTML supports browser printing.
- **Setup & test:** inventory, detection settings and simulator instructions. The token field is only for legacy login-free local mode.

API documentation: http://127.0.0.1:8000/docs.

## Monitoring configuration

Edit `config.yaml` for native execution or `config.docker.yaml` for Docker. Restart after changing watched paths. Docker watches `data/sandbox` and five folders beneath `data/sensitive-lab`: finance, hr, customer-data, legal and backups. These host directories are mounted read-only. Runtime storage uses a Docker named volume. Each watched root has its own detection window.

## Limitations

This educational detector does not prevent ransomware, terminate processes, isolate hosts or restore files. High entropy can also arise from legitimate compressed or random content. Process snapshots provide context but cannot identify the file writer. Docker process visibility is container-scoped; its polling observer can miss short-lived changes. Evidence is a point-in-time copy, not a clean backup. Linux is the verified platform.

## Libraries and credits

Uses FastAPI, Uvicorn, watchdog, psutil, SQLAlchemy, Pydantic, PyYAML, Loguru and Jinja2. Versions are pinned in `requirements.txt`. Development was assisted by OpenAI Codex. See LICENSE for repository licensing.

## Local accounts and login

The default `RDRS_AUTH_MODE=password` needs no Google setup or email verification. Open `/signup`, choose an email or username and a password of 12–128 characters containing uppercase and lowercase letters, a number and a symbol. Common password patterns, low character variety, and passwords containing your username or email name are rejected. Existing accounts can continue using their current passwords. Log in at `/login`. Usernames are case-insensitive and can contain letters, numbers, dots, underscores and hyphens (3–64 characters). Email addresses are identifiers only; ownership is not verified.

Accounts persist in `accounts.db` beside the application database (inside the runtime volume for Docker). Passwords use salted scrypt hashes. Sessions expire after eight hours, on logout, or on server restart. There is no email delivery or password recovery service. This is a shared demonstration dashboard, not separate monitored storage for each account.

Set `RDRS_ADMIN_EMAILS` to comma-separated account identifiers (emails or usernames) allowed to edit monitoring settings and inventory folders. Other accounts can view incidents and generate reports. Register the intended administrator account yourself on the local machine.

Docker reads these settings from `.env`; native execution reads environment variables. Restart after changes. For an internet deployment, set `RDRS_PUBLIC_URL` to the exact HTTPS origin and `RDRS_SESSION_SECRET` to at least 32 random characters. Never commit secrets or account databases. The legacy `local` mode bypasses login and is restricted to trusted localhost demonstrations.

### Varied synthetic file demonstration

Run `python3 scripts/demo_varied_files.py` while RDRS is monitoring. It creates 24 new files in a uniquely named `data/sandbox/synthetic-varied-*` folder, with approximate entropy levels of 0, 1, 2, 4, 6 and 8 bits/byte and different sizes. Over about 24 seconds, it moves them from `incoming` to `processed`, producing real source and destination paths. Only its newly created files are moved. This is labeled synthetic demo activity, not a real attack, and does not guarantee a Critical alert. The local manifest in `data/demo-manifests` records paths, measured entropy and hashes. Runtime data and account secrets are not part of the repository.

## Troubleshooting startup

- Run commands from the repository directory. Linux is the tested platform; on Windows use WSL2 with Docker integration.
- Ensure the Docker daemon is running and `docker compose version` succeeds. Your user needs Docker access.
- If port 8000 is already occupied, stop the other RDRS instance before starting.
- View startup errors with `docker compose logs --tail=100 rdrs` and health with `docker compose ps`.
- Register the exact administrator identifier configured in `.env`. Existing `.env` files are preserved by the launcher.
- A server restart signs users out; account registrations and monitoring history remain in the Docker volume.
- A fresh installation starts empty. Run the safe demo to populate actual observations.

## Verified setup

Validated on Linux on 21 October 2026 using a separate checkout containing only repository files and new storage:

- Docker launcher build, health check, initially empty incidents/reports, local registration, administrator login and logout.
- Safe burst detection at 95/Critical and HTML, JSON and CSV report downloads.
- Fresh Python virtual environment dependency installation, `pip check`, native startup and sign-up route.
- Local development suite: 67 tests passed, 95% application coverage; Ruff and JavaScript syntax checks passed. Upstream deprecation warnings remain.

The repository contains runtime source and setup files; local test fixtures and submission material are maintained separately. These checks cover the tested Linux environment, not every operating system or hosting configuration.

### Readable business files and known simulator process

Run `python3 scripts/demo_business_files.py` on the host. This creates fictional invoices, an employee directory, customer records, a text agreement, application logs and a ZIP backup in a new sandbox directory. It edits the log and moves the invoice to `finance/processed`, then runs a safe burst in a **separate new directory**. Readable business files remain intact, verified by SHA-256 after the burst. All names and contact details are fictional.

The generated local manifest records the actual simulator PID, parent PID, executable and script as **self-reported simulator context**. This is not detector attribution. Host PIDs may not appear in container process snapshots. File events appear in the dashboard; the process context is available in the demo manifest, not attributed to incidents by RDRS. No endpoint agent or OS tracing has been added.

### Browser demo on Render

In **Setup & test**, choose **Run demo simulation**. It creates a fresh sandbox
folder with fictional content, then changes and renames 50 newly created files.
Watch Overview and Incidents for real detector results. Existing files are untouched.
Signed-in users share this disposable workspace. Runs are limited to one per
90 seconds and 20 folders per instance.

**Clear demo history** asks for confirmation, stops monitoring, clears activity,
incidents and report listings, then restarts monitoring. Accounts, configuration,
audit records and all files on disk (including evidence) remain intact. It does
not clear browser cache or reclaim disk space. Render's disposable filesystem
may reset on redeployment.

Controls are enabled automatically on Render. Set `RDRS_WEB_DEMO=0` to disable,
or `RDRS_WEB_DEMO=1` to enable explicitly in a disposable local demo. The monitored
`sandbox` must be writable; the default read-only Docker sandbox cannot run this
web simulator. Use the host simulation scripts for that Docker configuration.
