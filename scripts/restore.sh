#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: RESTORE_CONFIRM=YES ./scripts/restore.sh <backup.dump>" >&2
  exit 2
fi
if [[ "${RESTORE_CONFIRM:-}" != "YES" ]]; then
  echo "Restore is destructive. Set RESTORE_CONFIRM=YES to continue." >&2
  exit 2
fi
if [[ ! -f "$1" ]]; then
  echo "Backup file not found: $1" >&2
  exit 2
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_FILE="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
cd "$ROOT_DIR"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

POSTGRES_USER="${POSTGRES_USER:-student_care}"
POSTGRES_DB="${POSTGRES_DB:-student_care}"

docker compose stop backend frontend >/dev/null
trap 'docker compose up -d backend frontend >/dev/null' EXIT

docker compose exec -T db pg_restore \
  --clean \
  --if-exists \
  --no-owner \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" < "$BACKUP_FILE"

echo "Restore completed: $BACKUP_FILE"
