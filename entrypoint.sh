#!/bin/sh
set -eu

if [ "${RUN_MIGRATIONS_ON_STARTUP:-false}" = "true" ]; then
  echo "[startup] Running migrations (best effort)..."
  if python -m alembic upgrade head; then
    echo "[startup] Migrations completed."
  else
    echo "[startup] Migration failed. Continuing to start API."
  fi
else
  echo "[startup] Skipping migrations on startup. Set RUN_MIGRATIONS_ON_STARTUP=true to enable them."
fi

echo "[startup] Starting uvicorn on port ${PORT:-8000}..."
exec python -m uvicorn app:app --host 0.0.0.0 --port "${PORT:-8000}"
