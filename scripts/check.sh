#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

(
  cd "$ROOT_DIR/backend"
  python -m ruff check app tests alembic/env.py alembic/versions
  python -m ruff format --check app tests alembic/env.py alembic/versions
  python -m pytest -q
  python -m compileall app
)

(
  cd "$ROOT_DIR/frontend"
  if [[ ! -d node_modules ]]; then
    npm ci
  fi
  npm run build
)
