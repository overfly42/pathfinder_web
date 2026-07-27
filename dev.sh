#!/usr/bin/env bash
# Starts backend (FastAPI/uvicorn) and frontend (Vite) together for local dev.
# Ctrl+C stops both.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${PATHFINDER_VENV:-$HOME/python/pathfinder_web}"

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
