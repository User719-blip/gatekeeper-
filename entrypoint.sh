#!/bin/sh
set -eu

echo "[startup] Running migrations (best effort)..."
if python -m alembic upgrade head; then
  echo "[startup] Migrations completed."
else
  echo "[startup] Migration failed. Continuing to start API."
fi

echo "[startup] Starting uvicorn on port ${PORT:-8000}..."
exec python -m uvicorn app:app --host 0.0.0.0 --port "${PORT:-8000}"
