# Ransomware Detection and Response System

RDRS is a local educational detector for ransomware-like file activity. It monitors configured folders, calculates an explainable threat score, records incidents and copies evidence without modifying source files.

## Requirements

- Docker with Docker Compose, and Python 3 for the launcher and safe simulator; or
- Python 3.12 or newer for running directly on Linux.

## Start with Docker

```bash
./scripts/start.sh
```

Open http://127.0.0.1:8000. The launcher creates the sandbox folders and a private `.env` file containing `RDRS_ADMIN_TOKEN`. Enter that token in **Setup & test** to generate reports, run an inventory or change settings. Keep `.env` private.

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
export RDRS_ADMIN_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
python -m app.main --config config.yaml
```

Use one server at a time on port 8000. Enter the same token in the dashboard for write actions.

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
- **Setup & test:** token entry, inventory, detection settings and simulator instructions.

API documentation: http://127.0.0.1:8000/docs.

## Monitoring configuration

Edit `config.yaml` for native execution or `config.docker.yaml` for Docker. Restart after changing watched paths. Docker watches `data/sandbox` and five folders beneath `data/sensitive-lab`: finance, hr, customer-data, legal and backups. These host directories are mounted read-only. Runtime storage uses a Docker named volume. Each watched root has its own detection window.

## Limitations

This educational detector does not prevent ransomware, terminate processes, isolate hosts or restore files. High entropy can also arise from legitimate compressed or random content. Process snapshots provide context but cannot identify the file writer. Docker process visibility is container-scoped; its polling observer can miss short-lived changes. Evidence is a point-in-time copy, not a clean backup. Linux is the verified platform.

## Libraries and credits

Uses FastAPI, Uvicorn, watchdog, psutil, SQLAlchemy, Pydantic, PyYAML, Loguru and Jinja2. Versions are pinned in `requirements.txt`. Development was assisted by OpenAI Codex. See LICENSE for repository licensing.

## Local accounts and login

The default `RDRS_AUTH_MODE=password` needs no Google setup or email verification. Open `/signup`, choose an email or username and a password of 10–128 characters, then log in at `/login`. Usernames are case-insensitive and can contain letters, numbers, dots, underscores and hyphens (3–64 characters). Email addresses are identifiers only; ownership is not verified.

Accounts persist in `accounts.db` beside the application database (inside the runtime volume for Docker). Passwords use salted scrypt hashes. Sessions expire after eight hours, on logout, or on server restart. There is no email delivery or password recovery service. This is a shared demonstration dashboard, not separate monitored storage for each account.

Set `RDRS_ADMIN_EMAILS` to comma-separated account identifiers (emails or usernames) allowed to edit monitoring settings and inventory folders. Other accounts can view incidents and generate reports. Register the intended administrator account yourself on the local machine.

Docker reads these settings from `.env`; native execution reads environment variables. Restart after changes. For an internet deployment, set `RDRS_PUBLIC_URL` to the exact HTTPS origin and `RDRS_SESSION_SECRET` to at least 32 random characters. Never commit secrets or account databases. The legacy `local` mode bypasses login and is restricted to trusted localhost demonstrations.
