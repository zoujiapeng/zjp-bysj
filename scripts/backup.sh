#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups}"
POSTGRES_USER="${POSTGRES_USER:-student_care}"
POSTGRES_DB="${POSTGRES_DB:-student_care}"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

OUTPUT="${1:-$BACKUP_DIR/student-care-$(date +%Y%m%d-%H%M%S).dump}"
docker compose exec -T db pg_dump \
  --format=custom \
  --no-owner \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" > "$OUTPUT"
chmod 600 "$OUTPUT"
printf 'Backup created: %s\n' "$OUTPUT"
