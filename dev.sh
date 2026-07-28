#!/usr/bin/env bash
# Starts the database (Postgres via podman-compose), backend (FastAPI/uvicorn),
# and frontend (Vite) together for local dev. Ctrl+C stops backend/frontend;
# the database container is left running (it's cheap to leave up between
# sessions and persists to a volume).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${PATHFINDER_VENV:-$HOME/python/pathfinder_web}"

source "$VENV/bin/activate"
podman-compose -f "$ROOT/docker-compose.yml" up -d

cleanup() {
  echo "Stopping dev servers..."
  kill 0
}
trap cleanup EXIT INT TERM

(
  cd "$ROOT/backend"
  source "$VENV/bin/activate"
  uvicorn app.main:app --reload --port 8000
) &

(
  cd "$ROOT/frontend"
  npm run dev
) &

wait
