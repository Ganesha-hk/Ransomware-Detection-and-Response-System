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
- **Reports:** select local start/end times and readable HTML, JSON or CSV formats. Only selected formats are generated, one per matching incident. The end time is excluded. HTML supports browser printing.
- **Setup & test:** token entry, inventory, detection settings and simulator instructions.

API documentation: http://127.0.0.1:8000/docs.

## Monitoring configuration

Edit `config.yaml` for native execution or `config.docker.yaml` for Docker. Restart after changing watched paths. Docker watches `data/sandbox` and five folders beneath `data/sensitive-lab`: finance, hr, customer-data, legal and backups. These host directories are mounted read-only. Runtime storage uses a Docker named volume. Each watched root has its own detection window.

## Limitations

This educational detector does not prevent ransomware, terminate processes, isolate hosts or restore files. High entropy can also arise from legitimate compressed or random content. Process snapshots provide context but cannot identify the file writer. Docker process visibility is container-scoped; its polling observer can miss short-lived changes. Evidence is a point-in-time copy, not a clean backup. Linux is the verified platform.

## Libraries and credits

Uses FastAPI, Uvicorn, watchdog, psutil, SQLAlchemy, Pydantic, PyYAML, Loguru and Jinja2. Versions are pinned in `requirements.txt`. Development was assisted by OpenAI Codex. See LICENSE for repository licensing.

## Google login and account creation

The default mode requires Google login. `/login` and `/signup` both use **Continue with Google**. Google verifies the email; the first successful sign-in creates the local account. No Gmail password or inbox access is requested. This is a shared demonstration workspace, not a separate filesystem per user.

1. In Google Cloud, configure an OAuth consent screen and create an OAuth client of type **Web application**.
2. Add an authorized redirect URI matching your host exactly: `http://127.0.0.1:8000/auth/callback` locally, or `https://YOUR-SERVICE.onrender.com/auth/callback` on Render.
3. Set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `RDRS_PUBLIC_URL` (origin only), and `RDRS_SESSION_SECRET` (at least 32 random characters) in the environment or Docker `.env`. Never commit real secrets.
4. Set `RDRS_ADMIN_EMAILS` to a comma-separated list of verified administrator emails. Others can read the shared sandbox and generate reports; only administrators can inventory folders or edit settings.
5. Restart. Use **Create an account**, choose your Google account, then enter the dashboard. Use **Sign out** to revoke the session. Sessions last up to eight hours and are invalidated on server restart. Account identities persist beside the application database in `accounts.db`.

If Google's consent screen is in Testing, add the evaluator's Google account to its test users. A production consent configuration may require Google verification. The external sign-in requires valid Google credentials and has not been end-to-end verified until those credentials are connected.

For a trusted localhost demonstration without Google, explicitly set `RDRS_AUTH_MODE=local`. Local mode retains the existing administrator token for write actions. Do not expose local mode to the internet. A public `RDRS_PUBLIC_URL` requires HTTPS, Google mode and complete credentials; startup fails if these are missing.

Google setup reference: https://developers.google.com/identity/openid-connect/openid-connect
