#!/usr/bin/env bash
# Creates .env with random secrets and the owner login you type in. Refuses to overwrite.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -e .env ] && { echo ".env already exists, not touching it." >&2; exit 1; }
command -v openssl >/dev/null || { echo "openssl is required" >&2; exit 1; }

read -r -p "Owner email: " email
read -r -s -p "Owner password (min 10 chars): " pw; echo
[ "${#pw}" -ge 10 ] || { echo "Password too short." >&2; exit 1; }
case "$pw" in *\$*|*\`*|*\"*|*\\*|*\'*) echo "Avoid \$ \` \" ' \\ in the password (they break .env parsing)." >&2; exit 1;; esac

umask 077
cat > .env <<ENV
POSTGRES_PASSWORD=$(openssl rand -hex 24)
COCKPIT_SECRET_KEY=$(openssl rand -hex 32)
COCKPIT_ADMIN_EMAIL=${email}
COCKPIT_ADMIN_PASSWORD=${pw}
COCKPIT_COOKIE_SECURE=true
COCKPIT_PORT=8080
ENV
echo ".env written (mode 600). Start with: docker compose up -d --build"
