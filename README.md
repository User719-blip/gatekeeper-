# FastAPI Authentication and Authorization

Production-ready FastAPI backend with JWT auth, refresh tokens, RBAC, Supabase support, and automatic cloud-to-local database failover.

## Features

- JWT access and refresh token flow
- Role-based access control (superadmin/admin)
- Refresh token hashing and revocation
- Login rate limiting
- SQLAlchemy with Alembic migrations
- Primary cloud DB with local SQLite fallback
- Sentry error monitoring integration

## Stack

- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL (Supabase) + SQLite fallback
- python-jose + passlib
- slowapi
- sentry-sdk
- pytest

## Quick Start

```bash
# 1. Copy env template
cp .env.example .env

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run migrations
alembic upgrade head

# 4. Start server
fastapi run app.py

# 5. Run tests
pytest -q test/
```

## Docker

### Build and Run (single container)

```bash
docker build -t fastapi-auth-api .
docker run --rm -p 8000:8000 --env-file .env fastapi-auth-api
```

The container startup command automatically runs migrations:

```bash
alembic upgrade head && uvicorn app:app --host 0.0.0.0 --port 8000
```

### Run with Docker Compose

```bash
docker compose up --build
```

Compose maps `8000:8000` and sets a persistent SQLite fallback path inside a named volume:

- `FALLBACK_DATABASE_URL=sqlite:////app/data/app.db`

Stop services:

```bash
docker compose down
```

Stop and remove the SQLite volume:

```bash
docker compose down -v
```

## Environment Variables

Use `.env.example` as the template.

Required for production:

- PRIMARY_DATABASE_URL
- SECRET_KEY
- API_KEY

Optional:

- FALLBACK_DATABASE_URL
- DB_FAILOVER_ENABLED
- DB_CONNECT_TIMEOUT_SECONDS
- SENTRY_DSN
- ENVIRONMENT
- RATE_LIMIT_LOGIN

## Sentry: How It Works

If `SENTRY_DSN` is set, Sentry is initialized at app startup and captures unhandled exceptions.

### Expected behavior of `/test-error`

- Calling `/test-error` intentionally raises an exception.
- API response is HTTP 500 by design.
- You will see traceback logs in server output.
- Sentry should receive the event in the dashboard.

So seeing "Internal Server Error" is normal for this test route.

### Verify event reached Sentry

1. Open Sentry project dashboard.
2. Go to Issues.
3. Find event message: `Test error - appears in Sentry dashboard`.
4. Check environment tag (`development`/`production`).

### If event does not appear

1. Confirm `SENTRY_DSN` is present in `.env`.
2. Restart server after changing `.env`.
3. Ensure app starts without import errors.
4. Trigger `/test-error` again and wait 10-30 seconds.

## API Endpoints

Authentication:

- POST /admin/register
- POST /admin/login
- POST /admin/refresh
- POST /admin/logout
- POST /admin/promote/{username}
- DELETE /admin/remove/{username}

Applications:

- POST /apply
- GET /applications
- PATCH /approve/{application_id}
- DELETE /delete/{application_id}

Observability:

- GET /
- GET /health
- GET /test-error (test only)

## Database Failover

Startup behavior:

1. Try `PRIMARY_DATABASE_URL`.
2. If unavailable, switch to `FALLBACK_DATABASE_URL`.
3. Continue serving requests using fallback DB.

Check active DB:

```bash
python -c "from db.database import ACTIVE_DATABASE_URL; print(ACTIVE_DATABASE_URL)"
```

## Security Notes

- Do not commit `.env`.
- Rotate exposed DB passwords immediately.
- Use strong values for `SECRET_KEY` and `API_KEY`.
- Restrict CORS origins in production.
- Keep `/test-error` disabled or protected in production.