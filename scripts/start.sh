#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v docker >/dev/null || { echo 'Install Docker with Compose first.'; exit 1; }
command -v python3 >/dev/null || { echo 'Install Python 3 first.'; exit 1; }
docker compose version >/dev/null
docker info >/dev/null
mkdir -p data/sandbox data/sensitive-lab/{finance,hr,customer-data,legal,backups}
if [ ! -f .env ]; then
  (umask 077; python3 -c 'import secrets; print("RDRS_AUTH_MODE=password\nRDRS_ADMIN_EMAILS=admin\nRDRS_SESSION_SECRET="+secrets.token_urlsafe(48)+"\nRDRS_ADMIN_TOKEN="+secrets.token_urlsafe(32))' > .env)
fi
docker compose up --build -d --wait --wait-timeout 120
echo 'RDRS: http://127.0.0.1:8000'
echo 'Create your account at /signup, then log in. For a fresh setup, register username admin to manage settings.'
echo 'Existing installations keep the administrator identifiers configured in .env (RDRS_ADMIN_EMAILS).'
echo 'Keep .env private. The service watches the sandbox and five sensitive-lab departments; it does not scan the entire VM.'
