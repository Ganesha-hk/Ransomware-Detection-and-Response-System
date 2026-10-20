#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v docker >/dev/null || { echo 'Install Docker with Compose first.'; exit 1; }
mkdir -p data/sandbox data/sensitive-lab/{finance,hr,customer-data,legal,backups}
if [ ! -f .env ]; then
  (umask 077; python3 -c 'import secrets; print("RDRS_ADMIN_TOKEN="+secrets.token_urlsafe(32))' > .env)
fi
docker compose up --build -d
echo 'RDRS: http://127.0.0.1:8000'
echo 'Your local admin token is in .env. Enter its value on Setup & test for write actions.'
echo 'Keep .env private. The service watches the sandbox and five sensitive-lab departments; it does not scan the entire VM.'
