#!/bin/sh
# Start the backend container: migrate, seed, then serve.
set -e

echo "Running database migrations..."
alembic upgrade head

# The first admin (FR-1.5), if FIRST_ADMIN_USERNAME/PASSWORD are set. Safe to repeat.
if [ -n "${FIRST_ADMIN_USERNAME:-}" ] && [ -n "${FIRST_ADMIN_PASSWORD:-}" ]; then
  python -m app.cli seed-admin
fi

# Optional demo data (one login per role). Safe to repeat.
if [ "${SEED_DEMO:-false}" = "true" ]; then
  python -m app.cli seed-demo
fi

# Nginx in front sets X-Forwarded-For to the real client address (replacing any
# value the client sent); the backend is only reachable through it in compose.
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'
