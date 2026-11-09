#!/usr/bin/env bash
# Dumps the database to ./backups/cockpit-<timestamp>.sql.gz. Run it from cron on the Pi.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p backups
out="backups/cockpit-$(date +%Y%m%d-%H%M%S).sql.gz"
docker compose exec -T db pg_dump -U cockpit cockpit | gzip > "$out"
echo "wrote $out"
# keep the 14 most recent
ls -1t backups/cockpit-*.sql.gz | tail -n +15 | xargs -r rm --
