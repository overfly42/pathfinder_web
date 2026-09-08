#!/usr/bin/env bash
# Dumps the Postgres database to db_backups/, keeping the 7 most recent dumps.
# Called from dev.sh right after the db container comes up, so each dev
# session starts by snapshotting whatever was there before migrations/seeding
# touch it. Safe to run standalone too.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTAINER="pathfinder_web_db_1"
DB_USER="pathfinder"
DB_NAME="pathfinder"
BACKUP_DIR="${ROOT}/db_backups"
KEEP=7

mkdir -p "$BACKUP_DIR"

# Postgres may still be starting up (first boot runs initdb) — give it a
# few seconds to accept connections before giving up.
ready=""
for _ in $(seq 1 15); do
  if podman exec "$CONTAINER" pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done

if [ -z "$ready" ]; then
  echo "backup_db.sh: database not reachable, skipping backup" >&2
  exit 0
fi

timestamp="$(date +%Y%m%d-%H%M%S)"
backup_file="${BACKUP_DIR}/pathfinder-${timestamp}.sql.gz"

podman exec "$CONTAINER" pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$backup_file"
echo "backup_db.sh: wrote $backup_file"

# Prune to the KEEP most recent backups.
ls -1t "$BACKUP_DIR"/pathfinder-*.sql.gz 2>/dev/null | tail -n "+$((KEEP + 1))" | xargs -r rm --
