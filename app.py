import os
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from router.admin_router import admin_router
from router.router import router
from db.database import ACTIVE_DATABASE_URL

sentry_dsn = os.getenv("SENTRY_DSN")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
        environment=os.getenv("ENVIRONMENT", "development"),
        traces_sample_rate=0.1,  # 10% of requests
        profiles_sample_rate=0.1,
    )

app = FastAPI(
    title="FastAPI Authentication System",
    description="Production-grade auth with JWT, RBAC, and cloud-to-local failover",
    version="1.0.0",
)

# CORS Configuration - Update origins for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(router)
app.include_router(admin_router)


@app.get("/")
async def root():
    """API info and health check."""
    return {
        "message": "FastAPI Authentication System",
        "version": "1.0.0",
        "database": "Cloud (Supabase)" if "postgresql" in ACTIVE_DATABASE_URL else "Local (SQLite)",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "database": "Cloud" if "postgresql" in ACTIVE_DATABASE_URL else "Local"}


@app.post("/test-sentry-message")
async def test_sentry_message():
    """Send a non-fatal test event to Sentry and return success."""
    sentry_sdk.capture_message("Manual Sentry test message from /test-sentry-message", level="info")
    return {"message": "Sentry test message sent"}


# Trigger an error in a route to test
@app.get("/test-error")
async def test_error():
    raise Exception("Test error - appears in Sentry dashboard")